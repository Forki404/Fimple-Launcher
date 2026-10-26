from __future__ import annotations

from .. import utils

from PySide6.QtGui import QColor, QFont, QFontDatabase

from ..config import ACCENTS

BG = "#15181c"
BG_ALT = "#1b1f24"
CARD = "#23282e"
CARD_HOVER = "#2c323a"
CARD_ACTIVE = "#343b45"
BORDER = "#333940"
BORDER_LIGHT = "#414953"

TEXT = "#f0f3f6"
TEXT_DIM = "#a7b0bb"
TEXT_MUTED = "#7b858f"

SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"
INFO = "#38bdf8"

GRASS = "#7cb342"

RADIUS_CARD = 16
RADIUS_PANEL = 14
RADIUS_CONTROL = 12
RADIUS_BADGE = 9
RADIUS_CHIP = 11

GAP_TIGHT = 6
GAP = 10
GAP_WIDE = 14
PAD_PAGE = 18
PAD_CARD = 13

def accent(name: str = "blue") -> str:
    return ACCENTS.get(name, ACCENTS["blue"])

def accent_soft(name: str = "blue", alpha: int = 38) -> str:
    c = QColor(accent(name))
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha / 255:.3f})"

def mix(c1: str, c2: str, t: float = 0.5) -> str:
    a, b = QColor(c1), QColor(c2)
    return QColor(
        int(a.red() + (b.red() - a.red()) * t),
        int(a.green() + (b.green() - a.green()) * t),
        int(a.blue() + (b.blue() - a.blue()) * t),
    ).name()

def ui_font(size: int = 13, weight: int = 400) -> QFont:
    for family in ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
                   "Noto Sans", "DejaVu Sans", "Arial"):
        if family in QFontDatabase.families():
            f = QFont(family, size)
            f.setWeight(QFont.Weight(weight))
            f.setHintingPreference(QFont.PreferFullHinting)
            return f
    return QFont("", size)

def mono_font(size: int = 12) -> QFont:
    for family in ("Cascadia Code", "JetBrains Mono", "Consolas", "DejaVu Sans Mono",
                   "Menlo", "Courier New"):
        if family in QFontDatabase.families():
            return QFont(family, size)
    return QFont("monospace", size)

def emoji_font(size: int = 16) -> QFont:
    for family in ("Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji",
                   "Twemoji Mozilla", "Symbola"):
        if family in QFontDatabase.families():
            return QFont(family, size)
    return QFont("", size)

