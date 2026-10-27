from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from . import paths, utils
from .config import get_config

GITHUB_API = "https://api.github.com"
REPO = f"{paths.GITHUB_OWNER}/{paths.GITHUB_REPO}"
REPO_URL = f"https://github.com/{REPO}"
RELEASES_API = f"{GITHUB_API}/repos/{REPO}/releases"
TAGS_API = f"{GITHUB_API}/repos/{REPO}/tags"
USER_AGENT = "FimpleLauncher-Updater/1.0"
JSON_ACCEPT = "application/vnd.github+json"
BINARY_ACCEPT = "application/octet-stream"

ProgressCB = Callable[[int, int, int], None]
StatusCB = Callable[[str], None]

PRESERVE_DIRS = {"Minecraft"}


@dataclass
class Release:
    tag: str
    name: str
    body: str
    url: str
    assets: List[dict] = field(default_factory=list)
    prerelease: bool = False
    published: str = ""

    @property
    def version(self) -> str:
        return self.tag.lstrip("vV").strip()

    def pick_asset(self) -> Optional[dict]:
        zips = [a for a in self.assets if str(a.get("name", "")).lower().endswith(".zip")]
        if zips:
            zips.sort(key=lambda a: 0 if "launcher" in str(a.get("name", "")).lower() else 1)
            return zips[0]
        return self.assets[0] if self.assets else None


@dataclass
class UpdateInfo:
    current: str
    latest: Optional[Release] = None
    error: Optional[str] = None

    @property
    def available(self) -> bool:
        if not self.latest:
            return False
        return _cmp(self.latest.version, self.current) > 0

    @property
    def size(self) -> int:
        if not self.latest:
            return 0
        a = self.latest.pick_asset()
        return int(a.get("size") or 0) if a else 0


def _vnums(v: str) -> tuple:
    out = []
    v = str(v).strip().lstrip("vV")
    for part in v.replace("-", ".").split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return tuple(out) or (0,)


def _cmp(a: str, b: str) -> int:
    va, vb = _vnums(a), _vnums(b)
    if va == vb:
        return 0
    return 1 if va > vb else -1


def _headers(accept: str = JSON_ACCEPT) -> dict:
    h = {"User-Agent": USER_AGENT, "Accept": accept}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _session():
    import requests

    return requests.Session()


def check_update(timeout: float = 12.0) -> UpdateInfo:
    current = paths.app_version()
    s = _session()
    try:
        r = s.get(f"{RELEASES_API}/latest", headers=_headers(), timeout=timeout)
        if r.status_code == 404:
            if not _repo_visible(s, timeout):
                return UpdateInfo(current, None, "repo_private")
            return _latest_tag(current, s, timeout)
        r.raise_for_status()
        data = r.json()
        rel = Release(
            tag=data.get("tag_name", "v0"),
            name=data.get("name") or data.get("tag_name", ""),
            body=data.get("body") or "",
            url=data.get("html_url", REPO_URL + "/releases"),
            assets=data.get("assets") or [],
            prerelease=bool(data.get("prerelease")),
            published=data.get("published_at", ""),
        )
        if not rel.assets:
            rel.assets = [{"name": f"Fimple-Launcher-{rel.version}.zip",
                           "url": f"{RELEASES_API}/{rel.tag}/zipball",
                           "size": 0, "browser_download_url": ""}]
        return UpdateInfo(current, rel, None)
    except Exception as e:
        utils.log(f"Проверка обновлений не удалась: {e}", "WARN")
        return UpdateInfo(current, None, str(e))


def _repo_visible(s, timeout: float) -> bool:
    r = s.get(f"{GITHUB_API}/repos/{REPO}", headers=_headers(), timeout=timeout)
    return r.status_code == 200


def _latest_tag(current: str, s, timeout: float) -> UpdateInfo:
    r = s.get(f"{TAGS_API}", headers=_headers(), timeout=timeout)
    if r.status_code != 200:
        utils.log("Обновлений нет: релизов и тегов ещё не создано", "INFO")
        return UpdateInfo(current, None, None)
    tags = r.json()
    if not tags:
        utils.log("Обновлений нет: релизов и тегов ещё не создано", "INFO")
        return UpdateInfo(current, None, None)
    latest = Release(
        tag=tags[0].get("name", "v0"),
        name=tags[0].get("name", ""),
        body="",
        url=REPO_URL + "/releases",
    )
    return UpdateInfo(current, latest, None)


def _verify_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            if not zf.namelist():
                raise RuntimeError("Архив обновления пуст")
    except zipfile.BadZipFile as e:
        raise RuntimeError(
            "Скачанный файл не является ZIP-архивом "
            "(возможно, GitHub вернул страницу ошибки)"
        ) from e


