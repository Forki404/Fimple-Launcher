from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time
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
REMOVE_DIRS = ("__pycache__", "launcher", "assets", "lib", "_internal")


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


@dataclass
class ApplyResult:
    entry: Path
    deferred: bool = False

    def __fspath__(self) -> str:
        return os.fspath(self.entry)

    def __str__(self) -> str:
        return str(self.entry)


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


def _ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _powershell_path() -> Optional[str]:
    if os.name != "nt":
        return None
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR") or r"C:\Windows"
    exe = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if exe.is_file():
        return str(exe)
    return shutil.which("powershell.exe")


def _launcher_pids() -> List[int]:
    pids = [os.getpid()]
    try:
        import psutil

        parent = psutil.Process(os.getpid()).parent()
        if parent is None or parent.pid in pids:
            return pids
        try:
            same_exe = (os.path.normcase(os.path.abspath(parent.exe()))
                        == os.path.normcase(os.path.abspath(sys.executable)))
        except (psutil.Error, OSError):
            same_exe = False
        if same_exe:
            pids.append(parent.pid)
    except Exception:
        pass
    return pids


def _launch_command(entry: Path) -> List[str]:
    if entry.suffix.lower() in (".exe", ".bat", ".cmd"):
        return [str(entry)]
    return utils.console_free_cmd([sys.executable, str(entry)])


def _windows_update_script(base: Path, staging: Path, archive: Path,
                           entry: Path, version: str, launch: List[str],
                           ready: Path) -> str:
    version_json = json.dumps(
        {"version": version, "updated": int(time.time())}, indent=2) + "\n"
    version_b64 = base64.b64encode(version_json.encode("utf-8")).decode("ascii")
    wait_ids = ", ".join(str(pid) for pid in _launcher_pids())
    args = ", ".join(_ps_quote(f'"{arg}"') for arg in launch[1:])
    preserve = ", ".join(_ps_quote(name) for name in sorted(PRESERVE_DIRS))
    old_dirs = ", ".join(_ps_quote(name) for name in REMOVE_DIRS)

    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$target = {_ps_quote(str(base))}",
        f"$staging = {_ps_quote(str(staging))}",
        f"$archive = {_ps_quote(str(archive))}",
        f"$entry = {_ps_quote(str(entry))}",
        f"$version = {_ps_quote(version)}",
        f"$ready = {_ps_quote(str(ready))}",
        f"$launchFile = {_ps_quote(launch[0])}",
        f"$launchArgs = @({args})",
        f"$waitIds = @({wait_ids})",
        f"$versionJson = [System.Text.Encoding]::UTF8.GetString("
        f"[System.Convert]::FromBase64String({_ps_quote(version_b64)}))",
        f"$preserve = @({preserve})",
        f"$oldDirs = @({old_dirs})",
        "$logDir = Join-Path $target 'Minecraft\\logs'",
        "$log = Join-Path $logDir 'update.log'",
        "",
        "function Write-Log([string]$message) {",
        "    try {",
        "        if (-not (Test-Path -LiteralPath $logDir)) {",
        "            New-Item -ItemType Directory -Path $logDir -Force | Out-Null",
        "        }",
        "        $line = '[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] ' + $message",
        "        Add-Content -LiteralPath $log -Value $line -Encoding UTF8",
        "    } catch { }",
        "}",
        "",
        "function Show-Error([string]$message) {",
        "    Write-Log ('ERROR: ' + $message)",
        "    try {",
        "        $shell = New-Object -ComObject WScript.Shell",
        "        $shell.Popup(($message + [Environment]::NewLine + [Environment]::NewLine + 'Подробности: ' + $log), 0, 'Fimple Launcher', 16) | Out-Null",
        "    } catch { }",
        "}",
        "",
        "function Remove-Old {",
        "    Get-ChildItem -LiteralPath $target -Force | ForEach-Object {",
        "        $name = $_.Name",
        "        if ($preserve -contains $name) { return }",
        "        if ($name.StartsWith('.')) { return }",
        "        if ($_.PSIsContainer) {",
        "            if ($oldDirs -contains $name) {",
        "                Remove-Item -LiteralPath $_.FullName -Recurse -Force",
        "            }",
        "        } else {",
        "            Remove-Item -LiteralPath $_.FullName -Force",
        "        }",
        "    }",
        "}",
        "",
        "function Copy-New {",
        "    robocopy $staging $target /E /R:3 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null",
        "    $code = $LASTEXITCODE",
        "    if (($null -eq $code) -or ($code -ge 8)) {",
        "        throw ('robocopy завершился с кодом ' + $code)",
        "    }",
        "}",
        "",
        "try {",
        "    Set-Content -LiteralPath $ready -Value $PID -Encoding ASCII",
        "    Write-Log 'Начинаю установку обновления'",
        "    foreach ($waitId in $waitIds) {",
        "        try { Wait-Process -Id $waitId -Timeout 180 -ErrorAction SilentlyContinue } catch { }",
        "    }",
        "    Start-Sleep -Milliseconds 800",
        "",
        "    Get-Process -ErrorAction SilentlyContinue | Where-Object {",
        "        try { $_.Path -and ((Split-Path -Parent $_.Path) -eq $target) } catch { $false }",
        "    } | Stop-Process -Force -ErrorAction SilentlyContinue",
        "",
        "    $deadline = (Get-Date).AddSeconds(60)",
        "    $done = $false",
        "    while (-not $done) {",
        "        try {",
        "            if (Test-Path -LiteralPath $entry) {",
        "                $stream = $null",
        "                try {",
        "                    $stream = [System.IO.File]::Open($entry, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)",
        "                } finally {",
        "                    if ($null -ne $stream) { $stream.Dispose() }",
        "                }",
        "            }",
        "            Remove-Old",
        "            Copy-New",
        "            $done = $true",
        "        } catch {",
        "            if ((Get-Date) -gt $deadline) { throw }",
        "            Start-Sleep -Milliseconds 500",
        "        }",
        "    }",
        "",
        "    $utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false",
        "    [System.IO.File]::WriteAllText((Join-Path $target 'version.json'), $versionJson, $utf8)",
        "    Write-Log ('Скопировано: ' + $version)",
        "",
        "    if ($launchArgs.Count -gt 0) {",
        "        Start-Process -FilePath $launchFile -ArgumentList $launchArgs -WorkingDirectory $target",
        "    } else {",
        "        Start-Process -FilePath $launchFile -WorkingDirectory $target",
        "    }",
        "    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue",
        "    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue",
        "    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue",
        "    Write-Log 'Обновление установлено, лаунчер запущен'",
        "    exit 0",
        "} catch {",
        "    Remove-Item -LiteralPath $ready -Force -ErrorAction SilentlyContinue",
        "    Show-Error ('Не удалось установить обновление: ' + $_.Exception.Message + '. Закройте все окна лаунчера и запустите его снова.')",
        "    exit 1",
        "}",
    ]
    return "\r\n".join(lines) + "\r\n"


