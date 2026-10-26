#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def _missing_modules() -> list:
    need = {
        "PySide6": "PySide6",
        "requests": "requests",
        "minecraft_launcher_lib": "minecraft-launcher-lib",
    }
    missing = []
    for module, package in need.items():
        try:
            __import__(module)
        except ImportError:
            missing.append((package, module))
    return missing


def _check_deps() -> bool:
    missing = _missing_modules()
    fatal = [p for p, m in missing if m != "minecraft_launcher_lib"]
    soft = [p for p, m in missing if m == "minecraft_launcher_lib"]

    if fatal:
        print("=" * 62)
        print("  Не хватает модулей: " + ", ".join(fatal))
        print("  Установите их одной командой:")
        print()
        print(f"      {sys.executable} -m pip install " + " ".join(fatal))
        print()
        print("  Или полностью:  pip install -r requirements.txt")
        print("=" * 62)
        try:
            input("Нажмите Enter для выхода…")
        except EOFError:
            pass
        return False

    if soft:
        print("=" * 62)
        print("  Не установлен: " + ", ".join(soft))
        print("  Установка и запуск игры будут недоступны.")
        print()
        print(f"      {sys.executable} -m pip install " + " ".join(soft))
        print("=" * 62)
    return True


def _needs_pythonw() -> bool:
    if os.name != "nt":
        return False
    if getattr(sys, "frozen", False):
        return True
    return not sys.executable.lower().endswith("pythonw.exe")


def main() -> int:
    if not _check_deps():
        input("Нажмите Enter для выхода…")
        return 1

    if HERE not in sys.path:
        sys.path.insert(0, HERE)

    from launcher.app import main as run

    if _needs_pythonw() and not getattr(sys, "frozen", False) \
            and "--windowed" not in sys.argv:
        args = [a for a in sys.argv[1:] if a != "--windowed"]
        try:
            from launcher.utils import console_free_cmd, hidden_console_args

            pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if os.path.exists(pythonw):
                cmd = console_free_cmd(
                    [pythonw, os.path.abspath(__file__), "--windowed"] + args)
                startupinfo, creationflags = hidden_console_args(True)
                subprocess.Popen(cmd, startupinfo=startupinfo,
                                 creationflags=creationflags)
                return 0
        except Exception:
            pass

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
