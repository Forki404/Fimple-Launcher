from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from ... import instances as instmod
from ... import java as javamod
from ... import paths, utils
from ...config import get_config
from .. import icons, shortcuts, theme
from ..dialogs import InstallDialog
from ..widgets import (Badge, Card, Chip, ElidedLabel, FlatCard, GhostButton, IconButton,
                       InstanceIcon, PrimaryButton, ProgressRow, divider, label,
                       network_image, round_pixmap, spacer, title)


class HomePage(QWidget):
    request_page = Signal(str)

    def __init__(self, window):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self._building = False
        self._recent_cols_now = 0
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        self.hello = ElidedLabel("", size=25, bold=True)
        self.subtitle = ElidedLabel("", size=13, color=theme.TEXT_DIM)
        hb = QVBoxLayout()
        hb.setSpacing(3)
        hb.addWidget(self.hello)
        hb.addWidget(self.subtitle)
        head.addLayout(hb, 1)
        self.tip = FlatCard()
        self.tip.setFixedWidth(340)
        tip_lay = QVBoxLayout(self.tip)
        tip_lay.setContentsMargins(12, 9, 12, 9)
        tip_lay.setSpacing(4)
        trow = QHBoxLayout()
        trow.setSpacing(7)
        ti = QLabel()
        ti.setPixmap(icons.make_pixmap("info", theme.WARNING, 15))
        trow.addWidget(ti, 0, Qt.AlignTop)
        trow.addWidget(label(self.cfg.t("tip_random"), size=11, bold=True,
                             color=theme.WARNING), 0, Qt.AlignTop)
        tip_lay.addLayout(trow)
        self.tip_text = label("", size=11, color=theme.TEXT_DIM, wrap=True)
        tip_lay.addWidget(self.tip_text)
        self.tip.setVisible(False)
        head.addWidget(self.tip, 0)
        root.addLayout(head)

        mid = QHBoxLayout()
        mid.setSpacing(12)
        root.addLayout(mid, 1)

        left = QVBoxLayout()
        left.setSpacing(11)
        mid.addLayout(left, 3)

        self.play_card = Card(clickable=False)
        self.play_card.setMinimumHeight(268)
        pl = QVBoxLayout(self.play_card)
        pl.setContentsMargins(16, 14, 16, 14)
        pl.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(11)
        self.inst_icon = InstanceIcon("#5aa469", 60)
        top.addWidget(self.inst_icon)
        box = QVBoxLayout()
        box.setSpacing(5)
        self.inst_name = ElidedLabel("", size=20, bold=True)
        self.inst_meta = QHBoxLayout()
        self.inst_meta.setSpacing(7)
        self.inst_badge = Badge("Vanilla", theme.INFO)
        self.inst_mc = label("", obj="Hint")
        box.addWidget(self.inst_name)
        box.addLayout(self.inst_meta)
        self.inst_note = ElidedLabel("", size=11, color=theme.TEXT_MUTED)
        box.addWidget(self.inst_note)
        box.addStretch(1)
        top.addLayout(box, 1)
        self.java_badge = Badge("", theme.TEXT_MUTED)
        top.addWidget(self.java_badge, 0, Qt.AlignTop)
        pl.addLayout(top)

        self.play_btn = QPushButton(self.cfg.t("play"))
        self.play_btn.setObjectName("Play")
        self.play_btn.setMinimumHeight(56)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(lambda: self.w.launch_selected())
        pl.addWidget(self.play_btn)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.btn_mods = GhostButton(self.cfg.t("nav_mods"), icon_name="package")
        self.btn_mods.clicked.connect(lambda: self.request_page.emit("mods"))
        self.btn_folder = GhostButton(self.cfg.t("open_folder"), icon_name="folder")
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_java = GhostButton(self.cfg.t("nav_java"), icon_name="coffee")
        self.btn_java.clicked.connect(lambda: self.request_page.emit("java"))
        self.btn_new = GhostButton(self.cfg.t("create_instance"), icon_name="plus")
        self.btn_new.clicked.connect(lambda: self.request_page.emit("instances"))
        for b in (self.btn_mods, self.btn_folder, self.btn_java, self.btn_new):
            row.addWidget(b)
        pl.addLayout(row)
        left.addWidget(self.play_card)

        self.progress = ProgressRow()
        self.progress.setVisible(False)
        left.addWidget(self.progress)

        rec_head = QHBoxLayout()
        rec_head.addWidget(label(self.cfg.t("recent_instances"), obj="SectionTitle"))
        rec_head.addStretch(1)
        all_btn = GhostButton(self.cfg.t("nav_instances") + " →")
        all_btn.clicked.connect(lambda: self.request_page.emit("instances"))
        rec_head.addWidget(all_btn)
        left.addLayout(rec_head)

        self.recent_row = QGridLayout()
        self.recent_row.setSpacing(8)
        left.addLayout(self.recent_row)

        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(11)
        mid.addLayout(right, 2)

        quick = FlatCard()
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(13, 11, 13, 13)
        ql.setSpacing(8)
        ql.addWidget(label(self.cfg.t("quick_actions"), obj="SectionTitle"))
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (name, glyph) in enumerate(instmod.LOADER_ORDER):
            btn = self._quick_button(name, glyph)
            grid.addWidget(btn, i // 2, i % 2)
        ql.addLayout(grid)
        right.addWidget(quick)

        stats = FlatCard()
        sl = QVBoxLayout(stats)
        sl.setContentsMargins(13, 11, 13, 13)
        sl.setSpacing(12)
        sl.addWidget(label(self.cfg.t("stat_title"), obj="SectionTitle"))
        self.stat_instances = self._stat_row(sl, "cube", "—", self.cfg.t("stat_instances"))
        self.stat_playtime = self._stat_row(sl, "sun", "—", self.cfg.t("stat_playtime"))
        self.stat_java = self._stat_row(sl, "coffee", "—", self.cfg.t("java"))
        self.stat_version = self._stat_row(sl, "shield", paths.app_version(),
                                           self.cfg.t("version"))
        right.addWidget(stats)
        right.addStretch(1)
        self.footer = FlatCard()
        fl = QHBoxLayout(self.footer)
        fl.setContentsMargins(13, 9, 13, 9)
        fl.setSpacing(14)
        kt_icon = QLabel()
        kt_icon.setPixmap(icons.make_pixmap("keyboard", theme.TEXT_MUTED, 17))
        kt_icon.setAlignment(Qt.AlignVCenter)
        fl.addWidget(kt_icon)
        fl.addWidget(label(self.cfg.t("hotkeys_title"), obj="SectionTitle"), 0,
                     Qt.AlignVCenter)

        kbox = QVBoxLayout()
        kbox.setSpacing(5)
        self.key_row = QHBoxLayout()
        self.key_row.setSpacing(6)
        for keys, tr, _section in shortcuts.shortcut_entries():
            self.key_row.addWidget(self._key_cap(keys, self.cfg.t(tr)))
        self.key_row.addStretch(1)
        kbox.addLayout(self.key_row)
        kbox.addWidget(label(self.cfg.t("hotkeys_hint"), size=11,
                             color=theme.TEXT_MUTED))
        fl.addLayout(kbox, 1)
        root.addWidget(self.footer)

    def _key_cap(self, keys: str, text: str) -> QLabel:
        cap = QLabel(keys)
        cap.setFont(theme.ui_font(11, 700))
        cap.setAlignment(Qt.AlignCenter)
        cap.setToolTip(text)
        cap.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        cap.setContentsMargins(8, 2, 8, 2)
        cap.setStyleSheet(
            f"background:{theme.CARD_ACTIVE};color:{theme.TEXT};"
            f"border:1px solid {theme.BORDER_LIGHT};"
            f"border-radius:{theme.RADIUS_BADGE}px;")
        cap.adjustSize()
        return cap

    def _quick_button(self, loader: str, glyph: str) -> QPushButton:
        soon = not instmod.loader_enabled(loader)
        color = instmod.LOADER_COLORS.get(loader, theme.TEXT_DIM)
        icon_color = theme.TEXT_MUTED if soon else color
        text = self.cfg.t(f"install_{loader}")
        btn = QPushButton(text if not soon else
                          f"{text} · {self.cfg.t('coming_soon')}")
        btn.setCursor(Qt.ArrowCursor if soon else Qt.PointingHandCursor)
        btn.setMinimumHeight(44)
        btn.setIcon(icons.make_icon(glyph, icon_color, 18))
        if soon:
            dim = theme.mix(theme.CARD, theme.BG, 0.45)
            btn.setEnabled(False)
            btn.setToolTip(self.cfg.t("loader_soon_hint"))
            btn.setStyleSheet(
                f"QPushButton{{background:{dim};border:1px solid {theme.BORDER};"
                f"border-radius:10px;font-weight:600;text-align:left;"
                f"padding-left:12px;color:{theme.TEXT_MUTED};}}"
                f"QPushButton:disabled{{background:{dim};"
                f"border:1px solid {theme.BORDER};color:{theme.TEXT_MUTED};}}")
        else:
            btn.setStyleSheet(
                f"QPushButton{{background:{theme.CARD};"
                f"border:1px solid {theme.BORDER_LIGHT};"
                f"border-radius:10px;font-weight:600;text-align:left;"
                f"padding-left:12px;color:{theme.TEXT};}}"
                f"QPushButton:hover{{background:{theme.CARD_HOVER};"
                f"border-color:{color};}}")
            btn.clicked.connect(lambda _=False, l=loader: self.w.start_install(l))
        return btn

    def _stat_row(self, parent_layout, glyph: str, value: str, name: str) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(9)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap(glyph, theme.TEXT_MUTED, 15))
        row.addWidget(ico)
        row.addWidget(label(name, obj="Dim", size=12))
        row.addStretch(1)
        val = label(value, size=12, bold=True)
        row.addWidget(val)
        parent_layout.addLayout(row)
        return val

    def refresh(self):
        cfg = get_config()
        self.cfg = cfg
        self.hello.setText(f"Привет, {cfg.get('nickname') or 'Player'}" if cfg.lang == "ru"
                           else f"Hello, {cfg.get('nickname') or 'Player'}")
        self.subtitle.setText(cfg.random_tip())
        self.tip_text.setText(cfg.random_tip())
        self.tip.setVisible(True)

        repo = instmod.repo()
        inst = self.w.selected_instance()
        running = self.w.running_instance

        if inst is None:
            self.inst_icon._color = theme.TEXT_MUTED
            self.inst_icon.update()
            self.inst_name.setText(cfg.t("instance_none"))
            self.inst_badge.setText("—")
            self.inst_badge.set_color(theme.TEXT_MUTED)
            self.inst_mc.setText("")
            self.inst_note.setText(cfg.t("instance_none_hint"))
            self.play_btn.setEnabled(False)
            self.play_btn.setText(cfg.t("create_instance"))
            self.btn_mods.setEnabled(False)
            self.btn_folder.setEnabled(False)
            self.java_badge.setText("—")
        else:
            color = instmod.LOADER_COLORS.get(inst.loader, theme.INFO)
            self.inst_icon._color = color
            self.inst_icon._glyph = {"vanilla": "grass", "forge": "hammer",
                                     "fabric": "layers", "quilt": "layers",
                                     "neoforge": "hammer", "optifine": "sun"}.get(
                                         inst.loader, "cube")
            self.inst_icon.update()
            self.inst_name.setText(inst.id)
            self.inst_badge.setText(inst.label)
            self.inst_badge.set_color(color)
            self.inst_mc.setText(f"Minecraft {inst.base_mc}")
            mods_n = inst.mod_count()
            parts = [f"{utils.format_playtime(inst.playtime)}", f"{mods_n} {cfg.t('mods_count')}"]
            if inst.last_played:
                parts.append(utils.relative_time(inst.last_played))
            self.inst_note.setText(" · ".join(parts))
            self.btn_mods.setEnabled(True)
            self.btn_folder.setEnabled(True)
            if running and running.id == inst.id:
                self.play_btn.setEnabled(False)
                self.play_btn.setText(cfg.t("playing"))
            else:
                self.play_btn.setEnabled(True)
                self.play_btn.setText(cfg.t("play"))

        searching = javamod.java_cache_state() is None
        if inst is not None:
            info = instmod.resolve_java(inst, cached_only=True)
            if info is None and searching:
                self.java_badge.setText(self.cfg.t("java_scanning"))
                self.java_badge.set_color(theme.TEXT_MUTED)
            elif info is None:
                need = javamod.required_java(inst.base_mc)
                self.java_badge.setText(self.cfg.t("java_needed_for", f"Java {need}"))
                self.java_badge.set_color(theme.WARNING)
            else:
                state = javamod.java_ok(inst.base_mc, info)
                colors = {"ok": theme.SUCCESS, "low": theme.WARNING, "high": theme.INFO}
                self.java_badge.setText(f"Java {info.major}")
                self.java_badge.set_color(colors.get(state, theme.TEXT_MUTED))
        else:
            jv = javamod.cached_javas()
            if jv:
                self.java_badge.setText(f"Java {jv[0].major}")
                self.java_badge.set_color(theme.SUCCESS)
            elif searching:
                self.java_badge.setText(self.cfg.t("java_scanning"))
                self.java_badge.set_color(theme.TEXT_MUTED)
            else:
                self.java_badge.setText("Java ?")
                self.java_badge.set_color(theme.WARNING)

        instances = repo.all()
        self.stat_instances.setText(str(len(instances)))
        self.stat_playtime.setText(utils.format_playtime(instmod.total_playtime()))
        jv = javamod.cached_javas()
        if jv:
            self.stat_java.setText(jv[0].version)
            java_color = theme.SUCCESS
        elif searching:
            self.stat_java.setText("…")
            java_color = theme.TEXT_MUTED
        else:
            self.stat_java.setText("—")
            java_color = theme.WARNING
        self.stat_java.setStyleSheet(f"color:{java_color};"
                                     "background:transparent;font-weight:700;")
        self._refresh_recent(instances)

    RECENT_MIN_W = 132
    RECENT_H = 96
    RECENT_COLS_MAX = 4
    RECENT_ROWS_MAX = 2

    def _recent_cols(self) -> int:
        gap = self.recent_row.spacing() or 8
        avail = self.recent_row.geometry().width()
        if avail <= 0:
            avail = max(1, (self.width() - 12) * 3 // 5)
        cols = (avail + gap) // (self.RECENT_MIN_W + gap)
        return max(1, min(self.RECENT_COLS_MAX, int(cols)))

    def _refresh_recent(self, instances):
        while self.recent_row.count():
            item = self.recent_row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        cols = self._recent_cols()
        self._recent_cols_now = cols
        shown = instances[:cols * self.RECENT_ROWS_MAX]
        for n, inst in enumerate(shown):
            card = Card()
            card.setMinimumWidth(self.RECENT_MIN_W)
            card.setFixedHeight(self.RECENT_H)
            card.setToolTip(f"{inst.id}\n{inst.label} {inst.base_mc}")
            lay = QVBoxLayout(card)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(4)
            top = QHBoxLayout()
            top.setSpacing(6)
            ic = InstanceIcon(instmod.LOADER_COLORS.get(inst.loader, theme.INFO), 22)
            top.addWidget(ic)
            top.addWidget(ElidedLabel(inst.label, size=11, bold=True,
                                      color=instmod.LOADER_COLORS.get(inst.loader,
                                                                     theme.INFO)), 1)
            lay.addLayout(top)
            nm = ElidedLabel(inst.base_mc, size=12, bold=True)
            nm.setToolTip(inst.id)
            lay.addWidget(nm)
            lay.addWidget(label(utils.format_playtime(inst.playtime), size=11,
                                color=theme.TEXT_MUTED))
            lay.addStretch(1)
            card.clicked.connect(lambda i=inst: self.w.select_instance(i.id))
            self.recent_row.addWidget(card, n // cols, n % cols)
        for c in range(cols):
            self.recent_row.setColumnStretch(c, 1)
        used = len(shown)
        for k in range(used, ((used + cols - 1) // cols) * cols):
            self.recent_row.addWidget(spacer(), k // cols, k % cols)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._recent_cols() != getattr(self, "_recent_cols_now", 0):
            self._refresh_recent(instmod.repo().all())

    def _open_folder(self):
        inst = self.w.selected_instance()
        if inst:
            utils.open_path(inst.path)
        else:
            utils.open_path(paths.data_dir())

    def show_progress(self, text: str = "", percent: int = -1):
        self._status_text = text or ""
        self.progress.setVisible(True)
        if text:
            self.progress.set(text, percent)

    def set_progress(self, downloaded: int, total: int, percent: int):
        if total > 0 and total != 100:
            size_text = f"{paths.human_size(downloaded)} / {paths.human_size(total)}"
        else:
            size_text = f"{percent}%"
        text = f"{getattr(self, '_status_text', '')}  {size_text}".strip()
        self.progress.set(text, percent)

    def hide_progress(self):
        self.progress.setVisible(False)
