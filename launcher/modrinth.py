from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import paths, utils
from .config import get_config

API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "FimpleLauncher/1.0 (minecraft launcher)"}


@dataclass
class Project:
    id: str
    title: str
    description: str = ""
    icon: str = ""
    author: str = ""
    downloads: int = 0
    follows: int = 0
    versions: List[str] = field(default_factory=list)
    client_side: str = ""
    server_side: str = ""
    project_type: str = "mod"
    slug: str = ""

    @property
    def url(self) -> str:
        return f"https://modrinth.com/mod/{self.slug or self.id}"

    def downloads_text(self) -> str:
        d = self.downloads
        if d >= 1_000_000:
            return f"{d / 1_000_000:.1f}M"
        if d >= 1_000:
            return f"{d / 1_000:.0f}K"
        return str(d)


@dataclass
class ModVersion:
    id: str
    project_id: str
    name: str
    version_number: str
    game_versions: List[str]
    loaders: List[str]
    version_type: str = "release"
    downloads: int = 0
    files: List[dict] = field(default_factory=list)
    dependencies: List[dict] = field(default_factory=list)

    @property
    def file(self) -> Optional[dict]:
        primary = [f for f in self.files if f.get("primary")]
        return (primary or self.files or [None])[0]

    def loader_text(self) -> str:
        return ", ".join(l.capitalize() for l in self.loaders)

    def mc_text(self) -> str:
        gv = self.game_versions
        if len(gv) > 4:
            return f"{gv[0]}…{gv[-1]} ({len(gv)})"
        return ", ".join(gv)


def _session():
    import requests

    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def _project_from_hit(hit: dict) -> Project:
    return Project(
        id=hit.get("project_id", ""),
        slug=hit.get("slug", ""),
        title=hit.get("title", ""),
        description=hit.get("description", ""),
        icon=hit.get("icon_url") or "",
        author=hit.get("author", ""),
        downloads=int(hit.get("downloads") or 0),
        follows=int(hit.get("follows") or 0),
        versions=hit.get("versions") or [],
        client_side=hit.get("client_side", ""),
        server_side=hit.get("server_side", ""),
        project_type=hit.get("project_type", "mod"),
    )


def search(query: str, loaders: Sequence[str] = (), game_version: str = "",
           project_type: str = "mod", limit: int = 40) -> List[Project]:
    s = _session()
    facets = [[f"project_type:{project_type}"]]
    if loaders:
        facets.append(["categories:" + l for l in loaders])
    if game_version:
        facets.append([f"versions:{game_version}"])
    r = s.get(f"{API}/search", params={
        "query": query,
        "facets": facets,
        "limit": limit,
        "index": "relevance",
    }, timeout=15)
    r.raise_for_status()
    return [_project_from_hit(h) for h in r.json().get("hits", [])]


def project(project_id: str) -> Project:
    s = _session()
    r = s.get(f"{API}/project/{project_id}", timeout=15)
    r.raise_for_status()
    d = r.json()
    return Project(
        id=d.get("id", project_id),
        slug=d.get("slug", ""),
        title=d.get("title", ""),
        description=d.get("description", ""),
        icon=d.get("icon_url") or "",
        author=d.get("display_name") or d.get("team", "") and ", ".join(
            t.get("name", "") for t in d.get("team", [])) or "",
        downloads=int(d.get("downloads") or 0),
        follows=int(d.get("follows") or 0),
        versions=[v["version_number"] for v in d.get("versions", [])],
        client_side=d.get("client_side", ""),
        server_side=d.get("server_side", ""),
        project_type=d.get("project_type", "mod"),
    )


def versions(project_id: str) -> List[ModVersion]:
    s = _session()
    r = s.get(f"{API}/project/{project_id}/version", timeout=15)
    r.raise_for_status()
    out = []
    for v in r.json():
        out.append(ModVersion(
            id=v.get("id", ""),
            project_id=v.get("project_id", project_id),
            name=v.get("name", ""),
            version_number=v.get("version_number", ""),
            game_versions=v.get("game_versions", []),
            loaders=v.get("loaders", []),
            version_type=v.get("version_type", "release"),
            downloads=int(v.get("downloads") or 0),
            files=v.get("files", []),
            dependencies=v.get("dependencies", []),
        ))
    return out


