from __future__ import annotations

import hashlib
import os
import random
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import paths

_LOG_FILE: Optional[Path] = None
_LOG_STREAM = None


def init_logging() -> Path:
    global _LOG_FILE
    if _LOG_FILE is None:
        ts = datetime.now().strftime("%Y-%m-%d")
        _LOG_FILE = paths.logs_dir() / f"launcher-{ts}.log"
    _LOG_FILE.touch(exist_ok=True)
    return _LOG_FILE


def log(message: str, level: str = "INFO") -> str:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {message}"
    try:
        with open(paths.logs_dir() / f"launcher-{datetime.now().strftime('%Y-%m-%d')}.log",
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    stream = sys.stderr if level in ("ERROR", "WARN") else sys.stdout
    try:
        print(line, file=stream, flush=True)
    except Exception:
        pass
    return line


def format_playtime(seconds: float) -> str:
    seconds = int(max(0, seconds or 0))
    if seconds < 60:
        return f"{seconds} с"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} мин"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h} ч {m} мин"
    d, h = divmod(h, 24)
    return f"{d} д {h} ч"


def relative_time(ts: float) -> str:
    if not ts:
        return "никогда"
    diff = time.time() - ts
    if diff < 60:
        return "только что"
    if diff < 3600:
        return f"{int(diff // 60)} мин назад"
    if diff < 86400:
        return f"{int(diff // 3600)} ч назад"
    if diff < 86400 * 7:
        return f"{int(diff // 86400)} дн назад"
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y")


def offline_uuid(username: str) -> str:
    md5 = hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest()
    return str(uuid.UUID(bytes=md5))


def version_key(version: str) -> tuple:
    v = (version or "").strip().lower()
    v = v.split("-")[0]
    parts = re.split(r"[._]", v)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p), ""))
        else:
            key.append((1, 0, p))
    return tuple(key)


def human_size(num: float) -> str:
    return paths.human_size(num)


def hidden_console_args(hide_console: bool = True):
    if os.name != "nt" or not hide_console:
        return None, 0
    return None, subprocess.CREATE_NO_WINDOW


def pythonw_executable() -> Optional[str]:
    if os.name != "nt":
        return None
    if os.path.basename(sys.executable).lower() == "pythonw.exe":
        return sys.executable
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else None


def console_free_cmd(cmd: list[str]) -> list[str]:
    if not cmd or os.name != "nt":
        return cmd
    exe = cmd[0]
    if os.path.basename(exe).lower() != "python.exe":
        return cmd
    w = os.path.join(os.path.dirname(exe), "pythonw.exe")
    return [w] + cmd[1:] if os.path.exists(w) else cmd


def run_hidden(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    startupinfo, creationflags = hidden_console_args(True)
    if "input" not in kwargs:
        kwargs.setdefault("stdin", subprocess.DEVNULL)
    kwargs.setdefault("startupinfo", startupinfo)
    kwargs.setdefault("creationflags", creationflags)
    return subprocess.run(cmd, **kwargs)


def start_detached(cmd: list[str], cwd: Optional[Path] = None,
                   hide_console: bool = True) -> subprocess.Popen:
    startupinfo, creationflags = hidden_console_args(hide_console)
    env = dict(os.environ)
    env["FIMPLE_LAUNCHED"] = "1"
    return subprocess.Popen(
        cmd, cwd=str(cwd) if cwd else None,
        startupinfo=startupinfo, creationflags=creationflags,
        env=env,
    )


def open_path(path: Path) -> None:
    p = str(path)
    if os.name == "nt":
        os.startfile(p)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def read_json(path: Path, default):
    try:
        import json

        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, data) -> None:
    import json

    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def adaptive_mem_split(total_mb: int, reserve: int = 1024) -> int:
    return max(1024, int(total_mb - reserve))