def stylesheet(accent_name: str = "blue") -> str:
    a = accent(accent_name)
    a_dark = mix(a, "#000000", 0.35)
    a_hover = mix(a, "#ffffff", 0.15)
    soft = accent_soft(accent_name, 46)

    css = f"""
* {{
    outline: 0;
}}

QWidget {{
    background: transparent;
    color: {TEXT};
    font-size: 13px;
}}

QToolTip {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 10px;
    padding: 6px 9px;
}}

#Root {{
    background: {BG};
}}

#Sidebar {{
    background: {BG_ALT};
    border-right: 1px solid {BORDER};
}}

#SidebarTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT};
    padding: 4px 0;
}}

#SidebarBadge {{
    color: {a};
    font-size: 18px;
    font-weight: 800;
}}

#PageTitle {{
    font-size: 23px;
    font-weight: 700;
}}

#PageSubtitle {{
    color: {TEXT_DIM};
    font-size: 13px;
}}

#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_CARD}px;
}}

#Card:hover {{
    background: {CARD_HOVER};
    border: 1px solid {BORDER_LIGHT};
}}

#CardFlat {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_PANEL}px;
}}

#CardSelected {{
    background: {CARD_ACTIVE};
    border: 1px solid {a};
    border-radius: {RADIUS_CARD}px;
}}

#Divider {{
    background: {BORDER};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}

#SectionTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {TEXT_DIM};
}}

#Hint {{
    color: {TEXT_MUTED};
    font-size: 12px;
}}

#Dim {{
    color: {TEXT_DIM};
}}

#Mono {{
    font-family: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
    color: {TEXT_DIM};
}}
QPushButton {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER_LIGHT};
    border-radius: {RADIUS_CONTROL}px;
    padding: 7px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background: {CARD_HOVER};
    border-color: {mix(BORDER_LIGHT, a, 0.5)};
}}
QPushButton:pressed {{
    background: {CARD_ACTIVE};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    background: {mix(CARD, BG, 0.5)};
    border-color: {BORDER};
}}

QPushButton#Primary {{
    background: {a};
    color: #ffffff;
    border: 1px solid {a};
    border-radius: {RADIUS_CONTROL}px;
    padding: 7px 14px;
    font-weight: 700;
}}
QPushButton#Primary:hover {{ background: {a_hover}; border-color: {a_hover}; }}
QPushButton#Primary:pressed {{ background: {a_dark}; }}
QPushButton#Primary:disabled {{
    background: {mix(a, BG, 0.65)};
    border-color: transparent;
    color: {mix("#ffffff", BG, 0.4)};
}}

QPushButton#Danger {{
    background: {DANGER};
    color: #ffffff;
    border: 1px solid {DANGER};
    font-weight: 700;
}}
QPushButton#Danger:hover {{ background: {mix(DANGER, "#ffffff", 0.15)}; }}

QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_DIM};
    padding: 6px 10px;
}}
QPushButton#Ghost:hover {{
    background: {CARD_HOVER};
    color: {TEXT};
}}

QPushButton#Play {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {mix(a, "#ffffff", 0.18)}, stop:1 {a});
    color: #ffffff;
    border: none;
    border-radius: {RADIUS_CONTROL}px;
    font-size: 18px;
    font-weight: 800;
    padding: 13px 10px;
}}
QPushButton#Play:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {mix(a, "#ffffff", 0.32)}, stop:1 {a_hover});
}}
QPushButton#Play:disabled {{
    background: {CARD};
    color: {TEXT_MUTED};
}}

QPushButton#Accent {{
    background: {soft};
    color: {a};
    border: 1px solid {mix(a, BG, 0.55)};
    font-weight: 700;
}}
QPushButton#Accent:hover {{ background: {accent_soft(accent_name, 70)}; }}

QPushButton#Chip {{
    background: transparent;
    color: {TEXT_DIM};
    border: 1px solid {BORDER_LIGHT};
    border-radius: {RADIUS_CHIP}px;
    padding: 4px 11px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#Chip:checked {{
    background: {soft};
    color: {a};
    border-color: {a};
}}
QPushButton#Chip:hover {{ color: {TEXT}; }}
QPushButton#Chip:disabled {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    background: transparent;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {{
    background: {mix(BG, CARD, 0.35)};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 10px;
    padding: 9px 12px;
    selection-background-color: {a};
    selection-color: #ffffff;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{
    border-color: {a};
    background: {mix(BG, CARD, 0.55)};
}}
QLineEdit::placeholder {{ color: {TEXT_MUTED}; }}

QComboBox {{
    background: {mix(BG, CARD, 0.35)};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 16px;
    padding: 8px 12px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {mix(BORDER_LIGHT, a, 0.4)}; }}
QComboBox::drop-down {{
    border: none;
    width: 26px;
    subcontrol-origin: padding;
    subcontrol-position: center right;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0px;
    height: 0px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 16px;
    selection-background-color: {soft};
    selection-color: {TEXT};
    padding: 4px;
    outline: 0;
}}
QProgressBar {{
    background: {mix(BG, CARD, 0.3)};
    border: none;
    border-radius: 16px;
    height: 10px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {mix(a, "#ffffff", 0.2)}, stop:1 {a});
    border-radius: 16px;
}}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LIGHT};
    border-radius: 9px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {TEXT_MUTED}; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_LIGHT};
    border-radius: 9px;
    min-width: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:vertical {{
    height: 8px;
}}
QCheckBox, QRadioButton {{ spacing: 10px; color: {TEXT}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 19px; height: 19px;
    border: 1px solid {BORDER_LIGHT};
    background: {mix(BG, CARD, 0.3)};
}}
QCheckBox::indicator {{ border-radius: 10px; }}
QRadioButton::indicator {{ border-radius: 14px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {a}; }}
QCheckBox::indicator:checked {{
    background: {a};
    border-color: {a};
    image: none;
}}
QCheckBox::indicator:unchecked:hover {{ background: {mix(BG, CARD, 0.55)}; }}
QRadioButton::indicator:checked {{
    background: {a};
    border: 5px solid {mix(BG, CARD, 0.3)};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {mix(BG, CARD, 0.3)};
    border-radius: 9px;
}}
QSlider::sub-page:horizontal {{
    background: {a};
    border-radius: 9px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    width: 17px; height: 17px;
    margin: -6px 0;
    border-radius: 14px;
    border: 2px solid {a};
}}
QSlider::handle:horizontal:hover {{ background: {a_hover}; }}
QListWidget, QTreeWidget, QTableWidget {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: {RADIUS_PANEL}px;
    outline: 0;
    padding: 3px;
}}
QListWidget::item {{
    border-radius: {RADIUS_CONTROL}px;
    padding: 3px;
    margin: 1px 0;
}}
QListWidget::item:hover {{ background: {CARD_HOVER}; }}
QListWidget::item:selected {{ background: {CARD_ACTIVE}; color: {TEXT}; }}

QMenu {{
    background: {CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: {RADIUS_PANEL}px;
    padding: 5px;
}}
QMenu::item {{
    padding: 6px 22px 6px 12px;
    border-radius: {RADIUS_CONTROL}px;
}}
QMenu::item:selected {{ background: {soft}; color: {a}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 5px 8px; }}

QDialog {{ background: {BG}; }}
QMessageBox {{ background: {BG}; }}
QMessageBox QLabel {{ color: {TEXT}; font-size: 13px; }}

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: {RADIUS_PANEL}px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 9px 18px;
    margin-right: 4px;
    border-radius: 13px;
    font-weight: 600;
}}
QTabBar::tab:selected {{ background: {soft}; color: {a}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
"""
    return _sanitize_css(css)

def _sanitize_css(css: str) -> str:
    import re

    if not css.strip():
        return ""

    def fix_url(m) -> str:
        return 'url("%s")' % m.group(1).replace("\\", "/")

    css = re.sub(r'url\(\s*["\']?([^"\')]+)["\']?\s*\)', fix_url, css)

    while css.count("{") > css.count("}") and "}" in css:
        cut = css.rfind("}")
        utils.log(f"QSS: обрезаю незакрытый блок с позиции {cut}", "WARN")
        css = css[:cut + 1]
    while css.count("}") > css.count("{") and "{" in css:
        cut = css.find("}")
        utils.log(f"QSS: лишняя скобка в позиции {cut}, обрезаю", "WARN")
        css = css[:cut]

    css_masked = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for sel in re.findall(r"([^{}]*)\{", css_masked):
        s = sel.strip()
        if s and not s.startswith(("Q", "#", "*", ".")):
            utils.log(f"QSS: подозрительный селектор {s[:40]!r}", "WARN")

    if css.count("{") != css.count("}"):
        utils.log("QSS: не удалось починить, стили отключены", "ERROR")
        return ""
    return css
