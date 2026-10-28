from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from . import paths, utils

ACCENTS = {
    "blue": "#3b82f6",
    "violet": "#8b5cf6",
    "emerald": "#10b981",
    "amber": "#f59e0b",
    "rose": "#f43f5e",
    "cyan": "#06b6d4",
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        "app_title": "Fimple Launcher",
        "nav_home": "Главная",
        "nav_instances": "Инстансы",
        "nav_mods": "Моды",
        "nav_java": "Java",
        "nav_settings": "Настройки",
        "nav_logs": "Логи",
        "refresh": "Обновить",
        "play": "ИГРАТЬ",
        "playing": "Игра запущена",
        "instance_none": "Инстансы не найдены",
        "instance_none_hint": "Создайте первый инстанс, чтобы начать игру",
        "create_instance": "Создать инстанс",
        "quick_actions": "Быстрые действия",
        "install_vanilla": "Vanilla",
        "install_forge": "Forge",
        "install_fabric": "Fabric",
        "install_quilt": "Quilt",
        "install_neoforge": "NeoForge",
        "install_optifine": "OptiFine",
        "coming_soon": "скоро",
        "loader_soon_hint": "Поддержка отложена, установка пока недоступна",
        "recent_instances": "Недавние",
        "java_needed_for": "нужна {}",
        "search_results": "Найдено: {}",
        "stat_instances": "инстансов",
        "stat_playtime": "в игре",
        "stat_updates": "обновлений",
        "search_placeholder": "Поиск инстанса…",
        "all": "Все",
        "empty_search": "Ничего не найдено",
        "installed": "Установлено",
        "playtime": "Игра",
        "last_played": "Запуск",
        "launch": "Запустить",
        "delete_instance": "Удалить",
        "delete_instance_confirm": "Удалить инстанс «{}»?\nФайлы игры и моды будут удалены без возможности восстановления.",
        "rename": "Переименовать",
        "open_folder": "Открыть папку",
        "instance_renamed": "Инстанс переименован",
        "instance_deleted": "Инстанс удалён",
        "instance_created": "Инстанс «{}» создан",
        "mods_count": "модов",
        "saves_count": "сохранений",
        "mods_dir": "Папка модов",
        "sec_settings": "Настройки",
        "type_release": "Релизы",
        "type_snapshot": "Снапшоты",
        "type_old_beta": "Старые беты",
        "type_old_alpha": "Альфы",
        "type_all": "Все",
        "search_versions": "Поиск версии: 1.20 или fabric…",
        "versions_loading": "Загружаем список версий…",
        "versions_error": "Не удалось загрузить список версий",
        "versions_need_lib": "Нет модуля minecraft-launcher-lib — установите его (см. README)",
        "versions_manual_hint": "Версию можно вписать вручную в поле выше",
        "enter_version_required": "Укажите версию Minecraft — введите её или выберите из списка",
        "stat_title": "Быстрая информация",
        "signing_in": "Вход…",
        "show_password": "Показать пароль",
        "fill_both_fields": "Заполните оба поля",
        "password_not_saved": "Пароль не сохраняется — вход идёт напрямую",
        "instance_info": "Информация",
        "java_for_instance": "Java для инстанса",
        "auto": "Авто",
        "install": "Установить",
        "installing": "Установка…",
        "installed_ok": "{} установлен!",
        "version_exists": "Эта версия уже установлена",
        "enter_version": "Версия Minecraft",
        "enter_version_hint": "например 1.20.1 или 1.21.1",
        "enter_loader_version": "Версия загрузчика",
        "enter_loader_version_hint": "например 47.2.0 (необязательно)",
        "auto_latest": "пусто = последняя",
        "cancel": "Отмена",
        "close": "Закрыть",
        "start": "Начать",
        "select": "Выбрать",
        "accounts": "Аккаунты",
        "account_offline": "Оффлайн",
        "add_account": "Добавить аккаунт",
        "add_offline": "Оффлайн-ник",
        "ely_title": "Вход через Ely.by",
        "ely_email": "E-mail",
        "ely_password": "Пароль",
        "ely_success": "Вы вошли как {}",
        "ely_failed": "Ошибка входа Ely.by",
        "offline_created": "Оффлайн-аккаунт создан",
        "no_accounts": "Аккаунты не созданы",
        "select_account": "Выберите аккаунт",
        "username": "Никнейм",
        "java_title": "Java",
        "java_none": "Java не найдена",
        "java_none_hint": "Скачайте Java — без неё Minecraft не запустится",
        "java_found": "Найденные Java",
        "java_found_short": "найдено",
        "java_scanning": "идёт поиск…",
        "java_download": "Скачать",
        "java_download_title": "Скачать Java {}",
        "java_need_for": "Для Minecraft {} нужна {}",
        "java_compat": "Обе поддерживают Minecraft 1.17+, 25-я умеет всё, что умеет 21-я",
        "java_download_tooltip": "Скачать Temurin {} (JDK) в Minecraft/runtime",
        "sec_behavior": "Запуск и обновления",
        "sec_appearance": "Цвет темы и язык",
        "sec_paths": "Папки и сброс",
        "reset_confirm": "Сбросить все настройки и удалить Minecraft/versions?",
        "java_progress": "Загрузка Java {}…",
        "java_extracting": "Распаковка Java {}…",
        "java_ready": "Java {} установлена",
        "java_select": "Выбрать",
        "java_selected": "Выбрано",
        "java_use": "Использовать",
        "java_browse": "Указать вручную…",
        "java_delete": "Удалить",
        "java_manual": "Путь к java.exe",
        "java_path": "Путь к Java",
        "java_test": "Проверить",
        "java_invalid": "Не удалось определить версию Java по этому пути",
        "java_required": "Требуется Java",
        "java_ok": "Подходит",
        "java_low": "Слишком старая",
        "java_high": "Слишком новая",
        "java_bundled": "В комплекте",
        "java_system": "Системная",
        "settings_title": "Настройки",
        "ram": "Выделенная память",
        "ram_total": "В системе: {}",
        "ram_auto": "Автоматически",
        "language": "Язык",
        "accent": "Цвет темы",
        "close_console": "Скрывать консоль игры",
        "version_missing": "Файлы версии {} не найдены — игру не запустить. Переустановить версию?",
        "reinstall": "Переустановить",
        "hotkeys_title": "Горячие клавиши",
        "hotkeys_hint": "1–6 — разделы · L — запуск · R — обновление · Q — выход",
        "hotkey_launch": "Запустить игру",
        "hotkey_refresh": "Обновить списки",
        "hotkey_quit": "Выход",
        "show_console": "Показывать консоль игры",
        "console_title": "Консоль игры",
        "auto_play": "Автозапуск после установки",
        "check_updates": "Проверять обновления при запуске",
        "check_java": "Предлагать скачать Java",
        "minimize_on_launch": "Сворачивать лаунчер при запуске игры",
        "jvm_args": "Дополнительные JVM-аргументы",
        "mcmeta": "Использовать MCMeta для RAM",
        "saved": "Сохранено",
        "update_available": "Доступно обновление: {}",
        "update_download": "Скачать",
        "update_skip": "Позже",
        "update_checking": "Проверка обновлений…",
        "update_none": "Установлена последняя версия",
        "update_failed": "Не удалось проверить обновления",
        "update_downloading": "Загрузка обновления…",
        "update_extracting": "Распаковка обновления…",
        "update_ready": "Обновление готово. Перезапустить лаунчер?",
        "update_restart": "Перезапустить",
        "update_later": "Выйти",
        "update_notes": "Что нового",
        "update_to": "Обновление до {}",
        "update_current": "У вас установлена {}",
        "logs_title": "Логи",
        "logs_launcher": "Журнал лаунчера",
        "logs_placeholder": "Здесь появятся сообщения лаунчера…",
        "console_placeholder": "Здесь появится вывод игры…",
        "logs_open": "Открыть папку с логами",
        "copy": "Копировать",
        "cleared": "Очищено",
        "clear": "Очистить",
        "mods_title": "Моды",
        "mods_search": "Поиск модов на Modrinth…",
        "mods_of_instance": "Моды инстанса {}",
        "installed_mods": "Установленные моды",
        "no_mods": "Моды не установлены",
        "install_mod": "Установить",
        "uninstall_mod": "Удалить",
        "enable": "Вкл.",
        "disable": "Выкл.",
        "mods_searching": "Поиск…",
        "mods_error": "Ошибка Modrinth",
        "mod_installed": "{} установлен",
        "mod_uninstalled": "{} удалён",
        "select_instance_for_mod": "Куда установить мод?",
        "open_modrinth": "Открыть на Modrinth",
        "loader_fabric": "Fabric",
        "loader_quilt": "Quilt",
        "loader_forge": "Forge",
        "loader_neoforge": "NeoForge",
        "loader_optifine": "OptiFine",
        "loader_vanilla": "Vanilla",
        "dependencies": "Зависимости",
        "ok": "ОК",
        "yes": "Да",
        "no": "Нет",
        "error": "Ошибка",
        "warning": "Внимание",
        "done": "Готово",
        "select_version": "Выберите версию",
        "enter_nickname": "Введите ник",
        "version": "Версия",
        "loader": "Загрузчик",
        "offline_mode": "Оффлайн-режим",
        "java": "Java",
        "status": "Статус",
        "idle": "Готов",
        "downloading": "Загрузка",
        "installing_short": "Установка",
        "launching": "Запуск",
        "tip_random": "Совет дня",
    },
    "en": {
        "app_title": "Fimple Launcher",
        "nav_home": "Home",
        "nav_instances": "Instances",
        "nav_mods": "Mods",
        "nav_java": "Java",
        "nav_settings": "Settings",
        "nav_logs": "Logs",
        "refresh": "Refresh",
        "play": "PLAY",
        "playing": "Game is running",
        "instance_none": "No instances found",
        "instance_none_hint": "Create your first instance to start playing",
        "create_instance": "Create instance",
        "quick_actions": "Quick actions",
        "install_vanilla": "Vanilla",
        "install_forge": "Forge",
        "install_fabric": "Fabric",
        "install_quilt": "Quilt",
        "install_neoforge": "NeoForge",
        "install_optifine": "OptiFine",
        "coming_soon": "soon",
        "loader_soon_hint": "Support is on hold, installing is not available yet",
        "recent_instances": "Recent",
        "java_needed_for": "requires {}",
        "search_results": "Found: {}",
        "stat_instances": "instances",
        "stat_playtime": "played",
        "stat_updates": "updates",
        "search_placeholder": "Search instance…",
        "all": "All",
        "empty_search": "Nothing found",
        "installed": "Installed",
        "playtime": "Played",
        "last_played": "Last run",
        "launch": "Launch",
        "delete_instance": "Delete",
        "delete_instance_confirm": "Delete instance '{}'?\nGame files and mods will be removed permanently.",
        "rename": "Rename",
        "open_folder": "Open folder",
        "instance_renamed": "Instance renamed",
        "instance_deleted": "Instance deleted",
        "instance_created": "Instance '{}' created",
        "mods_count": "mods",
        "saves_count": "saves",
        "mods_dir": "Mods folder",
        "sec_settings": "Settings",
        "type_release": "Releases",
        "type_snapshot": "Snapshots",
        "type_old_beta": "Old beta",
        "type_old_alpha": "Alpha",
        "type_all": "All",
        "search_versions": "Search version: 1.20 or fabric…",
        "versions_loading": "Loading version list…",
        "versions_error": "Could not load the version list",
        "versions_need_lib": "minecraft-launcher-lib is missing — install it (see README)",
        "versions_manual_hint": "You can type the version in the field above",
        "enter_version_required": "Pick a Minecraft version — type it or choose it from the list",
        "stat_title": "Quick info",
        "signing_in": "Signing in…",
        "show_password": "Show password",
        "fill_both_fields": "Fill in both fields",
        "password_not_saved": "Your password is never stored — sign-in goes straight to Ely.by",
        "instance_info": "Information",
        "java_for_instance": "Java for instance",
        "auto": "Auto",
        "install": "Install",
        "installing": "Installing…",
        "installed_ok": "{} installed!",
        "version_exists": "This version is already installed",
        "enter_version": "Minecraft version",
        "enter_version_hint": "for example 1.20.1 or 1.21.1",
        "enter_loader_version": "Loader version",
        "enter_loader_version_hint": "for example 47.2.0 (optional)",
        "auto_latest": "empty = latest",
        "cancel": "Cancel",
        "close": "Close",
        "start": "Start",
        "select": "Select",
        "accounts": "Accounts",
        "account_offline": "Offline",
        "add_account": "Add account",
        "add_offline": "Offline name",
        "ely_title": "Sign in with Ely.by",
        "ely_email": "E-mail",
        "ely_password": "Password",
        "ely_success": "Signed in as {}",
        "ely_failed": "Ely.by sign-in failed",
        "offline_created": "Offline account created",
        "no_accounts": "No accounts yet",
        "select_account": "Select an account",
        "username": "Username",
        "java_title": "Java",
        "java_none": "No Java found",
        "java_none_hint": "Download Java — Minecraft won't start without it",
        "java_found": "Found Java",
        "java_found_short": "found",
        "java_scanning": "searching…",
        "java_download": "Download",
        "java_download_title": "Download Java {}",
        "java_need_for": "Minecraft {} requires {}",
        "java_compat": "Both run Minecraft 1.17+, and 25 runs everything 21 does",
        "java_download_tooltip": "Download Temurin {} (JDK) into Minecraft/runtime",
        "sec_behavior": "Launching and updates",
        "sec_appearance": "Theme and language",
        "sec_paths": "Folders and reset",
        "reset_confirm": "Reset all settings and delete Minecraft/versions?",
        "java_progress": "Downloading Java {}…",
        "java_extracting": "Extracting Java {}…",
        "java_ready": "Java {} installed",
        "java_select": "Select",
        "java_selected": "Selected",
        "java_use": "Use",
        "java_browse": "Specify manually…",
        "java_delete": "Delete",
        "java_manual": "Path to java.exe",
        "java_path": "Java path",
        "java_test": "Test",
        "java_invalid": "Could not determine the Java version at this path",
        "java_required": "Required",
        "java_ok": "Suitable",
        "java_low": "Too old",
        "java_high": "Too new",
        "java_bundled": "Bundled",
        "java_system": "System",
        "settings_title": "Settings",
        "ram": "Allocated memory",
        "ram_total": "System: {}",
        "ram_auto": "Automatic",
        "language": "Language",
        "accent": "Accent color",
        "close_console": "Hide game console",
        "version_missing": "Files for version {} are missing, the game cannot start. Reinstall it?",
        "reinstall": "Reinstall",
        "hotkeys_title": "Hotkeys",
        "hotkeys_hint": "1–6 — sections · L — launch · R — refresh · Q — quit",
        "hotkey_launch": "Launch game",
        "hotkey_refresh": "Refresh lists",
        "hotkey_quit": "Quit",
        "show_console": "Show game console",
        "console_title": "Game console",
        "auto_play": "Auto-launch after install",
        "check_updates": "Check updates on start",
        "check_java": "Offer to download Java",
        "minimize_on_launch": "Minimize launcher on launch",
        "jvm_args": "Extra JVM arguments",
        "mcmeta": "Use MCMeta for RAM",
        "saved": "Saved",
        "update_available": "Update available: {}",
        "update_download": "Download",
        "update_skip": "Later",
        "update_checking": "Checking for updates…",
        "update_none": "You're up to date",
        "update_failed": "Could not check for updates",
        "update_downloading": "Downloading update…",
        "update_extracting": "Extracting update…",
        "update_ready": "Update ready. Restart the launcher?",
        "update_restart": "Restart",
        "update_later": "Exit",
        "update_notes": "What's new",
        "update_to": "Update to {}",
        "update_current": "You have {}",
        "logs_title": "Logs",
        "logs_launcher": "Launcher log",
        "logs_placeholder": "Launcher messages will show up here…",
        "console_placeholder": "Game output will show up here…",
        "logs_open": "Open logs folder",
        "copy": "Copy",
        "cleared": "Cleared",
        "clear": "Clear",
        "mods_title": "Mods",
        "mods_search": "Search mods on Modrinth…",
        "mods_of_instance": "Instance {} mods",
        "installed_mods": "Installed mods",
        "no_mods": "No mods installed",
        "install_mod": "Install",
        "uninstall_mod": "Remove",
        "enable": "On",
        "disable": "Off",
        "mods_searching": "Searching…",
        "mods_error": "Modrinth error",
        "mod_installed": "{} installed",
        "mod_uninstalled": "{} removed",
        "select_instance_for_mod": "Where to install the mod?",
        "open_modrinth": "Open on Modrinth",
        "loader_fabric": "Fabric",
        "loader_quilt": "Quilt",
        "loader_forge": "Forge",
        "loader_neoforge": "NeoForge",
        "loader_optifine": "OptiFine",
        "loader_vanilla": "Vanilla",
        "dependencies": "Dependencies",
        "ok": "OK",
        "yes": "Yes",
        "no": "No",
        "error": "Error",
        "warning": "Warning",
        "done": "Done",
        "select_version": "Select a version",
        "enter_nickname": "Enter a nickname",
        "version": "Version",
        "loader": "Loader",
        "offline_mode": "Offline mode",
        "java": "Java",
        "status": "Status",
        "idle": "Ready",
        "downloading": "Downloading",
        "installing_short": "Installing",
        "launching": "Launching",
        "tip_random": "Tip of the day",
    },
}