def download_release(release: Release, progress: Optional[ProgressCB] = None,
                     status: Optional[StatusCB] = None) -> Path:
    import requests

    asset = release.pick_asset()
    if not asset:
        raise RuntimeError("В релизе нет файлов для скачивания")

    api_url = str(asset.get("url") or "")
    browser_url = str(asset.get("browser_download_url") or "")
    tmp = paths.temp_dir()
    name = Path(str(asset.get("name") or "update.zip")).name or "update.zip"
    target = tmp / name

    if status:
        status(get_config().t("update_downloading"))

    def do_download(url: str, headers: dict) -> None:
        downloaded = 0
        total = int(asset.get("size") or 0)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        with requests.get(url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            ctype = str(r.headers.get("Content-Type") or "").lower()
            if "application/json" in ctype or "text/html" in ctype:
                raise RuntimeError(f"GitHub вернул {ctype} вместо файла архива")
            if not total:
                total = int(r.headers.get("Content-Length") or 0)
            with open(target, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total,
                                 int(downloaded * 100 / total) if total else 0)

    sources = []
    if api_url and not api_url.endswith("/zipball"):
        # API GitHub отдаёт метаданные JSON, пока не запрошен бинарный файл.
        sources.append((api_url, _headers(BINARY_ACCEPT)))
    if browser_url:
        sources.append((browser_url, {"User-Agent": USER_AGENT,
                                      "Accept": BINARY_ACCEPT}))
    if not sources:
        sources.append((api_url or browser_url, _headers(BINARY_ACCEPT)))

    errors = []
    for url, headers in sources:
        if not url:
            continue
        try:
            do_download(url, headers)
            _verify_archive(target)
            return target
        except Exception as e:
            errors.append(f"{e}")
            utils.log(f"Не удалось скачать обновление с {url}: {e}", "WARN")
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass

    raise RuntimeError("Не удалось скачать обновление: " + "; ".join(errors))


def _is_within(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except Exception:
        return False


def extract_release(archive: Path, dest: Path, status: Optional[StatusCB] = None) -> Path:
    if status:
        status(get_config().t("update_extracting"))
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        tops = {n.replace("\\", "/").split("/")[0] for n in names}
        single = tops.pop() if len(tops) == 1 else None
        for name in names:
            norm = name.replace("\\", "/")
            if norm.startswith("/") or ".." in norm.split("/"):
                continue
            rel = norm[len(single) + 1:] if single and norm.startswith(single + "/") else norm
            if not rel:
                continue
            out = dest / rel
            if not _is_within(dest, out):
                continue
            if name.endswith("/"):
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if os.name != "nt" and out.suffix in (".exe", ".sh", ""):
                try:
                    out.chmod(0o755)
                except OSError:
                    pass
    return dest


def _kill_running_launcher() -> None:
    if os.name != "nt":
        return

    try:
        me = os.getpid()
        out = utils.run_hidden(
            ["wmic", "process", "where", f"name='Fimple Launcher*.exe' or name='python.exe'",
             "get", "processid,commandline"],
            capture_output=True, timeout=10).stdout.decode("utf-8", "ignore")
        for line in out.splitlines():
            if str(me) in line or "Fimple Launcher" not in line:
                continue
            for token in line.split():
                if token.isdigit() and int(token) != me:
                    utils.run_hidden(["taskkill", "/F", "/PID", token],
                                     capture_output=True)
    except Exception:
        pass


def apply_update(archive: Path, release: Release, keep_data: bool = True,
                 status: Optional[StatusCB] = None) -> Path:
    base = paths.base_dir()
    staging = paths.temp_dir() / "update"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    extract_release(archive, staging, status=status)

    new_entry = None
    for cand in sorted(staging.iterdir()):
        if cand.suffix.lower() in (".exe", ".bat", ".cmd") and cand.is_file():
            new_entry = cand
            break
    if new_entry is None:
        new_entry = staging / "main.py"

    backup = base.parent / f"{base.name}.backup"
    if backup.exists():
        shutil.rmtree(backup, ignore_errors=True)

    if os.name == "nt":
        _kill_running_launcher()

    for item in list(base.iterdir()):
        if item.name in PRESERVE_DIRS or item.name.startswith("."):
            continue
        if item.is_dir() and item.name in ("__pycache__", "launcher", "assets", "lib"):
            shutil.rmtree(item, ignore_errors=True)
            continue
        if item.suffix.lower() in (".exe", ".py", ".spec", ".pyd", ".dll", ".zip") or item.is_file():
            try:
                item.unlink()
            except OSError:
                pass

    for item in staging.iterdir():
        dest = base / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
            if dest.suffix.lower() in (".exe", ".bat", ".cmd"):
                try:
                    dest.chmod(0o755)
                except OSError:
                    pass

    shutil.rmtree(staging, ignore_errors=True)
    try:
        archive.unlink(missing_ok=True)
    except Exception:
        pass
    utils.log(f"Обновление {release.version} применено в {base}")
    return new_entry


def relaunch(entry: Optional[Path] = None) -> None:
    import subprocess
    import sys

    entry = entry or paths.app_root_entry()
    if not entry:
        return
    if getattr(sys, "frozen", False) or entry.suffix.lower() == ".exe":
        cmd = [str(entry)]
    else:
        cmd = [sys.executable, str(entry)]
    cmd = utils.console_free_cmd(cmd)
    utils.log(f"Перезапуск: {' '.join(cmd)}")
    startupinfo, creationflags = utils.hidden_console_args(True)
    subprocess.Popen(cmd, close_fds=True,
                     startupinfo=startupinfo, creationflags=creationflags)
