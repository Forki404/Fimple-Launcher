from __future__ import annotations

import os
import platform
import re
import shutil
import threading
import time
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, List, Optional

from . import paths, utils
from .config import get_config

ADOPTIUM_API = "https://api.adoptium.net/v3"
USER_AGENT = "FimpleLauncher/1.0"

ProgressCB = Callable[[int, int, int], None]
StatusCB = Callable[[str], None]


@dataclass
class JavaInfo:
    path: Path
    major: int = 0
    version: str = ""
    vendor: str = ""
    arch: str = ""
    bundled: bool = False
    custom: bool = False

    @property
    def name(self) -> str:
        return self.version or f"Java {self.major}" if self.major else "Java"

    @property
    def directory(self) -> Path:
        return self.path.parent.parent


_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_mc_version(mc_version: str) -> tuple:
    base = (mc_version or "").strip().lower().split("-")[0]
    m = _VERSION_RE.match(base)
    if not m:
        return (1, 21, 0)
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3) or 0)
    return (major, minor, patch)


def required_java(mc_version: str) -> int:
    v = parse_mc_version(mc_version)
    if v >= (1, 21):
        return 25
    if v >= (1, 20, 5):
        return 21
    if v >= (1, 17):
        return 21
    return 8


def java_candidates(mc_version: str) -> List[int]:
    v = parse_mc_version(mc_version)
    if v >= (1, 21):
        return [25, 21]
    if v >= (1, 17):
        return [21]
    return [8, 21]


def preferred_java(mc_version: str = "") -> int:
    if mc_version:
        return required_java(mc_version)
    pref = str(get_config().get("java_major_pref") or "auto").strip().lower()
    if pref in ("21", "25"):
        return int(pref)
    return 25 if _latest_mc_needs_25() else 21


def _latest_mc_needs_25() -> bool:
    try:
        from . import instances as inst
        from .utils import version_key

        items = inst.repo().all()
        if not items:
            return True
        newest = max(items, key=lambda i: version_key(i.base_mc))
        return parse_mc_version(newest.base_mc) >= (1, 21)
    except Exception:
        return True


