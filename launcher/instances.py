from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import java as javamod
from . import paths, utils
from .config import get_config

ProgressCB = Callable[[int, int, int], None]
StatusCB = Callable[[str], None]
LogCB = Callable[[str], None]

LOADER_LABELS = {
    "vanilla": "Vanilla",
    "forge": "Forge",
    "fabric": "Fabric",
    "quilt": "Quilt",
    "neoforge": "NeoForge",
    "optifine": "OptiFine",
    "liteloader": "LiteLoader",
}

LOADER_COLORS = {
    "vanilla": "#5aa469",
    "forge": "#1f6f8b",
    "fabric": "#c8a06a",
    "quilt": "#9b59b6",
    "neoforge": "#e8a33d",
    "optifine": "#c0392b",
    "liteloader": "#7f8c8d",
}

LOADER_ORDER = (
    ("vanilla", "grass"),
    ("forge", "hammer"),
    ("fabric", "layers"),
    ("quilt", "layers"),
    ("neoforge", "hammer"),
    ("optifine", "sun"),
)

DISABLED_LOADERS = ("quilt", "optifine")


def loader_enabled(loader: str) -> bool:
    return loader not in DISABLED_LOADERS


_MOD_COUNT_CACHE: dict = {}


def _dir_stamp(folder: Path):
    try:
        st = folder.stat()
        return (int(st.st_mtime_ns), st.st_size)
    except OSError:
        return None


@dataclass
class Instance:
    id: str
    mc_version: str
    loader: str = "vanilla"
    created: float = field(default_factory=time.time)
    last_played: float = 0.0
    playtime: float = 0.0
    launches: int = 0
    java_path: Optional[str] = None
    jvm_args: str = ""
    window_width: int = 854
    window_height: int = 480
    icon: Optional[str] = None
    notes: str = ""

    @property
    def path(self) -> Path:
        return paths.instances_dir() / self.id

    @property
    def label(self) -> str:
        return LOADER_LABELS.get(self.loader, self.loader)

    @property
    def base_mc(self) -> str:
        v = self.mc_version or ""
        if self.loader == "neoforge":
            m = re.match(r"neoforge-(\d+)\.(\d+)", v, re.IGNORECASE)
            if m:
                major, minor = int(m.group(1)), int(m.group(2))
                if major >= 26:
                    return f"{major}.{minor}"
                if major >= 20:
                    return f"1.{major}.{minor}"
        if self.loader in ("fabric", "quilt"):
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)\s*$", v)
            if m:
                return m.group(1)
        if self.loader in ("forge", "neoforge", "optifine"):
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", v)
            if m:
                return m.group(1)
        return v

    @property
    def is_fabric_like(self) -> bool:
        return self.loader in ("fabric", "quilt")

    def exists(self) -> bool:
        return (self.path / "instance.json").exists()

    def mod_count(self) -> int:
        mods = self.path / "mods"
        if not mods.exists():
            return 0
        stamp = _dir_stamp(mods)
        cached = _MOD_COUNT_CACHE.get(str(mods))
        if cached and cached[0] == stamp:
            return cached[1]
        count = len([p for p in mods.iterdir() if p.suffix == ".jar"])
        if len(_MOD_COUNT_CACHE) > 256:
            _MOD_COUNT_CACHE.clear()
        _MOD_COUNT_CACHE[str(mods)] = (stamp, count)
        return count

    def save_count(self) -> int:
        saves = self.path / "saves"
        if not saves.exists():
            return 0
        return len([p for p in saves.iterdir() if p.is_dir()])

    def size_mb(self) -> float:
        total = 0
        if not self.path.exists():
            return 0.0
        for p in self.path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                pass
        return total / 1024 / 1024

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mc_version": self.mc_version,
            "loader": self.loader,
            "created": self.created,
            "last_played": self.last_played,
            "playtime": self.playtime,
            "launches": self.launches,
            "java_path": self.java_path,
            "jvm_args": self.jvm_args,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "icon": self.icon,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Instance":
        return Instance(
            id=data.get("id", "unknown"),
            mc_version=data.get("mc_version", "1.0"),
            loader=data.get("loader", "vanilla"),
            created=data.get("created", time.time()),
            last_played=data.get("last_played", 0),
            playtime=data.get("playtime", 0),
            launches=data.get("launches", 0),
            java_path=data.get("java_path"),
            jvm_args=data.get("jvm_args", ""),
            window_width=data.get("window_width", 854),
            window_height=data.get("window_height", 480),
            icon=data.get("icon"),
            notes=data.get("notes", ""),
        )