def best_version(project_id: str, loaders: Sequence[str], game_version: str) -> Optional[ModVersion]:
    all_v = versions(project_id)
    if not all_v:
        return None

    def score(v: ModVersion) -> tuple:
        loader_match = 1 if (not loaders or set(v.loaders) & set(loaders)) else 0
        mc_match = 1 if game_version in v.game_versions else 0
        type_rank = {"release": 3, "beta": 2, "alpha": 1}.get(v.version_type, 0)
        return (mc_match, loader_match, type_rank, v.downloads)

    return sorted(all_v, key=score, reverse=True)[0]


def resolve_dependencies(version: ModVersion, loaders: Sequence[str],
                         game_version: str) -> List[ModVersion]:
    if not version.dependencies:
        return []
    s = _session()
    result: Dict[str, ModVersion] = {}

    def walk(project_id: str, seen: set):
        if project_id in seen:
            return
        seen.add(project_id)
        try:
            best = best_version(project_id, loaders, game_version)
        except Exception:
            return
        if not best:
            return
        result[project_id] = best
        for dep in best.dependencies:
            if dep.get("version_id") and dep.get("project_id"):
                walk(dep["project_id"], seen)

    seen = {version.project_id}
    for dep in version.dependencies:
        pid = dep.get("project_id")
        if pid:
            walk(pid, seen)
    return list(result.values())


def download_file(file_info: dict, dest_dir: Path, progress=None) -> Path:
    import requests

    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / file_info["filename"]
    tmp = target.with_suffix(target.suffix + ".part")
    total = int(file_info.get("size") or 0)
    downloaded = 0
    with requests.get(file_info["url"], stream=True, timeout=60, headers=HEADERS) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total, int(downloaded * 100 / total) if total else 0)
    tmp.replace(target)
    return target


def install_mod(inst_dir: Path, version: ModVersion, progress=None,
                with_deps: bool = True, loaders: Sequence[str] = (),
                game_version: str = "") -> List[Path]:
    mods_dir = inst_dir / "mods"
    out: List[Path] = []
    targets = [version]
    if with_deps:
        targets += resolve_dependencies(version, loaders, game_version)
    for i, v in enumerate(targets):
        f = v.file
        if not f:
            continue
        out.append(download_file(f, mods_dir, progress))
    return out


def install_project(inst_dir: Path, project_id: str, loaders: Sequence[str],
                    game_version: str, progress=None, with_deps: bool = True) -> List[Path]:
    v = best_version(project_id, loaders, game_version)
    if not v:
        raise RuntimeError("Подходящая версия мода не найдена")
    return install_mod(inst_dir, v, progress, with_deps, loaders, game_version)


def list_local_mods(inst_dir: Path) -> List[Tuple[str, Path, bool]]:
    mods_dir = inst_dir / "mods"
    if not mods_dir.exists():
        return []
    out = []
    for p in sorted(mods_dir.iterdir()):
        if p.is_dir():
            continue
        name = p.name
        disabled = name.endswith(".disabled")
        if disabled:
            name = name[: -len(".disabled")]
        if not (name.endswith(".jar") or name.endswith(".zip")):
            continue
        out.append((name, p, not disabled))
    return out


def set_mod_enabled(path: Path, enabled: bool) -> None:
    if enabled and path.name.endswith(".disabled"):
        path.rename(path.with_name(path.name[: -len(".disabled")]))
    elif not enabled and not path.name.endswith(".disabled"):
        path.rename(path.with_name(path.name + ".disabled"))


def remove_mod(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def mod_icon_url(project_id: str) -> str:
    return f"https://cdn.modrinth.com/data/{project_id}/icon.png"
