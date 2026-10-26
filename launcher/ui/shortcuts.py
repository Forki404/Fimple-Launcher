from __future__ import annotations

from typing import List, Tuple

NAV_PAGES: Tuple[str, ...] = ("home", "instances", "mods", "java", "logs", "settings")

ACTION_KEYS: Tuple[Tuple[str, str], ...] = (
    ("Ctrl+L", "hotkey_launch"),
    ("Ctrl+R", "hotkey_refresh"),
    ("Ctrl+Q", "hotkey_quit"),
)


def shortcut_entries() -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = [
        (f"Ctrl+{i}", f"nav_{key}", key)
        for i, key in enumerate(NAV_PAGES, start=1)
    ]
    out.extend((keys, label, "") for keys, label in ACTION_KEYS)
    return out
