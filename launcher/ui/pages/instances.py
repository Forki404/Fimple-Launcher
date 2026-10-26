from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QMenu, QSizePolicy, QVBoxLayout, QWidget)

from ... import instances as instmod
from ... import paths, utils
from ...config import get_config
from .. import icons, theme
from ..dialogs import InstallDialog
from ..widgets import (Badge, Card, Chip, ElidedLabel, FlatCard, GhostButton, IconButton,
                       InstanceIcon, PrimaryButton, ScrollArea, SearchBox, label, spacer)

FILTERS = [
    ("all", "cube", None),
    ("vanilla", "grass", "vanilla"),
    ("forge", "hammer", "forge"),
    ("neoforge", "hammer", "neoforge"),
    ("fabric", "layers", "fabric"),
    ("quilt", "layers", "quilt"),
    ("optifine", "sun", "optifine"),
]

FILTER_LABEL_KEY = {
    "all": "all", "vanilla": "install_vanilla", "forge": "install_forge",
    "neoforge": "install_neoforge", "fabric": "install_fabric",
    "quilt": "install_quilt", "optifine": "install_optifine",
}


class InstancesPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self.filter = "all"
        self.query = ""
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        head = QHBoxLayout()
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(label(self.cfg.t("nav_instances"), size=25, bold=True))
        self.subtitle = ElidedLabel("", size=13, color=theme.TEXT_DIM)
        box.addWidget(self.subtitle)
        head.addLayout(box, 1)

        self.search = SearchBox(self.cfg.t("search_placeholder"))
        self.search.setFixedWidth(240)
        self.search.textChanged.connect(self._on_search)
        head.addWidget(self.search)

        self.btn_new = PrimaryButton(self.cfg.t("create_instance"))
        self.btn_new.setIcon(icons.make_icon("plus", "#ffffff", 16))
        self.btn_new.clicked.connect(lambda: self.w.pick_install_loader())
        head.addWidget(self.btn_new)
        root.addLayout(head)

        chips = QHBoxLayout()
        chips.setSpacing(7)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        for key, glyph, loader in FILTERS:
            soon = loader in instmod.DISABLED_LOADERS
            chip = Chip(self.cfg.t(FILTER_LABEL_KEY[key])
                        + (" · " + self.cfg.t("coming_soon") if soon else ""))
            chip.setIcon(icons.make_icon(glyph,
                                         theme.TEXT_MUTED if soon else
                                         instmod.LOADER_COLORS.get(loader or "", theme.TEXT_DIM)
                                         if loader else theme.TEXT_DIM, 14))
            if soon:
                chip.setEnabled(False)
                chip.setToolTip(self.cfg.t("loader_soon_hint"))
            chip.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            chip.setProperty("key", key)
            self.group.addButton(chip)
            chips.addWidget(chip)
            if key == "all":
                chip.setChecked(True)
        chips.addStretch(1)
        self.count_label = label("", obj="Hint")
        chips.addWidget(self.count_label)
        root.addLayout(chips)

        self.scroll = ScrollArea()
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignTop)
        self.scroll.body.addWidget(self.grid_host)
        self.scroll.body.addStretch(1)
        root.addWidget(self.scroll, 1)

        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.setAlignment(Qt.AlignCenter)
        el.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("cube", theme.TEXT_MUTED, 56))
        ico.setAlignment(Qt.AlignCenter)
        el.addWidget(ico)
        self.empty_title = label(self.cfg.t("instance_none"), size=17, bold=True)
        self.empty_title.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_title)
        self.empty_hint = label(self.cfg.t("instance_none_hint"), obj="Hint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_hint)
        create = PrimaryButton(self.cfg.t("create_instance"))
        create.setIcon(icons.make_icon("plus", "#ffffff", 16))
        create.clicked.connect(lambda: self.w.pick_install_loader())
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(create)
        row.addStretch(1)
        el.addLayout(row)
        self.empty.setVisible(False)
        root.addWidget(self.empty, 1)

    def _on_search(self, text: str):
        self.query = text.strip().lower()
        self.render()

    def _set_filter(self, key: str):
        self.filter = key
        self.render()

    def refresh(self):
        self.cfg = get_config()
        instances = instmod.repo().all()
        self.subtitle.setText(f"{len(instances)} {self.cfg.t('stat_instances')}")
        self.render()

    def _visible(self) -> List[instmod.Instance]:
        out = []
        for i in instmod.repo().all():
            if self.filter != "all" and i.loader != self.filter:
                continue
            if self.query and self.query not in i.id.lower() and self.query not in i.base_mc.lower():
                continue
            out.append(i)
        return out

    def render(self):
        scroll_pos = self.scroll.verticalScrollBar().value()
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        items = self._visible()
        self.count_label.setText(f"{len(items)}" if items else "")
        self.empty.setVisible(not items)
        self.scroll.setVisible(bool(items))
        if not items:
            if self.query:
                self.empty_title.setText(self.cfg.t("empty_search"))
                self.empty_hint.setText(f"«{self.query}»")
            else:
                self.empty_title.setText(self.cfg.t("instance_none"))
                self.empty_hint.setText(self.cfg.t("instance_none_hint"))
            return

        selected_id = self.w.current_id()
        columns = 3 if self.w.width() > 1000 else (2 if self.w.width() > 700 else 1)
        for c in range(max(columns, self.grid.columnCount())):
            self.grid.setColumnStretch(c, 0)
        for idx, inst in enumerate(items):
            card = self._card(inst, selected_id == inst.id)
            self.grid.addWidget(card, idx // columns, idx % columns)
        for c in range(columns):
            self.grid.setColumnStretch(c, 1)
        self.scroll.verticalScrollBar().setValue(scroll_pos)

    def _card(self, inst: instmod.Instance, selected: bool) -> QWidget:
        cfg = get_config()
        color = instmod.LOADER_COLORS.get(inst.loader, theme.INFO)
        card = Card(selected=selected)
        card.setMinimumHeight(184)
        card.setMinimumWidth(240)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(lambda pos, i=inst: self._menu(i, card, pos))

        lay = QVBoxLayout(card)
        lay.setContentsMargins(13, 11, 12, 12)
        lay.setSpacing(9)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(InstanceIcon(color, 42, {
            "vanilla": "grass", "forge": "hammer", "fabric": "layers",
            "quilt": "layers", "neoforge": "hammer", "optifine": "sun"}.get(inst.loader, "cube")))
        box = QVBoxLayout()
        box.setSpacing(3)
        name = ElidedLabel(inst.id, size=14, bold=True)
        name.setToolTip(str(inst.path))
        box.addWidget(name)
        badges = QHBoxLayout()
        badges.setSpacing(6)
        badges.addWidget(Badge(inst.label, color))
        badges.addWidget(ElidedLabel(f"MC {inst.base_mc}", size=11,
                                     color=theme.TEXT_MUTED), 1)
        box.addLayout(badges)
        top.addLayout(box, 1)
        lay.addLayout(top)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        stats.addWidget(self._stat("sun", utils.format_playtime(inst.playtime),
                                   cfg.t("playtime")))
        stats.addWidget(self._stat("package", f"{inst.mod_count()}",
                                   cfg.t("mods_count")))
        if inst.last_played:
            stats.addWidget(self._stat("terminal", utils.relative_time(inst.last_played),
                                       cfg.t("last_played")))
        stats.addStretch(1)
        lay.addLayout(stats)

        from ... import java as javamod

        jinfo = instmod.resolve_java(inst, cached_only=True)
        row = QHBoxLayout()
        row.setSpacing(6)
        ji = QLabel()
        ji.setPixmap(icons.make_pixmap("coffee", theme.TEXT_MUTED, 13))
        row.addWidget(ji)
        if jinfo is None and javamod.java_cache_state() is None:
            row.addWidget(label(cfg.t("java_scanning"), size=11,
                                color=theme.TEXT_MUTED))
        elif jinfo is None:
            need = javamod.required_java(inst.base_mc)
            row.addWidget(label(f"{cfg.t('java_needed_for', f'Java {need}')} · "
                                f"{cfg.t('java_download')}", size=11,
                                color=theme.WARNING))
        else:
            state = javamod.java_ok(inst.base_mc, jinfo)
            col = {"ok": theme.SUCCESS, "low": theme.WARNING, "high": theme.INFO}[state]
            row.addWidget(label(f"Java {jinfo.major}", size=11, color=col))
        row.addStretch(1)
        lay.addLayout(row)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        b_play = PrimaryButton(cfg.t("launch"))
        b_play.setIcon(icons.make_icon("play", "#ffffff", 14))
        b_play.setMinimumHeight(34)
        b_play.clicked.connect(lambda: self.w.launch_instance(inst))
        buttons.addWidget(b_play, 1)
        b_mods = GhostButton("", icon_name="package")
        b_mods.setFixedWidth(40)
        b_mods.setToolTip(cfg.t("nav_mods"))
        b_mods.clicked.connect(lambda: self.w.open_instance_mods(inst))
        b_folder = GhostButton("", icon_name="folder")
        b_folder.setFixedWidth(40)
        b_folder.setToolTip(cfg.t("open_folder"))
        b_folder.clicked.connect(lambda: utils.open_path(inst.path))
        buttons.addWidget(b_folder)
        menu_btn = IconButton("sliders", theme.TEXT_MUTED, 34, tip="...")
        menu_btn.clicked.connect(lambda: self._menu(inst, menu_btn,
                                                    menu_btn.rect().bottomLeft()))
        buttons.addWidget(menu_btn)
        lay.addLayout(buttons)
        return card

    def _stat(self, glyph: str, value: str, name: str) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap(glyph, theme.TEXT_MUTED, 12))
        row.addWidget(ico)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(label(value, size=12, bold=True))
        col.addWidget(label(name, size=10, color=theme.TEXT_MUTED))
        row.addLayout(col)
        return w

    def _menu(self, inst: instmod.Instance, parent: QWidget, pos):
        cfg = get_config()
        m = QMenu(parent)
        m.addAction(icons.make_icon("play", theme.SUCCESS, 16), cfg.t("launch"),
                    lambda: self.w.launch_instance(inst))
        m.addAction(icons.make_icon("package", theme.INFO, 16), cfg.t("nav_mods"),
                    lambda: self.w.open_instance_mods(inst))
        m.addAction(icons.make_icon("folder", theme.TEXT_DIM, 16), cfg.t("open_folder"),
                    lambda: utils.open_path(inst.path))
        m.addAction(icons.make_icon("copy", theme.TEXT_DIM, 16),
                    f"{cfg.t('mods_dir')} / saves", lambda: utils.open_path(inst.path / "mods"))
        m.addSeparator()
        m.addAction(icons.make_icon("edit", theme.TEXT_DIM, 16), cfg.t("rename"),
                    lambda: self._rename(inst))
        m.addAction(icons.make_icon("trash", theme.DANGER, 16), cfg.t("delete_instance"),
                    lambda: self._delete(inst))
        m.exec(parent.mapToGlobal(pos))

    def _rename(self, inst: instmod.Instance):
        from ..dialogs import text_input

        new = text_input(self, self.cfg.t("rename"), inst.id, inst.id)
        if not new or new == inst.id:
            return
        res = instmod.repo().rename(inst, new)
        if res is None:
            from ..dialogs import warn

            warn(self, get_config().t("error"), get_config().t("error"))
        self.w.refresh_all()
        from ..widgets import toast

        toast(self, get_config().t("instance_renamed"), "success")

    def _delete(self, inst: instmod.Instance):
        from ..dialogs import confirm

        cfg = get_config()
        if not confirm(self, cfg.t("delete_instance_confirm", inst.id),
                       cfg.t("delete_instance")):
            return
        instmod.repo().delete(inst)
        if self.w.current_id() == inst.id:
            self.w.select_instance(None)
        self.w.refresh_all()
        from ..widgets import toast

        toast(self, cfg.t("instance_deleted"), "success")
