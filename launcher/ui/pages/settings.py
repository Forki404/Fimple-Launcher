from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
                               QSlider, QVBoxLayout, QWidget)

from ... import accounts as accmod
from ... import java as javamod
from ... import paths, utils
from ...config import ACCENTS, get_config, suggested_ram_mb, total_ram_mb
from .. import dialogs, icons, theme
from ..widgets import (Badge, Card, Chip, ComboBox, ElidedLabel, FlatCard,
                       GhostButton, IconButton, PrimaryButton, RoundCheckBox,
                       label, round_pixmap, spacer, toast)


class SettingsPage(QWidget):
    _SCROLLBAR_BASE = ("QScrollBar:vertical{background:transparent;width:11px;"
                       "margin:2px;}"
                       "QScrollBar::handle:vertical{border-radius:9px;"
                       "min-height:30px;}"
                       "QScrollBar::add-line,QScrollBar::sub-line"
                       "{height:0;width:0;border:none;background:transparent;}"
                       "QScrollBar::add-page,QScrollBar::sub-page"
                       "{background:transparent;}")
    _SCROLLBAR_HIDDEN = (_SCROLLBAR_BASE +
                         "QScrollBar::handle:vertical{background:transparent;}")

    def __init__(self, window):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self._loading = True
        self._build()
        self._loading = False
        self.load_values()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        head = QVBoxLayout()
        head.setSpacing(3)
        head.addWidget(label(self.cfg.t("settings_title"), size=25, bold=True))
        self.subtitle = label("", obj="Hint")
        head.addWidget(self.subtitle)
        root.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll = scroll
        inner = QWidget()
        self.lay = QVBoxLayout(inner)
        self.lay.setContentsMargins(0, 0, 10, 0)
        self.lay.setSpacing(14)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)
        bar = scroll.verticalScrollBar()
        bar.setStyleSheet(self._SCROLLBAR_HIDDEN)
        self._scrollbar_timer = QTimer(self)
        self._scrollbar_timer.setSingleShot(True)
        self._scrollbar_timer.timeout.connect(self._hide_scrollbar)
        bar.valueChanged.connect(self._flash_scrollbar)

        self._build_accounts()
        self._build_memory()
        self._build_behavior()
        self._build_appearance()
        self._build_paths()
        self.lay.addStretch(1)

    def _flash_scrollbar(self, _value: int) -> None:
        bar = self.scroll.verticalScrollBar()
        shown = self._SCROLLBAR_BASE + (
            f"QScrollBar::handle:vertical{{background:{theme.TEXT_MUTED};}}"
            f"QScrollBar::handle:vertical:hover{{background:{theme.TEXT_DIM};}}")
        if bar.styleSheet() != shown:
            bar.setStyleSheet(shown)
        self._scrollbar_timer.start(900)

    def _hide_scrollbar(self) -> None:
        bar = self.scroll.verticalScrollBar()
        if bar.styleSheet() != self._SCROLLBAR_HIDDEN:
            bar.setStyleSheet(self._SCROLLBAR_HIDDEN)

    def show_accounts(self) -> None:
        self.scroll.verticalScrollBar().setValue(0)

    def _build_accounts(self):
        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 11, 14, 12)
        v.setSpacing(11)
        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("user", theme.accent(self.cfg.get("accent")), 20))
        head.addWidget(ico)
        head.addWidget(label(self.cfg.t("accounts"), size=15, bold=True))
        head.addStretch(1)
        self.btn_ely = GhostButton("Ely.by", icon_name="shield")
        self.btn_ely.clicked.connect(self._ely_login)
        self.btn_offline = GhostButton(self.cfg.t("add_offline"), icon_name="plus")
        self.btn_offline.clicked.connect(self._add_offline)
        head.addWidget(self.btn_offline)
        head.addWidget(self.btn_ely)
        v.addLayout(head)

        self.accounts_host = QWidget()
        self.accounts_lay = QVBoxLayout(self.accounts_host)
        self.accounts_lay.setContentsMargins(0, 0, 0, 0)
        self.accounts_lay.setSpacing(8)
        v.addWidget(self.accounts_host)
        self.accounts_empty = label(self.cfg.t("no_accounts"), obj="Hint")
        v.addWidget(self.accounts_empty)
        self.lay.addWidget(card)

    def _render_accounts(self):
        while self.accounts_lay.count():
            item = self.accounts_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        store = accmod.store()
        accounts = store.all()
        current = store.current()
        self.accounts_empty.setVisible(not accounts)
        for a in accounts:
            self.accounts_lay.addWidget(self._account_row(a, current))

    def _account_row(self, a, current) -> QWidget:
        row = QFrame()
        row.setObjectName("CardFlat")
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 7, 8, 7)
        h.setSpacing(11)
        avatar = QLabel()
        avatar.setFixedSize(34, 34)
        path = store_avatar(a)
        if path:
            avatar.setPixmap(round_pixmap(path, 34))
        else:
            avatar.setPixmap(icons.make_pixmap("user", theme.TEXT_MUTED, 20))
            avatar.setAlignment(Qt.AlignCenter)
        h.addWidget(avatar)
        box = QVBoxLayout()
        box.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(7)
        top.addWidget(ElidedLabel(a.username, size=13, bold=True))
        top.addWidget(Badge("Ely.by" if a.type == "ely" else "offline",
                            theme.SUCCESS if a.type == "ely" else theme.TEXT_MUTED,
                            compact=True))
        box.addLayout(top)
        box.addWidget(ElidedLabel(a.uuid[:32], size=11, color=theme.TEXT_MUTED))
        h.addLayout(box, 1)
        if current and current.id == a.id:
            h.addWidget(Badge("✓", theme.SUCCESS))
        else:
            btn = GhostButton(self.cfg.t("select"))
            btn.setFixedWidth(80)
            btn.clicked.connect(lambda: self._select_account(a))
            h.addWidget(btn)
        rm = IconButton("trash", theme.DANGER, 30)
        rm.clicked.connect(lambda: self._remove_account(a))
        h.addWidget(rm)
        return row

    def _select_account(self, a):
        accmod.store().select(a.id)
        self._render_accounts()
        self.w.refresh_all()
        toast(self, f"{self.cfg.t('accounts')}: {a.username}", "success")

    def _remove_account(self, a):
        if not dialogs.confirm(self, f"{self.cfg.t('delete_instance')}: {a.username}?",
                               self.cfg.t("accounts")):
            return
        accmod.store().remove(a.id)
        self._render_accounts()
        self.w.refresh_all()

    def _ely_login(self):
        dlg = dialogs.ElyLoginDialog(self)
        if dlg.exec() and dlg.result_account:
            self._render_accounts()
            self.w.refresh_all()
            toast(self, self.cfg.t("ely_success", dlg.result_account.username), "success")
        self.w.workers.shutdown()

    def _add_offline(self):
        nick = dialogs.text_input(self, self.cfg.t("add_offline"),
                                  self.cfg.t("username"),
                                  self.cfg.get("nickname") or "Player")
        if not nick:
            return
        accmod.store().add_offline(nick)
        self._render_accounts()
        self.w.refresh_all()
        toast(self, self.cfg.t("offline_created"), "success")

    def _build_memory(self):
        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 11, 14, 12)
        v.setSpacing(12)
        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("cpu", theme.accent(self.cfg.get("accent")), 20))
        head.addWidget(ico)
        head.addWidget(label(self.cfg.t("ram"), size=15, bold=True))
        head.addStretch(1)
        self.ram_value = label("", size=14, bold=True, color=theme.accent(
            self.cfg.get("accent")))
        head.addWidget(self.ram_value)
        v.addLayout(head)

        self.auto_ram = RoundCheckBox(self.cfg.t("ram_auto"))
        self.auto_ram.stateChanged.connect(self._on_auto_ram)
        v.addWidget(self.auto_ram)

        self.slider = QSlider(Qt.Horizontal)
        total = total_ram_mb()
        self.slider.setRange(512, max(2048, total))
        self.slider.setSingleStep(256)
        self.slider.setPageStep(512)
        self.slider.valueChanged.connect(self._on_ram)
        v.addWidget(self.slider)

        self.ram_info = label(self.cfg.t("ram_total", utils.human_size(total * 1024 * 1024)),
                              obj="Hint")
        v.addWidget(self.ram_info)

        presets = QHBoxLayout()
        presets.setSpacing(7)
        self.ram_group = QButtonGroup(self)
        self.ram_group.setExclusive(True)
        for mb in (1024, 2048, 3072, 4096, 6144, 8192, 12288, 16384):
            if mb > total:
                continue
            c = Chip(f"{mb // 1024}G" if mb >= 1024 else f"{mb}M")
            c.setProperty("ram_mb", mb)
            c.clicked.connect(lambda _=False, m=mb: self._set_ram(m))
            self.ram_group.addButton(c)
            presets.addWidget(c)
        presets.addStretch(1)
        v.addLayout(presets)
        self.lay.addWidget(card)

    def _sync_ram_chips(self) -> None:
        value = int(self.slider.value())
        for btn in self.ram_group.buttons():
            mb = int(btn.property("ram_mb") or 0)
            btn.setChecked(not self.auto_ram.isChecked() and mb == value)

    def _on_auto_ram(self, state: int):
        self.slider.setEnabled(not state)
        self.cfg.set("auto_ram", bool(state))
        self.cfg.save()
        self._sync_ram_chips()
        self.w.refresh_all()

    def _on_ram(self, value: int):
        self.cfg.set("ram", int(value))
        self.cfg.save()
        self._update_ram_label(int(value))
        self._sync_ram_chips()
        self.w.refresh_all()

    def _set_ram(self, mb: int):
        self.auto_ram.setChecked(False)
        self.slider.setValue(mb)

    def _update_ram_label(self, mb: int):
        text = f"{mb // 1024} ГБ" if mb >= 1024 else f"{mb} МБ"
        self.ram_value.setText(text)
        try:
            self.ram_value.setStyleSheet(
                f"color:{theme.accent(self.cfg.get('accent'))};background:transparent;"
                "font-weight:700;")
        except Exception:
            pass

    def _build_behavior(self):
        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 11, 14, 12)
        v.setSpacing(10)
        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("sliders", theme.accent(self.cfg.get("accent")), 20))
        head.addWidget(ico)
        head.addWidget(label(self.cfg.t("sec_behavior"), size=15, bold=True))
        head.addStretch(1)
        v.addLayout(head)

        self.chk_hide_console = self._check(v, "close_console", self._save_bool)
        self.chk_minimize = self._check(v, "minimize_on_launch", self._save_bool)
        self.chk_auto_play = self._check(v, "auto_play", self._save_bool)
        self.chk_updates = self._check(v, "check_updates", self._save_bool)
        self.chk_java = self._check(v, "check_java", self._save_bool)
        self.lay.addWidget(card)

    def _check(self, layout: QVBoxLayout, key: str, slot) -> QCheckBox:
        box = RoundCheckBox(get_config().t(key))
        box.stateChanged.connect(lambda _s, k=key, b=box: slot(k, b.isChecked()))
        layout.addWidget(box)
        return box

    def _save_bool(self, key: str, value: bool) -> None:
        if self._loading:
            return
        self.cfg.set(key, value)
        self.cfg.save()

    def _build_appearance(self):
        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 11, 14, 12)
        v.setSpacing(12)
        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("palette", theme.accent(self.cfg.get("accent")), 20))
        head.addWidget(ico)
        head.addWidget(label(self.cfg.t("sec_appearance"), size=15, bold=True))
        head.addStretch(1)
        v.addLayout(head)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(label(self.cfg.t("language"), obj="Dim"))
        self.lang_combo = ComboBox()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCursor(Qt.PointingHandCursor)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        row.addWidget(self.lang_combo)
        row.addStretch(1)
        v.addLayout(row)

        colors = QHBoxLayout()
        colors.setSpacing(9)
        self.accent_buttons: dict = {}
        for name, hexc in ACCENTS.items():
            btn = IconButton("check", hexc, 30)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda _=False, n=name: self._set_accent(n))
            btn.setToolTip(hexc)
            self.accent_buttons[name] = btn
            colors.addWidget(btn)
        colors.addStretch(1)
        v.addLayout(colors)
        self._paint_accents()

        self.jvm_edit = QLineEdit()
        self.jvm_edit.setPlaceholderText("-XX:+UseZGC -Xss1M")
        self.jvm_edit.textChanged.connect(self._on_jvm)
        v.addWidget(label(self.cfg.t("jvm_args"), obj="Dim"))
        v.addWidget(self.jvm_edit)
        self.lay.addWidget(card)

    def _on_lang(self, idx: int):
        lang = self.lang_combo.itemData(idx)
        if lang and lang != self.cfg.lang:
            self.cfg.set("language", lang)
            self.cfg.save()
            self.w.retranslate()

    def _paint_accents(self) -> None:
        current = self.cfg.get("accent")
        for name, hexc in ACCENTS.items():
            btn = self.accent_buttons.get(name)
            if btn is None:
                continue
            picked = name == current
            btn.set_color("#ffffff" if picked else hexc)
            btn.setStyleSheet(
                f"QPushButton{{background:{hexc};border-radius:15px;"
                f"border:2px solid {'#ffffff' if picked else 'transparent'};}}")

    def _set_accent(self, name: str):
        self.cfg.set("accent", name)
        self.cfg.save()
        self._paint_accents()
        self.w.apply_theme()
        self.w.refresh_all()
        toast(self, f"{self.cfg.t('accent')}: {ACCENTS[name]}", "success")

    def _on_jvm(self, text: str):
        if self._loading:
            return
        self.cfg.set("jvm_args", text)
        self.cfg.save()

    def _build_paths(self):
        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 11, 14, 12)
        v.setSpacing(10)
        head = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("folder", theme.accent(self.cfg.get("accent")), 20))
        head.addWidget(ico)
        head.addWidget(label(self.cfg.t("sec_paths"), size=15, bold=True))
        head.addStretch(1)
        v.addLayout(head)
        row = QHBoxLayout()
        row.setSpacing(8)
        b1 = GhostButton(self.cfg.t("open_folder"), icon_name="folder")
        b1.clicked.connect(lambda: utils.open_path(paths.data_dir()))
        b2 = GhostButton(self.cfg.t("logs_open"), icon_name="terminal")
        b2.clicked.connect(lambda: utils.open_path(paths.logs_dir()))
        b3 = GhostButton(self.cfg.t("clear"), icon_name="trash")
        b3.clicked.connect(self._reset)
        for b in (b1, b2, b3):
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        self.paths_label = ElidedLabel(str(paths.base_dir()), size=12,
                                       color=theme.TEXT_MUTED)
        self.paths_label.setToolTip(str(paths.base_dir()))
        v.addWidget(self.paths_label)
        self.lay.addWidget(card)

    def _reset(self):
        if not dialogs.confirm(self, self.cfg.t("reset_confirm"),
                               self.cfg.t("clear")):
            return
        import shutil

        for folder in ("versions", "assets", "libraries"):
            p = paths.data_dir() / folder
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
        self.cfg.reset()
        toast(self, self.cfg.t("cleared"), "success")
        self.w.restart()

    def load_values(self):
        cfg = get_config()
        self._loading = True
        self.auto_ram.setChecked(bool(cfg.get("auto_ram", True)))
        self.slider.setEnabled(not cfg.get("auto_ram", True))
        self.slider.setValue(int(cfg.get("ram") or suggested_ram_mb()))
        self._update_ram_label(int(cfg.get("ram") or suggested_ram_mb()))
        self._sync_ram_chips()

        self.chk_hide_console.setChecked(bool(cfg.get("hide_console", True)))
        self.chk_minimize.setChecked(bool(cfg.get("minimize_on_launch", True)))
        self.chk_auto_play.setChecked(bool(cfg.get("auto_play", False)))
        self.chk_updates.setChecked(bool(cfg.get("check_updates", True)))
        self.chk_java.setChecked(bool(cfg.get("check_java", True)))

        idx = self.lang_combo.findData(cfg.lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.jvm_edit.setText(cfg.get("jvm_args") or "")
        self._loading = False
        self._paint_accents()
        self._render_accounts()
        self.subtitle.setText(f"v{paths.app_version()}")

    def refresh(self):
        self.cfg = get_config()
        self.load_values()


def store_avatar(a):
    return accmod.store().avatar_path(a)