def _version_from_output(text: str) -> tuple:
    text = (text or "").strip()
    if not text:
        return 0, "", ""
    vendor = "Oracle" if "Oracle" in text else ("Adoptium" if "Temurin" in text or "Eclipse" in text
                                                else ("OpenJDK" if "OpenJDK" in text else "Unknown"))
    patterns = [
        r'version\s+"([^"]+)"',
        r'openjdk\s+(\d+)',
        r'java\s+version\s+"([^"]+)"',
    ]
    raw = ""
    for p in patterns:
        m = re.search(p, text)
        if m:
            raw = m.group(1)
            break
    if not raw:
        m = re.search(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?', text)
        raw = m.group(0) if m else ""
    if not raw:
        return 0, "", vendor
    nums = re.findall(r"\d+", raw)
    if not nums:
        return 0, raw, vendor
    if raw.startswith("1.") and len(nums) >= 2:
        major = int(nums[1])
    else:
        major = int(nums[0])
    return major, raw, vendor


_PROBE_CACHE: dict = {}
_PROBE_LOCK = threading.Lock()


def _probe_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _path_stamp(path: Path):
    try:
        st = path.stat()
        return (int(st.st_mtime_ns), int(st.st_size))
    except OSError:
        return None


def _java_flags(path: Path) -> tuple:
    key = _probe_key(path)
    bundled = _probe_key(paths.java_dir()) in key
    custom_path = get_config().get("custom_java")
    custom = bool(custom_path) and _probe_key(Path(custom_path)) == key
    return bundled, custom


def _cached_probe(path: Path, stamp) -> Optional[JavaInfo]:
    if stamp is None:
        return None
    with _PROBE_LOCK:
        hit = _PROBE_CACHE.get(_probe_key(path))
    if not hit or hit[0] != stamp:
        return None
    bundled, custom = _java_flags(path)
    return replace(hit[1], bundled=bundled, custom=custom)


def probe_java_cached(path: Path) -> Optional[JavaInfo]:
    try:
        if not path.exists():
            return None
        return _cached_probe(path, _path_stamp(path))
    except Exception:
        return None


def probe_java(path: Path) -> Optional[JavaInfo]:
    try:
        if not path.exists():
            return None
        stamp = _path_stamp(path)
        cached = _cached_probe(path, stamp)
        if cached is not None:
            return cached

        proc = utils.run_hidden([str(path), "-version"],
                                capture_output=True, timeout=12)
        out = (proc.stdout or b"").decode("utf-8", "ignore") + (proc.stderr or b"").decode("utf-8", "ignore")
        major, ver, vendor = _version_from_output(out)
        if not major:
            return None
        bundled, custom = _java_flags(path)
        info = JavaInfo(path=path, major=major, version=ver, vendor=vendor,
                        arch=platform.machine(), bundled=bundled, custom=custom)
        if stamp is not None:
            with _PROBE_LOCK:
                _PROBE_CACHE[_probe_key(path)] = (stamp, info)
        return info
    except Exception:
        return None


def _java_bin(root: Path) -> Optional[Path]:
    exe = "java.exe" if os.name == "nt" else "java"
    cand = root / "bin" / exe
    return cand if cand.exists() else None


def find_bundled_javas() -> List[JavaInfo]:
    out: List[JavaInfo] = []
    base = paths.java_dir()
    if not base.exists():
        return out
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        exe = _java_bin(child)
        if not exe:
            found = None
            for sub in child.iterdir():
                if sub.is_dir():
                    exe = _java_bin(sub)
                    if exe:
                        found = exe
                        break
            if not found:
                continue
            exe = found
        info = probe_java(exe)
        if info:
            out.append(info)
    return out


def _common_system_paths() -> List[Path]:
    exe = "java.exe" if os.name == "nt" else "java"
    roots: List[Path] = []
    if os.name == "nt":
        for env in ("JAVA_HOME", "JDK_HOME", "JRE_HOME"):
            v = os.environ.get(env)
            if v:
                roots.append(Path(v))
        for base in ("C:\\Program Files\\Java", "C:\\Program Files\\Eclipse Adoptium",
                     "C:\\Program Files\\Microsoft", "C:\\Program Files\\Zulu",
                     "C:\\Program Files\\Amazon Corretto", "C:\\Program Files (x86)\\Java",
                     str(Path.home() / ".jdks"), str(Path.home() / ".gradle/jdks"),
                     str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs")):
            try:
                p = Path(base)
                if p.exists():
                    roots.append(p)
            except Exception:
                pass
    elif sys_platform_darwin():
        roots = [Path("/Library/Java/JavaVirtualMachines"),
                 Path.home() / "Library/Java/JavaVirtualMachines"]
    else:
        roots = [Path("/usr/lib/jvm"), Path("/usr/java"), Path("/opt/java")]
    return scan_java_roots(roots)


def scan_java_roots(roots: List[Path], max_depth: int = 2) -> List[Path]:
    out: List[Path] = []
    seen = set()

    def add(exe: Path) -> None:
        key = str(exe)
        if key not in seen:
            seen.add(key)
            out.append(exe)

    def walk(folder: Path, depth: int) -> None:
        direct = _java_bin(folder)
        if direct:
            add(direct)
            return
        if depth <= 0 or not folder.is_dir():
            return
        try:
            children = [c for c in sorted(folder.iterdir()) if c.is_dir()]
        except OSError:
            return
        for child in children:
            j = _java_bin(child)
            if j:
                add(j)
            else:
                walk(child, depth - 1)

    for r in roots:
        try:
            if r.exists():
                walk(r, max_depth)
        except OSError:
            continue
    return out


def sys_platform_darwin() -> bool:
    import sys

    return sys.platform == "darwin"


def which_java() -> Optional[Path]:
    exe = "java.exe" if os.name == "nt" else "java"
    found = shutil.which(exe)
    return Path(found) if found else None


_JAVA_CACHE: dict = {}
_JAVA_TTL = 120.0
JAVA_CACHE_TTL = _JAVA_TTL
_JAVA_GENERATION = 0


def invalidate_java_cache() -> None:
    global _JAVA_GENERATION
    _JAVA_GENERATION += 1
    _JAVA_CACHE.clear()
    with _PROBE_LOCK:
        _PROBE_CACHE.clear()


def java_cache_generation() -> int:
    return _JAVA_GENERATION


def cached_javas() -> List[JavaInfo]:
    hit = _JAVA_CACHE.get(("all", True))
    return list(hit[1]) if hit else []


def java_cache_state() -> Optional[List[JavaInfo]]:
    hit = _JAVA_CACHE.get(("all", True))
    return list(hit[1]) if hit else None


def java_cache_age() -> Optional[float]:
    hit = _JAVA_CACHE.get(("all", True))
    return (time.monotonic() - hit[0]) if hit else None


def detect_javas(include_system: bool = True, max_age: float = _JAVA_TTL,
                 cancelled=None) -> List[JavaInfo]:
    key = ("all", bool(include_system))
    hit = _JAVA_CACHE.get(key)
    if hit and max_age > 0 and (time.monotonic() - hit[0]) <= max_age:
        return list(hit[1])
    generation = _JAVA_GENERATION
    found = _detect_javas_now(include_system, cancelled)
    if not _is_cancelled(cancelled) and generation == _JAVA_GENERATION:
        _JAVA_CACHE[key] = (time.monotonic(), list(found))
    return found


def _is_cancelled(cancelled) -> bool:
    if not cancelled:
        return False
    try:
        return bool(cancelled() if callable(cancelled) else cancelled)
    except Exception:
        return True


def _detect_javas_now(include_system: bool = True, cancelled=None) -> List[JavaInfo]:
    def stopped() -> bool:
        return _is_cancelled(cancelled)

    result: List[JavaInfo] = []
    if stopped():
        return result
    seen = set()
    for info in find_bundled_javas():
        if stopped():
            return result
        if str(info.path) not in seen:
            seen.add(str(info.path))
            result.append(info)

    custom = get_config().get("custom_java")
    if custom:
        info = probe_java(Path(custom))
        if info and str(info.path) not in seen:
            seen.add(str(info.path))
            result.insert(0, info)

    try:
        from . import instances as instmod

        instance_paths = [Path(i.java_path) for i in instmod.repo().all()
                          if i.java_path]
    except Exception:
        instance_paths = []
    for exe in instance_paths:
        if stopped():
            return result
        if not exe.exists() or str(exe) in seen:
            continue
        info = probe_java(exe)
        if info:
            seen.add(str(info.path))
            result.insert(0, info)

    if include_system:
        w = which_java()
        candidates = ([w] if w else []) + _common_system_paths()
        env_home = os.environ.get("JAVA_HOME")
        if env_home:
            j = _java_bin(Path(env_home))
            if j:
                candidates.insert(0, j)
        for c in candidates:
            if stopped():
                return result
            if not c:
                continue
            exe = c if c.name in ("java", "java.exe") else _java_bin(c)
            if not exe or not exe.exists() or str(exe) in seen:
                continue
            info = probe_java(exe)
            if info:
                seen.add(str(info.path))
                result.append(info)
    return result


def _is_javapath_shim(path) -> bool:
    return "javapath" in str(path).lower().replace("/", "\\")


def _best_java(javas: List[JavaInfo], mc_version: str,
               prefer: Optional[int] = None) -> Optional[JavaInfo]:
    if not javas:
        return None
    candidates = [prefer] if prefer else java_candidates(mc_version)
    for major in candidates:
        for j in javas:
            if j.major == major:
                return j
    for major in candidates:
        for j in javas:
            if j.major >= major:
                return j
    return max(javas, key=lambda j: (j.major, not _is_javapath_shim(j.path)))


def find_java(mc_version: str, prefer: Optional[int] = None) -> Optional[JavaInfo]:
    return _best_java(detect_javas(), mc_version, prefer)


def find_java_cached(mc_version: str,
                     prefer: Optional[int] = None) -> Optional[JavaInfo]:
    return _best_java(cached_javas(), mc_version, prefer)


def java_ok(mc_version: str, info: JavaInfo) -> str:
    primary = required_java(mc_version)
    if info.major in java_candidates(mc_version):
        return "ok"
    if info.major == 25 and primary == 21:
        return "ok"
    if info.major < primary:
        return "low"
    return "high"


def _adoptium_os() -> str:
    import sys

    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def fetch_asset(major: int) -> dict:
    import requests

    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x64"
    os_name = _adoptium_os()
    url = f"{ADOPTIUM_API}/assets/latest/{major}/hotspot"
    resp = requests.get(url, params={
        "architecture": arch,
        "image_type": "jdk",
        "os": os_name,
        "vendor": "eclipse",
        "heap_size": "normal",
    }, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}, timeout=25)
    resp.raise_for_status()
    assets = resp.json()
    if not assets:
        raise RuntimeError(f"Adoptium не нашёл JDK {major} для {os_name}/{arch}")

    prefer_ext = (".zip", ".tar.gz", ".tgz")
    best = None
    for a in assets:
        pkg = (a.get("binary") or {}).get("package") or {}
        link = pkg.get("link")
        name = pkg.get("name", "")
        if not link:
            continue
        if name.endswith(".zip"):
            return a
        if best is None:
            best = a
    for ext in (".tar.gz", ".tgz", ".zip"):
        for a in assets:
            pkg = (a.get("binary") or {}).get("package") or {}
            if (pkg.get("name") or "").endswith(ext):
                return a
    return best or assets[0]


def download_java(major: int, progress: Optional[ProgressCB] = None,
                  status: Optional[StatusCB] = None) -> JavaInfo:
    import requests

    if status:
        status(get_config().t("java_progress", major))
    asset = fetch_asset(major)
    pkg = (asset.get("binary") or {}).get("package") or {}
    url = pkg.get("link")
    name = pkg.get("name") or f"jdk-{major}.zip"
    total = int(pkg.get("size") or asset.get("size") or 0)

    if not url:
        raise RuntimeError("Adoptium не вернул ссылку на загрузку")

    tmp_dir = paths.temp_dir()
    archive = tmp_dir / name
    utils.log(f"Скачиваем {name} ({paths.human_size(total)})")

    downloaded = 0
    with requests.get(url, stream=True, timeout=60,
                      headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        if not total:
            total = int(r.headers.get("Content-Length") or 0)
        with open(archive, "wb") as f:
            for chunk in r.iter_content(1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total, int(downloaded * 100 / total) if total else 0)

    if status:
        status(get_config().t("java_extracting", major))
    target = paths.java_dir() / f"jdk-{major}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)

    extracted_name = ""
    if archive.suffix == ".zip" or name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(target)
            top = {n.split("/")[0] for n in zf.namelist() if "/" in n}
            extracted_name = top.pop() if len(top) == 1 else ""
    else:
        import tarfile

        with tarfile.open(archive) as tf:
            tf.extractall(target)
            top = {n.split("/")[0] for n in tf.getnames() if "/" in n}
            extracted_name = top.pop() if len(top) == 1 else ""

    if not (target / "bin").exists():
        inner = None
        if extracted_name and (target / extracted_name / "bin").exists():
            inner = target / extracted_name
        else:
            candidates = [d for d in target.iterdir()
                          if d.is_dir() and (_java_bin(d) is not None)]
            if len(candidates) == 1:
                inner = candidates[0]
        if inner is not None:
            for item in list(inner.iterdir()):
                dest = target / item.name
                if dest.exists():
                    continue
                shutil.move(str(item), str(dest))
            try:
                inner.rmdir()
            except OSError:
                pass

    try:
        archive.unlink(missing_ok=True)
    except Exception:
        pass

    exe = _java_bin(target)
    if not exe:
        for p in target.rglob("java.exe" if os.name == "nt" else "java"):
            if p.parent.name == "bin":
                exe = p
                break
    if not exe or not exe.exists():
        raise RuntimeError("После распаковки не найден исполняемый файл java")

    if os.name != "nt":
        bin_dir = exe.parent
        for item in bin_dir.iterdir():
            if item.is_file():
                try:
                    item.chmod(0o755)
                except OSError:
                    pass
        try:
            bin_dir.chmod(0o755)
        except OSError:
            pass

    info = probe_java(exe)
    if not info:
        raise RuntimeError("Не удалось определить версию скачанной Java")
    utils.log(f"Java {major} установлена: {info.version}")
    invalidate_java_cache()
    return info


def delete_bundled(info: JavaInfo) -> None:
    root = info.directory
    if str(paths.java_dir()) in str(root):
        shutil.rmtree(root, ignore_errors=True)
    invalidate_java_cache()