TIPS = [
    "Не забудь выделить Minecraft хотя бы 4 ГБ памяти — иначе будет лагать.",
    "Fabric быстрее Forge и поддерживает почти все моды на новых версиях.",
    "Клавиатурные подсказки: Ctrl+1…5 переключают разделы лаунчера.",
    "Моды можно включать и выключать, не удаляя — файлы просто переименовываются.",
    "Обновления лаунчера проверяются автоматически при запуске.",
    "Если игра вылетает — попробуй уменьшить выделенную память или сменить Java.",
    "OptiFine ставится поверх Vanilla или Forge.",
    "Авторизация Ely.by безопаснее: пароль не хранится у нас в открытом виде.",
]


class Config:
    def __init__(self) -> None:
        self._data: Dict[str, Any] = utils.read_json(paths.settings_file(), {}) or {}
        self._defaults: Dict[str, Any] = {
            "nickname": "Player",
            "ram": 0,
            "auto_ram": True,
            "ely": None,
            "accounts": [],
            "current_account": None,
            "hide_console": True,
            "language": "ru",
            "accent": "blue",
            "auto_play": False,
            "check_updates": True,
            "check_java": True,
            "minimize_on_launch": True,
            "jvm_args": "",
            "use_mcmeta": True,
            "custom_java": None,
            "java_major_pref": "auto",
            "window_width": 1180,
            "window_height": 760,
            "last_update_check": 0,
            "last_version": "",
            "last_loader_version": "",
        }
        self._data.setdefault("accounts", [])
        self._data.setdefault("nickname", "Player")
        if not isinstance(self._data.get("ram"), int):
            self._data["ram"] = 0

    def get(self, key: str, default: Any = None) -> Any:
        if key in self._data:
            return self._data[key]
        return self._defaults.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def update(self, values: Dict[str, Any]) -> None:
        self._data.update(values)

    def save(self) -> None:
        utils.write_json(paths.settings_file(), self._data)

    @property
    def all(self) -> Dict[str, Any]:
        return dict(self._data)

    def reset(self) -> None:
        self._data = {}
        self.save()

    @property
    def lang(self) -> str:
        return self._data.get("language", "ru")

    def t(self, key: str, *args) -> str:
        table = TRANSLATIONS.get(self.lang, TRANSLATIONS["ru"])
        text = table.get(key) or TRANSLATIONS["ru"].get(key, key)
        if args:
            try:
                return text.format(*args)
            except Exception:
                return text
        return text

    def random_tip(self) -> str:
        import random

        return random.choice(TIPS)


def total_ram_mb() -> int:
    try:
        import psutil

        return int(psutil.virtual_memory().total / 1024 / 1024)
    except Exception:
        pass
    try:
        if sys.platform == "win32":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return int(stat.ullTotalPhys / 1024 / 1024)
    except Exception:
        pass
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size / 1024 / 1024)
    except Exception:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return 4096


def suggested_ram_mb() -> int:
    total = total_ram_mb()
    if total <= 4096:
        return max(1024, int(total * 0.6))
    if total <= 8192:
        return 3072 if total <= 8192 else 4096
    if total <= 16384:
        return 4096
    return 6144 if total <= 32768 else 8192


def current_ram() -> int:
    cfg = get_config()
    if cfg.get("auto_ram", True):
        return suggested_ram_mb()
    return int(cfg.get("ram") or suggested_ram_mb())


_CONFIG: Optional[Config] = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config()
    return _CONFIG
