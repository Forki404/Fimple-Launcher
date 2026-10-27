from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_NAME = "Fimple Launcher"
ENTRY = ROOT / "main.py"
VERSION_FILE = ROOT / "version.json"
ICON_FILE = ROOT / "icon.ico"
BANNER_FILE = ROOT / "icon.png"
JAR_FILE = ROOT / "Minecraft" / "authlib-injector-1.2.7.jar"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
SPEC_DIR = BUILD_DIR / "spec"
DEFAULT_VERSION = "13.1.1"
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    try:
        data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_VERSION
    if not isinstance(data, dict):
        return DEFAULT_VERSION
    version = str(data.get("version", "")).strip()
    return version or DEFAULT_VERSION


def ask_version() -> str:
    current = read_version()
    while True:
        answer = input(f"Введите текущую версию проекта [{current}]: ").strip()
        version = answer or current
        if VERSION_PATTERN.fullmatch(version):
            return version
        print("Нужна версия из трёх чисел, например 13.1.1.")


def save_version(version: str) -> None:
    try:
        data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["version"] = version
    data.setdefault("name", APP_NAME)
    VERSION_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check_requirements() -> tuple[Path, Path]:
    if not ICON_FILE.is_file():
        raise SystemExit(f"Не найден {ICON_FILE.name}. Положите иконку рядом с build.py.")
    if not JAR_FILE.is_file():
        raise SystemExit(f"Не найден инжектор: {JAR_FILE.relative_to(ROOT)}")
    if not ENTRY.is_file():
        raise SystemExit(f"Не найден {ENTRY.name}.")
    return ICON_FILE, JAR_FILE


def install_pyinstaller() -> None:
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller не установлен. Устанавливаю…")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def executable_path(onefile: bool) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    if onefile:
        return DIST_DIR / f"{APP_NAME}{suffix}"
    return DIST_DIR / APP_NAME / f"{APP_NAME}{suffix}"


def build_executable(version: str, onefile: bool, icon: Path) -> Path:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--icon",
        str(icon),
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
        "--hidden-import",
        "minecraft_launcher_lib",
        "--collect-submodules",
        "launcher",
        "--exclude-module",
        "tkinter",
    ]
    if BANNER_FILE.is_file():
        command += ["--add-data", f"{BANNER_FILE}{os.pathsep}."]
    command.append("--onefile" if onefile else "--onedir")
    command.append(str(ENTRY))

    print(f"\nСборка {APP_NAME} {version}…")
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit(f"PyInstaller завершился с ошибкой (код {result.returncode}).")

    exe = executable_path(onefile)
    if not exe.is_file():
        raise SystemExit(f"Не найден собранный файл: {exe}")
    return exe


def prepare_release(exe: Path, version: str, icon: Path, jar: Path) -> Path:
    release_dir = exe.parent
    (release_dir / "version.json").write_text(
        json.dumps({"version": version, "name": APP_NAME}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(icon, release_dir / icon.name)

    minecraft_dir = release_dir / "Minecraft"
    minecraft_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jar, minecraft_dir / jar.name)
    return release_dir


def create_zip(release_dir: Path, version: str) -> Path:
    zip_path = ROOT / f"{APP_NAME} {version}.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(release_dir).as_posix())
    return zip_path


def build(onefile: bool = True) -> int:
    print(f"Сборка релиза {APP_NAME}")
    version = ask_version()
    icon, jar = check_requirements()
    install_pyinstaller()

    exe = build_executable(version, onefile, icon)
    release_dir = prepare_release(exe, version, icon, jar)
    zip_path = create_zip(release_dir, version)
    save_version(version)

    print("\nГотово.")
    print(f"EXE: {exe}")
    print(f"ZIP: {zip_path}")
    return 0


def main() -> int:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Использование: python build.py [--onefile | --onedir]")
        print("По умолчанию собирается один exe.")
        return 0
    return build(onefile="--onedir" not in sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
