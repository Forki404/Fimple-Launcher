from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Fimple Launcher"
APP_SLUG = "Fimple-Launcher"
GITHUB_OWNER = "Forki404"
GITHUB_REPO = "Fimple-Launcher"

IS_FROZEN = getattr(sys, "frozen", False)


def resource_dir() -> Path:
    if IS_FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _base_dir() -> Path:
    if IS_FROZEN:
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def base_dir() -> Path:
    return _base_dir()


def data_dir() -> Path:
    d = _base_dir() / "Minecraft"
    d.mkdir(parents=True, exist_ok=True)
    return d


def instances_dir() -> Path:
    d = data_dir() / "instances"
    d.mkdir(parents=True, exist_ok=True)
    return d


def versions_file() -> Path:
    return data_dir() / "versions.json"


def settings_file() -> Path:
    return data_dir() / "settings.json"


def playtime_file() -> Path:
    return data_dir() / "playtime.json"


def runtime_dir() -> Path:
    d = data_dir() / "runtime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def java_dir() -> Path:
    d = runtime_dir() / "java"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_dir() -> Path:
    d = data_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def logs_dir() -> Path:
    d = data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def authlib_jar() -> Path:
    candidates = [
        data_dir() / "authlib-injector-1.2.7.jar",
        _base_dir() / "authlib-injector-1.2.7.jar",
        _base_dir() / "Minecraft" / "authlib-injector-1.2.7.jar",
        resource_dir() / "authlib-injector-1.2.7.jar",
        resource_dir() / "Minecraft" / "authlib-injector-1.2.7.jar",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def temp_dir() -> Path:
    d = data_dir() / "temp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def app_version() -> str:
    for vf in (base_dir() / "version.json", resource_dir() / "version.json"):
        if vf.exists():
            try:
                import json

                return json.loads(vf.read_text(encoding="utf-8")).get("version", "0.0.0")
            except Exception:
                pass
    baked = getattr(sys, "FIMPLE_VERSION", None)
    if baked:
        return str(baked)
    return "13.1.3"


def app_root_entry() -> Path | None:
    if IS_FROZEN:
        return Path(sys.executable)
    cand = _base_dir() / "main.py"
    return cand if cand.exists() else None


def safe_makedirs(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_hidden(p: Path) -> bool:
    try:
        import stat

        st = os.stat(p)
        if st.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN:
            return True
    except Exception:
        pass
    name = p.name.lower()
    return name.startswith(".") or name in ("windows", "$recycle.bin", "system volume information")


def human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024.0:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"