def _schedule_windows_update(base: Path, staging: Path, archive: Path,
                             entry: Path, version: str) -> None:
    powershell = _powershell_path()
    if not powershell:
        raise RuntimeError("PowerShell не найден")

    ready = paths.temp_dir() / (
        f"update-helper-{os.getpid()}-{int(time.time() * 1000)}.ready")

    launch = _launch_command(entry)
    script = _windows_update_script(base, staging, archive, entry, version,
                                    launch, ready)
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    cmd = [powershell, "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
           "Bypass", "-WindowStyle", "Hidden", "-EncodedCommand", encoded]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    popen_args = dict(
        cwd=str(base),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    try:
        proc = subprocess.Popen(
            cmd, creationflags=flags | 0x01000000, **popen_args)
    except OSError:
        proc = subprocess.Popen(cmd, creationflags=flags, **popen_args)

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if ready.is_file() and proc.poll() is None:
            utils.log("Запущен отдельный процесс установки обновления")
            return
        if proc.poll() is not None:
            break
        time.sleep(0.1)

    try:
        proc.terminate()
        proc.wait(timeout=2)
    except Exception:
        pass
    try:
        ready.unlink(missing_ok=True)
    except OSError:
        pass
    raise RuntimeError("Отдельный установщик не запустился")


def _find_entry(staging: Path) -> Path:
    for cand in sorted(staging.iterdir()):
        if cand.is_file() and cand.suffix.lower() in (".exe", ".bat", ".cmd"):
            return cand
    return staging / "main.py"


def _apply_in_process(base: Path, staging: Path, archive: Path,
                      new_entry: Path, release: Release) -> Path:
    if os.name == "nt":
        _kill_running_launcher()

    for item in list(base.iterdir()):
        if item.name in PRESERVE_DIRS or item.name.startswith("."):
            continue
        if item.is_dir() and item.name in REMOVE_DIRS:
            shutil.rmtree(item, ignore_errors=True)
            continue
        if item.is_file():
            try:
                item.unlink()
            except OSError:
                pass

    try:
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
    except (OSError, shutil.Error) as e:
        if os.name == "nt" and (
                getattr(e, "winerror", None) == 32 or "WinError 32" in str(e)
                or "другим процессом" in str(e)):
            raise RuntimeError(
                "Не удалось заменить файлы лаунчера: они заняты другим "
                "процессом. Закройте все копии лаунчера и повторите обновление."
            ) from e
        raise

    shutil.rmtree(staging, ignore_errors=True)
    try:
        archive.unlink(missing_ok=True)
    except Exception:
        pass
    utils.log(f"Обновление {release.version} применено в {base}")
    return base / new_entry.name


def apply_update(archive: Path, release: Release, keep_data: bool = True,
                 status: Optional[StatusCB] = None) -> ApplyResult:
    base = paths.base_dir()
    staging = paths.temp_dir() / "update"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    extract_release(archive, staging, status=status)

    new_entry = _find_entry(staging)
    target_entry = base / new_entry.name

    if os.name == "nt":
        try:
            _schedule_windows_update(base, staging, archive, target_entry,
                                     release.version)
            utils.log(
                f"Обновление {release.version} будет установлено после выхода лаунчера")
            return ApplyResult(target_entry, deferred=True)
        except Exception as e:
            utils.log(
                f"Не удалось запустить отложенную установку ({e}); "
                f"пробую заменить файлы на месте", "WARN")

    entry = _apply_in_process(base, staging, archive, new_entry, release)
    return ApplyResult(entry, deferred=False)


def relaunch(entry: Optional[Path] = None) -> None:
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