class InstanceRepo:
    def __init__(self) -> None:
        self._cache: Optional[List[Instance]] = None

    def all(self) -> List[Instance]:
        if self._cache is not None:
            return self._cache
        out: List[Instance] = []
        base = paths.instances_dir()
        for child in base.iterdir():
            meta = child / "instance.json"
            if not meta.exists():
                continue
            data = utils.read_json(meta, None)
            if not data:
                continue
            inst = Instance.from_dict(data)
            if inst.exists():
                out.append(inst)
        out.sort(key=lambda i: (i.last_played or i.created), reverse=True)
        self._cache = out
        return out

    def get(self, instance_id: str) -> Optional[Instance]:
        for i in self.all():
            if i.id == instance_id:
                return i
        return None

    def create(self, instance_id: str, mc_version: str, loader: str = "vanilla",
               **kwargs) -> Instance:
        inst = Instance(id=instance_id, mc_version=mc_version, loader=loader, **kwargs)
        for folder in ("mods", "saves", "config", "resourcepacks", "shaderpacks", "screenshots"):
            (inst.path / folder).mkdir(parents=True, exist_ok=True)
        self.save(inst)
        self.invalidate()
        return inst

    def save(self, inst: Instance) -> None:
        inst.path.mkdir(parents=True, exist_ok=True)
        (inst.path / "instance.json").write_text(
            json.dumps(inst.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        self.invalidate()

    def delete(self, inst: Instance, remove_data: bool = True) -> None:
        if remove_data and inst.path.exists():
            shutil.rmtree(inst.path, ignore_errors=True)
        self.invalidate()

    def rename(self, inst: Instance, new_id: str) -> Optional[Instance]:
        new_id = sanitize_id(new_id)
        if not new_id or new_id == inst.id:
            return None
        if self.get(new_id):
            return None
        old_path = inst.path
        new_path = paths.instances_dir() / new_id
        if old_path.exists():
            if new_path.exists():
                shutil.rmtree(new_path, ignore_errors=True)
            old_path.rename(new_path)
        inst.id = new_id
        self.save(inst)
        self.invalidate()
        return inst

    def invalidate(self) -> None:
        self._cache = None

    def register_launch(self, inst: Instance) -> None:
        inst.launches += 1
        inst.last_played = time.time()
        self.save(inst)

    def add_playtime(self, inst: Instance, seconds: float) -> None:
        inst.playtime = float(inst.playtime or 0) + seconds
        self.save(inst)
        data = utils.read_json(paths.playtime_file(), {"total_seconds": 0}) or {}
        data["total_seconds"] = float(data.get("total_seconds", 0)) + seconds
        data.setdefault("per_instance", {})
        data["per_instance"][inst.id] = float(
            (data.get("per_instance") or {}).get(inst.id, 0)) + seconds
        utils.write_json(paths.playtime_file(), data)


def repo() -> InstanceRepo:
    global _REPO
    if _REPO is None:
        _REPO = InstanceRepo()
    return _REPO


_REPO: Optional[InstanceRepo] = None


def sanitize_id(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", (name or "").strip())
    name = name.replace(" ", "_")
    return name[:64]


def total_playtime() -> float:
    data = utils.read_json(paths.playtime_file(), {"total_seconds": 0}) or {}
    return float(data.get("total_seconds", 0))


def _mll():
    import minecraft_launcher_lib as mll

    return mll


_LEGACY_NEOFORGE_MC = "1.20.1"
_LEGACY_NEOFORGE_METADATA = (
    "https://maven.neoforged.net/releases/net/neoforged/forge/maven-metadata.xml")
_legacy_neoforge_cache: Tuple[float, List[str]] = (0.0, [])
_NEOFORGE_COMPAT = None


def _legacy_artifact_version(loader_version: str) -> str:
    v = (loader_version or "").strip()
    prefix = _LEGACY_NEOFORGE_MC + "-"
    return v[len(prefix):] if v.startswith(prefix) else v


def _legacy_neoforge_versions() -> List[str]:
    global _legacy_neoforge_cache
    stamp, cached = _legacy_neoforge_cache
    if cached and time.time() - stamp < 3600:
        return list(cached)
    try:
        import requests

        r = requests.get(_LEGACY_NEOFORGE_METADATA, timeout=20,
                         headers={"User-Agent": "FimpleLauncher/1.0"})
        r.raise_for_status()
        raw = re.findall(r"<version>\s*([^<]+?)\s*</version>", r.text)
    except Exception as e:
        utils.log(f"Не удалось получить версии NeoForge 1.20.1: {e}", "WARN")
        return list(cached)

    prefix = _LEGACY_NEOFORGE_MC + "-"
    versions = []
    for v in raw:
        v = v.strip()
        if v.startswith(prefix):
            v = v[len(prefix):]
        if re.fullmatch(r"47\.\d+\.\d+", v):
            versions.append(v)
    versions.sort(key=utils.version_key, reverse=True)
    _legacy_neoforge_cache = (time.time(), versions)
    return list(versions)


def _neoforge_compat_class():
    global _NEOFORGE_COMPAT
    if _NEOFORGE_COMPAT is not None:
        return _NEOFORGE_COMPAT or None
    try:
        from minecraft_launcher_lib.mod_loader._neoforge import Neoforge
    except Exception:
        _NEOFORGE_COMPAT = False
        return None

    class _NeoForgeCompat(Neoforge):
        def _normalize_minecraft_version(self, minecraft_version: str) -> str:
            m = re.match(r"^(\d+)\.(\d+)", minecraft_version or "")
            if not m:
                return minecraft_version
            major = int(m.group(1))
            if major >= 26:
                return f"{major}.{m.group(2)}"
            return f"1.{major}.{m.group(2)}"

        def get_minecraft_versions(self, stable_only: bool) -> List[str]:
            versions = list(super().get_minecraft_versions(stable_only))
            if _legacy_neoforge_versions() and _LEGACY_NEOFORGE_MC not in versions:
                versions.append(_LEGACY_NEOFORGE_MC)
            return versions

        def get_loader_versions(self, minecraft_version: str,
                                stable_only: bool) -> List[str]:
            if minecraft_version == _LEGACY_NEOFORGE_MC:
                return _legacy_neoforge_versions()
            return list(super().get_loader_versions(minecraft_version, stable_only))

        def get_installer_url(self, minecraft_version: str,
                              loader_version: str) -> str:
            if minecraft_version == _LEGACY_NEOFORGE_MC:
                v = _legacy_artifact_version(loader_version)
                return ("https://maven.neoforged.net/releases/net/neoforged/"
                        f"forge/{_LEGACY_NEOFORGE_MC}-{v}/"
                        f"forge-{_LEGACY_NEOFORGE_MC}-{v}-installer.jar")
            return super().get_installer_url(minecraft_version, loader_version)

        def get_installed_version(self, minecraft_version: str,
                                  loader_version: str) -> str:
            if minecraft_version == _LEGACY_NEOFORGE_MC:
                return (f"{_LEGACY_NEOFORGE_MC}-forge-"
                        f"{_legacy_artifact_version(loader_version)}")
            return super().get_installed_version(minecraft_version, loader_version)

    _NEOFORGE_COMPAT = _NeoForgeCompat
    return _NEOFORGE_COMPAT


def _mod_loader(mll, loader: str):
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is None:
        return None
    if loader == "neoforge":
        compat = _neoforge_compat_class()
        if compat is not None:
            try:
                return mod_loader.ModLoader(compat())
            except Exception as e:
                utils.log(f"Заплатка NeoForge не применилась: {e}", "WARN")
    return mod_loader.get_mod_loader(loader)


class _MllProgress:
    def __init__(self, progress: ProgressCB, status: Optional[StatusCB],
                 log_cb: Optional[LogCB]):
        self._progress = progress
        self._status = status
        self._log = log_cb
        self._max: Optional[int] = None
        self._last_pct = -1

    def set_max(self, value) -> None:
        try:
            self._max = int(value)
        except (TypeError, ValueError):
            self._max = None

    def set_progress(self, value) -> None:
        try:
            count = float(value)
        except (TypeError, ValueError):
            return
        if self._max:
            total = self._max if self._max > 0 else 1
            pct = int(min(100, max(0, count / total * 100)))
        else:
            pct = int(min(100, max(0, count)))
        if pct == self._last_pct:
            return
        self._last_pct = pct
        if self._progress:
            self._progress(pct, 100, pct)

    def set_status(self, text) -> None:
        text = str(text)
        if self._status:
            self._status(text)
        if self._log:
            self._log(text)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "setStatus": self.set_status,
            "setProgress": self.set_progress,
            "setMax": self.set_max,
            "setMaxProgress": self.set_max,
            "clearProgress": lambda: None,
        }


def _callback(progress: Optional[ProgressCB], status: Optional[StatusCB],
              log_cb: Optional[LogCB]) -> Dict[str, Any]:
    return _MllProgress(progress, status, log_cb).as_dict()


def installed_version_ids() -> List[str]:
    d = paths.data_dir() / "versions"
    if not d.exists():
        return []
    return [p.name for p in d.iterdir() if p.is_dir()]


def version_installed(version_id: str) -> bool:
    return (paths.data_dir() / "versions" / version_id).exists()


def latest_version() -> tuple:
    try:
        latest = _mll().utils.get_latest_version()
    except Exception:
        return ("", "")
    if isinstance(latest, dict):
        return (str(latest.get("release", "")), str(latest.get("snapshot", "")))
    return (str(getattr(latest, "stable", "") or getattr(latest, "release", "")),
            str(getattr(latest, "snapshot", "")))


def available_versions(release_type: str = "release", limit: int = 300) -> List[str]:
    try:
        return [vid for vid, vtype, _ in fetch_versions() if vtype == release_type][:limit]
    except Exception:
        return []


def all_versions() -> List[tuple]:
    mll = _mll()
    raw = None
    fn = getattr(mll, "list_versions", None)
    if callable(fn):
        try:
            raw = fn()
        except Exception:
            raw = None
    if raw is None:
        get_list = getattr(mll.utils, "get_version_list", None)
        if not callable(get_list):
            raise RuntimeError("minecraft-launcher-lib: нет списка версий")
        raw = get_list()

    out: List[tuple] = []
    if isinstance(raw, dict):
        for vid, vtype in raw.items():
            out.append((str(vid), str(vtype), 0))
    else:
        for v in raw:
            if isinstance(v, dict):
                when = v.get("releaseTime")
                stamp = int(when.timestamp()) if hasattr(when, "timestamp") else 0
                out.append((str(v.get("id", "")), str(v.get("type", "release")), stamp))
            else:
                out.append((str(v), "release", 0))
    out = [t for t in out if t[0]]

    out.sort(key=lambda p: (p[2], utils.version_key(p[0])), reverse=True)
    out.sort(key=_version_type_rank)
    return out


def _version_type_rank(item: tuple) -> int:
    vtype = item[1]
    return {"release": 0, "snapshot": 1, "old_beta": 2, "old_alpha": 3}.get(vtype, 4)


def fetch_versions(force: bool = False) -> List[tuple]:
    cache = paths.cache_dir() / "versions.json"
    if not force and cache.exists() and (time.time() - cache.stat().st_mtime) < 3600:
        data = utils.read_json(cache, None)
        if data:
            return [(str(v[0]), str(v[1]), int(v[2]) if len(v) > 2 else 0)
                    for v in data]
    versions = all_versions()
    try:
        utils.write_json(cache, versions)
    except Exception:
        pass
    return versions


def install_vanilla(mc_version: str, loader_version: str = "", progress=None, status=None,
                    log_cb=None) -> str:
    mll = _mll()
    (status or (lambda t: None))(get_config().t("installing"))
    mll.install.install_minecraft_version(mc_version, str(paths.data_dir()),
                                          callback=_callback(progress, status, log_cb))
    return mc_version


def install_forge(mc_version: str, loader_version: str = "", progress=None, status=None,
                  log_cb=None) -> str:
    mll = _mll()
    status_cb = status or (lambda t: None)
    status_cb("Forge…")
    cb = _callback(progress, status, log_cb)
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is not None:
        return install_loader("forge", mc_version, loader_version,
                              progress, status, log_cb)
    if not loader_version:
        loader_version = mll.forge.find_forge_version(mc_version)
        if not loader_version:
            raise RuntimeError(f"Для {mc_version} нет подходящей версии Forge")
    mll.forge.install_forge_version(loader_version, str(paths.data_dir()),
                                    callback=cb)
    candidates = _find_loader_version(loader_version, mc_version, ("forge",))
    if not candidates:
        raise RuntimeError("Forge установлен, но версия не найдена в versions/")
    candidates.sort(key=utils.version_key, reverse=True)
    return candidates[0]


def _find_loader_version(loader_version: str, mc_version: str,
                         keywords: tuple) -> List[str]:
    ids = installed_version_ids()
    target = (loader_version or "").lower()
    base = (mc_version or "").lower()

    def has_kw(v: str) -> bool:
        return any(k in v.lower() for k in keywords)

    if target:
        exact = [v for v in ids if v.lower() == target]
        if exact:
            return exact
        near = [v for v in ids if target in v.lower() or v.lower() in target]
        if near:
            return near

    if base:
        match = [v for v in ids if v.lower().startswith(base) and has_kw(v)]
        if match:
            return match
        match = [v for v in ids if base in v.lower() and has_kw(v)]
        if match:
            return match
    return []


def latest_loader_version(loader: str, mc_version: str) -> str:
    versions = loader_versions(loader, mc_version)
    if not versions:
        return ""
    try:
        return max(versions, key=utils.version_key)
    except Exception:
        return versions[0]


def installer_java(mc_version: str = "") -> Optional[str]:
    try:
        info = javamod.find_java(mc_version) if mc_version else None
        if info is not None:
            return str(info.path)
    except Exception as e:
        utils.log(f"Не удалось подобрать Java для установщика: {e}", "WARN")
    return None


def check_loader_support(loader: str, mc_version: str) -> None:
    mll = _mll()
    if getattr(mll, "mod_loader", None) is None:
        return
    try:
        ml = _mod_loader(mll, loader)
        if ml is not None and ml.is_minecraft_version_supported(mc_version):
            return
    except Exception as e:
        utils.log(f"Проверка поддержки {loader}/{mc_version} не удалась: {e}", "WARN")
        return
    name = LOADER_LABELS.get(loader, loader.capitalize())
    raise RuntimeError(
        f"{name} не поддерживает Minecraft {mc_version}. "
        f"Выберите версию из списка, который показывает {name}.")


def _warn_weak_java(loader: str, mc_version: str, java: Optional[str]) -> None:
    if not java:
        return
    need = javamod.required_java(mc_version)
    try:
        info = javamod.probe_java(Path(java))
    except Exception:
        info = None
    if info is None or info.major >= need:
        return
    utils.log(f"{loader}: для Minecraft {mc_version} нужна Java {need}, "
              f"а установщик запустится на Java {info.major} "
              f"({info.version}) — скорее всего не сработает", "WARN")


def install_loader(loader: str, mc_version: str, loader_version: str = "",
                   progress=None, status=None, log_cb=None) -> str:
    if not loader_enabled(loader):
        raise RuntimeError(
            f"Установка {LOADER_LABELS.get(loader, loader)} пока недоступна — "
            "поддержка отложена")
    mll = _mll()
    cb = _callback(progress, status, log_cb)
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is None:
        raise RuntimeError("minecraft-launcher-lib не поддерживает mod_loader")

    check_loader_support(loader, mc_version)
    if not loader_version:
        loader_version = latest_loader_version(loader, mc_version)
    if not loader_version:
        raise RuntimeError(f"Нет версий {loader} для Minecraft {mc_version}")

    java = installer_java(mc_version)
    if java:
        utils.log(f"Установщик {loader} будет запущен через {java}")
        _warn_weak_java(loader, mc_version, java)
    else:
        import shutil as _shutil

        on_path = _shutil.which("java")
        if not on_path:
            need = javamod.required_java(mc_version)
            raise JavaMissing(
                f"Для установки {loader.capitalize()} нужна Java, а её нет "
                f"ни в системе, ни в PATH. Minecraft {mc_version} работает "
                f"на Java {need} — скачайте её в разделе «Java», иначе "
                f"установщик не запустится.", need)
        java = on_path
        utils.log(f"Своей Java нет, установщик пойдёт через {java}", "WARN")

    kwargs: Dict[str, Any] = {"callback": cb}
    if loader_version:
        kwargs["loader_version"] = loader_version
    if java:
        kwargs["java"] = java

    ml = _mod_loader(mll, loader)
    if ml is None:
        raise RuntimeError("minecraft-launcher-lib не поддерживает mod_loader")
    try:
        installed = ml.install(
            mc_version, str(paths.data_dir()), **kwargs)
    except subprocess.CalledProcessError as e:
        detail = ""
        for stream in (getattr(e, "stderr", None), getattr(e, "output", None)):
            if not stream:
                continue
            text = (stream.decode("utf-8", "replace")
                    if isinstance(stream, bytes) else str(stream))
            text = text.strip()
            if text:
                detail = text[-2000:]
                break
        utils.log(f"Установщик {loader} завершился с кодом {e.returncode}: "
                  f"{e.cmd}" + (f"\n{detail}" if detail else ""), "ERROR")
        raise RuntimeError(
            f"Установщик {loader} {loader_version} не смог установить "
            f"Minecraft {mc_version} (код {e.returncode}). "
            f"Подробности — в логе лаунчера.") from e
    except Exception as e:
        if type(e).__name__ == "VersionNotFound":
            raise RuntimeError(
                f"{loader.capitalize()} не создал профиль для Minecraft "
                f"{mc_version}. Обычно это значит, что установщик запустился "
                f"на слишком старой Java — для этой версии игры нужна "
                f"Java {javamod.required_java(mc_version)}.") from e
        raise
    return _version_on_disk(loader, mc_version, str(installed), loader_version)


def _version_on_disk(loader: str, mc_version: str, reported: str,
                     loader_version: str) -> str:
    versions = paths.data_dir() / "versions"
    if (versions / reported / f"{reported}.json").exists():
        return reported
    utils.log(f"{loader}: папка versions/{reported} не найдена, ищу на диске",
              "WARN")
    found = _match_loader_folder(loader, mc_version, loader_version)
    if not found:
        raise RuntimeError(
            f"{loader.capitalize()} отчитался об установке, но в versions/ "
            f"нет папки {reported}. Переустановите версию.")
    found.sort(key=utils.version_key, reverse=True)
    utils.log(f"{loader}: на диске найдена папка {found[0]}", "INFO")
    return found[0]


def _match_loader_folder(loader: str, mc_version: str,
                         loader_version: str = "") -> List[str]:
    base = (mc_version or "").lower()
    lver = (loader_version or "").lower()
    name = loader.lower()
    out = []
    for vid in installed_version_ids():
        low = vid.lower()
        if base and base not in low:
            continue
        if name and name not in low:
            continue
        if lver and lver not in low:
            continue
        out.append(vid)
    return out


def install_fabric(mc_version: str, loader_version: str = "", progress=None, status=None,
                   log_cb=None) -> str:
    mll = _mll()
    status_cb = status or (lambda t: None)
    status_cb(get_config().t("installing_short"))
    cb = _callback(progress, status, log_cb)
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is not None:
        return install_loader("fabric", mc_version, loader_version,
                              progress, status, log_cb)
    if not loader_version:
        loader_version = mll.fabric.get_latest_loader_version()
    mll.fabric.install_fabric(mc_version, str(paths.data_dir()), loader_version,
                              callback=cb)
    expected = f"fabric-loader-{loader_version}-{mc_version}"
    found = _find_loader_version(expected, mc_version, ("fabric",))
    return found[0] if found else expected


def loader_versions(loader: str, mc_version: str) -> List[str]:
    mll = _mll()
    cb = _callback(None, None, None)
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is not None:
        try:
            ml = _mod_loader(mll, loader)
            if ml is not None:
                return list(ml.get_loader_versions(mc_version, stable_only=False))
        except Exception as e:
            utils.log(f"loader_versions({loader}) через mod_loader: {e}", "WARN")
    for mod_name, fn_name in (("neoforge", "list_neoforge_versions"),
                              ("fabric", "get_all_loader_versions"),
                              ("quilt", "get_all_loader_versions")):
        if mod_name != loader:
            continue
        mod = getattr(mll, mod_name, None)
        fn = getattr(mod, fn_name, None) if mod else None
        if not callable(fn):
            continue
        try:
            return [v for v in fn() if mc_version in str(v) or True]
        except Exception:
            continue
    forge = getattr(mll, "forge", None)
    if loader == "forge" and forge is not None:
        try:
            found = forge.find_forge_version(mc_version)
            return [found] if found else []
        except Exception:
            pass
    _ = cb
    return []


def install_neoforge(mc_version: str, loader_version: str = "", progress=None, status=None,
                     log_cb=None) -> str:
    mll = _mll()
    cb = _callback(progress, status, log_cb)
    mod_loader = getattr(mll, "mod_loader", None)
    if mod_loader is not None:
        installed = install_loader("neoforge", mc_version, loader_version,
                                   progress, status, log_cb)
        return str(installed or f"neoforge-{loader_version}")
    if not loader_version:
        loader_version = mll.neoforge.list_neoforge_versions()[0]
    mll.neoforge.install_neoforge_version(loader_version, str(paths.data_dir()),
                                          callback=cb)
    return f"neoforge-{loader_version}"


INSTALLERS = {
    "vanilla": (install_vanilla, "mc_version"),
    "forge": (install_forge, "loader_version"),
    "fabric": (install_fabric, "loader_version"),
    "neoforge": (install_neoforge, "loader_version"),
}
for _off in DISABLED_LOADERS:
    INSTALLERS.pop(_off, None)


def installer_for(loader: str):
    entry = INSTALLERS.get(loader)
    return entry[0] if entry else None


def build_instance_id(mc_version: str, loader: str, loader_version: str = "") -> str:
    base = sanitize_id(mc_version)
    if loader == "vanilla":
        return base
    if loader == "forge":
        fv = loader_version.split("-")[0] if loader_version else "?"
        return f"forge-{base}-{fv}"
    if loader == "fabric":
        return f"fabric-{base}-{loader_version or 'latest'}"
    if loader == "quilt":
        return f"quilt-{base}-{loader_version or 'latest'}"
    if loader == "neoforge":
        return f"neoforge-{base}"
    if loader == "optifine":
        return f"optifine-{base}"
    return f"{loader}-{base}"


class VersionMissing(RuntimeError):
    pass


class JavaMissing(RuntimeError):
    def __init__(self, message: str, major: int = 0):
        super().__init__(message)
        self.major = major


@dataclass
class LaunchResult:
    process: Any
    instance: Instance
    command: List[str]
    java: Optional[javamod.JavaInfo] = None


def resolve_java(inst: Instance,
                 cached_only: bool = False) -> Optional[javamod.JavaInfo]:
    if inst.java_path and Path(inst.java_path).exists():
        path = Path(inst.java_path)
        info = (javamod.probe_java_cached(path) if cached_only
                else javamod.probe_java(path))
        if info:
            return info
    if cached_only:
        return javamod.find_java_cached(inst.base_mc)
    return javamod.find_java(inst.base_mc)


def needs_java(inst: Instance) -> Optional[int]:
    info = resolve_java(inst)
    if info is None:
        return javamod.required_java(inst.base_mc)
    state = javamod.java_ok(inst.base_mc, info)
    if state != "ok":
        return javamod.required_java(inst.base_mc)
    return None


def _account_options(inst: Instance) -> tuple[Dict[str, Any], str]:
    cfg = get_config()
    accounts = cfg.get("accounts") or []
    current = cfg.get("current_account")

    chosen = None
    for a in accounts:
        if a.get("id") == current:
            chosen = a
            break
    if chosen is None and accounts:
        chosen = accounts[0]

    if chosen and chosen.get("type") == "ely" and chosen.get("accessToken"):
        return ({
            "username": chosen.get("username", "Player"),
            "uuid": chosen.get("uuid", ""),
            "token": chosen.get("accessToken", ""),
        }, "ely")

    nick = (chosen or {}).get("username") or cfg.get("nickname") or "Player"
    return ({
        "username": nick,
        "uuid": utils.offline_uuid(nick),
        "token": "0",
    }, "offline")


def _minecraft_options(mll, options: Dict[str, Any]):
    types_mod = getattr(mll, "types", None)
    opts_cls = getattr(types_mod, "MinecraftOptions", None)
    if opts_cls is None:
        return options
    fields = set(getattr(opts_cls, "__annotations__", {}) or {})
    if not fields:
        return options
    opts = {k: v for k, v in options.items() if k in fields}
    for key in ("resolutionWidth", "resolutionHeight"):
        if key in opts and not isinstance(opts[key], str):
            opts[key] = str(opts[key])
    for required in ("defaultExecutablePath", "launcherName", "launcherVersion"):
        if required in fields and required not in opts:
            if required == "defaultExecutablePath":
                opts[required] = options.get("executablePath", "java")
            elif required == "launcherName":
                opts[required] = "Fimple Launcher"
            else:
                opts[required] = paths.app_version()
    return opts


def launch(inst: Instance, on_log: Optional[LogCB] = None,
           on_exit: Optional[Callable[[float], None]] = None,
           extra_jvm: str = "") -> LaunchResult:
    import subprocess

    mll = _mll()
    cfg = get_config()

    vdir = paths.data_dir() / "versions" / inst.mc_version
    if not (vdir / f"{inst.mc_version}.json").exists():
        utils.log(f"Нет файла {vdir / (inst.mc_version + '.json')}", "ERROR")
        raise VersionMissing(
            f"Версия {inst.mc_version} для «{inst.id}» не установлена или её "
            f"файлы удалены. Переустановите версию — иначе игру не запустить.")

    java = resolve_java(inst)
    if java is None:
        raise RuntimeError("Java не найдена — установите Java в разделе «Java»")

    ram_mb = int(cfg.get("ram") or 0) or 0
    if cfg.get("auto_ram", True):
        from .config import suggested_ram_mb
        ram_mb = suggested_ram_mb()

    account, account_type = _account_options(inst)
    jvm_args = [
        f"-Xmx{ram_mb}M",
        f"-Xms{max(512, ram_mb // 4)}M",
        "-XX:+UseG1GC" if ram_mb >= 4096 else "-XX:+UseParallelGC",
        "-Dfile.encoding=UTF-8",
    ]

    if account_type == "ely":
        jar = paths.authlib_jar()
        if jar.exists():
            jvm_args.append(f"-javaagent:{jar}=ely.by")
        else:
            utils.log("authlib-injector не найден — вход будет оффлайн", "WARN")
            account = {"username": account["username"],
                       "uuid": utils.offline_uuid(account["username"]), "token": "0"}
            account_type = "offline"

    extra = (inst.jvm_args or "").strip() or (cfg.get("jvm_args") or "").strip() or extra_jvm
    if extra:
        jvm_args.extend(extra.split())

    options: Dict[str, Any] = {
        "username": account["username"],
        "uuid": account["uuid"],
        "token": account.get("token") or "0",
        "executablePath": str(java.path),
        "jvmArguments": jvm_args,
        "gameDirectory": str(inst.path),
        "customResolution": True,
        "launcherName": "Fimple Launcher",
        "launcherVersion": paths.app_version(),
    }
    options["resolutionWidth"] = str(inst.window_width)
    options["resolutionHeight"] = str(inst.window_height)
    command = mll.command.get_minecraft_command(inst.mc_version, str(paths.data_dir()),
                                                _minecraft_options(mll, options))

    utils.log(f"Запуск {inst.id}: {str(java.path)} ({java.version}), {ram_mb} МБ")
    repo().register_launch(inst)

    startupinfo, creationflags = utils.hidden_console_args(cfg.get("hide_console", True))

    proc = subprocess.Popen(
        command, cwd=str(paths.data_dir()),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if on_log else subprocess.DEVNULL,
        stderr=subprocess.STDOUT if on_log else subprocess.DEVNULL,
        startupinfo=startupinfo, creationflags=creationflags)

    if on_exit:
        def watcher():
            start = time.time()
            if on_log:
                try:
                    for raw in proc.stdout:
                        on_log(raw.decode("utf-8", "ignore").rstrip())
                except Exception:
                    pass
            try:
                proc.wait()
            except Exception:
                pass
            duration = time.time() - start
            repo().add_playtime(inst, duration)
            on_exit(duration)

        import threading

        threading.Thread(target=watcher, daemon=True).start()

    return LaunchResult(process=proc, instance=inst, command=command, java=java)
