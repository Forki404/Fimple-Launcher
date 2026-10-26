from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QHBoxLayout, QLabel, QTabWidget,
                               QVBoxLayout, QWidget)

from ... import instances as instmod
from ... import modrinth
from ... import paths, utils
from ...config import get_config
from .. import dialogs, icons, theme
from ..widgets import (Badge, Card, Chip, ComboBox, ElidedLabel, FlatCard,
                       GhostButton, IconButton, PrimaryButton, ScrollArea, SearchBox,
                       label, network_image, spacer, toast)

LOADER_FILTERS = [("fabric", "Fabric"), ("forge", "Forge"), ("neoforge", "NeoForge"),
                  ("quilt", "Quilt")]


class ModsPage(QWidget):
    def __init__(self, window, instance: Optional[instmod.Instance] = None):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self.instance: Optional[instmod.Instance] = instance or window.selected_instance()
        self.query = ""
        self.loader_filter = ""
        self._search_timer: Optional[QTimer] = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        head = QHBoxLayout()
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(label(self.cfg.t("nav_mods"), size=25, bold=True))
        self.subtitle = ElidedLabel("", size=13, color=theme.TEXT_DIM)
        box.addWidget(self.subtitle)
        head.addLayout(box, 1)

        head.addWidget(label(self.cfg.t("version"), obj="Dim"))
        self.instance_combo = ComboBox()
        self.instance_combo.setMinimumWidth(220)
        self.instance_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.instance_combo.setMinimumContentsLength(18)
        self.instance_combo.currentIndexChanged.connect(self._on_instance_changed)
        head.addWidget(self.instance_combo)
        self.btn_folder = GhostButton(self.cfg.t("open_folder"), icon_name="folder")
        self.btn_folder.clicked.connect(self._open_mods_dir)
        head.addWidget(self.btn_folder)
        root.addLayout(head)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tab_installed = QWidget()
        self.tab_search = QWidget()
        self.tabs.addTab(self.tab_installed, self.cfg.t("installed_mods"))
        self.tabs.addTab(self.tab_search, self.cfg.t("mods_search"))
        self.tabs.currentChanged.connect(self._on_tab)
        root.addWidget(self.tabs, 1)

        self._build_installed()
        self._build_search()

    def _build_installed(self):
        lay = QVBoxLayout(self.tab_installed)
        lay.setContentsMargins(12, 11, 6, 8)
        lay.setSpacing(10)
        self.tabs.setDocumentMode(True)
        self.installed_host = QWidget()
        self.installed_list = QVBoxLayout(self.installed_host)
        self.installed_list.setContentsMargins(0, 0, 0, 0)
        self.installed_list.setSpacing(8)
        self.installed_scroll = ScrollArea()
        self.installed_scroll.setWidget(self.installed_host)
        lay.addWidget(self.installed_scroll, 1)
        self.installed_empty = QWidget()
        el = QVBoxLayout(self.installed_empty)
        el.setAlignment(Qt.AlignCenter)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("package", theme.TEXT_MUTED, 46))
        ico.setAlignment(Qt.AlignCenter)
        el.addWidget(ico)
        lab = ElidedLabel(self.cfg.t("no_mods"), size=12, color=theme.TEXT_MUTED)
        lab.setAlignment(Qt.AlignCenter)
        el.addWidget(lab)
        self.installed_empty_hint = lab
        btn = PrimaryButton(self.cfg.t("mods_search"))
        btn.setIcon(icons.make_icon("search", "#ffffff", 15))
        btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(btn)
        row.addStretch(1)
        el.addLayout(row)
        self.installed_empty.setVisible(False)
        lay.addWidget(self.installed_empty, 1)

    def _build_search(self):
        lay = QVBoxLayout(self.tab_search)
        lay.setContentsMargins(12, 11, 6, 8)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.search = SearchBox(self.cfg.t("mods_search"))
        self.search.textChanged.connect(self._on_search_text)
        top.addWidget(self.search, 1)
        self.loader_group = QButtonGroup(self)
        self.loader_group.setExclusive(True)
        self.loader_group.buttonClicked.connect(self._on_loader)
        chip = Chip(self.cfg.t("all"))
        chip.setChecked(True)
        chip.setProperty("key", "")
        self.loader_group.addButton(chip)
        top.addWidget(chip)
        for key, text in LOADER_FILTERS:
            c = Chip(text)
            c.setProperty("key", key)
            self.loader_group.addButton(c)
            top.addWidget(c)
        lay.addLayout(top)

        self.results_host = QWidget()
        self.results_list = QVBoxLayout(self.results_host)
        self.results_list.setContentsMargins(0, 0, 0, 0)
        self.results_list.setSpacing(8)
        self.results_scroll = ScrollArea()
        self.results_scroll.setWidget(self.results_host)
        lay.addWidget(self.results_scroll, 1)

        self.search_status = ElidedLabel(self.cfg.t("mods_searching"), size=12,
                                         color=theme.TEXT_MUTED)
        lay.addWidget(self.search_status)

        self.results_empty = QWidget()
        el = QVBoxLayout(self.results_empty)
        el.setAlignment(Qt.AlignCenter)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("search", theme.TEXT_MUTED, 44))
        ico.setAlignment(Qt.AlignCenter)
        el.addWidget(ico)
        lab = label("Modrinth", size=16, bold=True)
        lab.setAlignment(Qt.AlignCenter)
        el.addWidget(lab)
        hint = ElidedLabel("sodium · lithium · iris · iris-and-sodium", size=12,
                           color=theme.TEXT_MUTED)
        hint.setAlignment(Qt.AlignCenter)
        el.addWidget(hint)
        self.results_empty.setVisible(True)
        lay.addWidget(self.results_empty, 1)

    def set_instance(self, inst: Optional[instmod.Instance]):
        self.instance = inst
        self._reload_combo()
        self.render_installed()
        self.render_results()

    def _reload_combo(self):
        self.instance_combo.blockSignals(True)
        self.instance_combo.clear()
        for i in instmod.repo().all():
            self.instance_combo.addItem(f"{i.label} · {i.base_mc}", i.id)
            if self.instance and i.id == self.instance.id:
                self.instance_combo.setCurrentIndex(self.instance_combo.count() - 1)
        self.instance_combo.blockSignals(False)
        if not self.instance_combo.count():
            self.instance = None

    def refresh(self):
        self.cfg = get_config()
        self._reload_combo()
        inst = self.instance
        if inst:
            self.subtitle.setText(f"{self.cfg.t('mods_of_instance', inst.id)} · "
                                  f"{inst.mod_count()} {self.cfg.t('mods_count')}")
        else:
            self.subtitle.setText(self.cfg.t("instance_none_hint"))
        self.render_installed()

    def _clear_layout(self, lay) -> None:
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def render_installed(self):
        self._clear_layout(self.installed_list)
        if not self.instance:
            self.installed_scroll.setVisible(False)
            self.installed_empty.setVisible(True)
            if self.installed_empty_hint:
                self.installed_empty_hint.setText(self.cfg.t("instance_none_hint"))
            return
        if self.installed_empty_hint:
            self.installed_empty_hint.setText(self.cfg.t("no_mods"))
        mods = modrinth.list_local_mods(self.instance.path)
        self.installed_scroll.setVisible(bool(mods))
        self.installed_empty.setVisible(not mods)
        if not mods:
            return
        for name, path, enabled in mods:
            row = self._mod_row(name, path, enabled)
            self.installed_list.addWidget(row)
            self.installed_list.setAlignment(row, Qt.AlignTop)
        self.installed_list.addStretch(1)

    def _mod_row(self, name: str, path, enabled: bool) -> QWidget:
        card = FlatCard()
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 6, 8, 6)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignVCenter)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("package",
                                         theme.SUCCESS if enabled else theme.TEXT_MUTED, 16))
        lay.addWidget(ico, 0, Qt.AlignVCenter)
        nm = ElidedLabel(name, size=12, bold=not enabled,
                         color=theme.TEXT if enabled else theme.TEXT_MUTED)
        nm.setToolTip(str(path))
        lay.addWidget(nm, 1)
        state = Badge("✓" if enabled else "✕",
                      theme.SUCCESS if enabled else theme.TEXT_MUTED)
        state.setFixedWidth(30)
        lay.addWidget(state, 0, Qt.AlignVCenter)
        size = label(utils.human_size(path.stat().st_size if path.exists() else 0),
                     size=11, color=theme.TEXT_MUTED)
        lay.addWidget(size)
        toggle = GhostButton(self.cfg.t("disable") if enabled else self.cfg.t("enable"))
        toggle.setFixedWidth(66)
        toggle.clicked.connect(lambda: self._toggle(path, enabled))
        lay.addWidget(toggle)
        rm = IconButton("trash", theme.DANGER, 30)
        rm.clicked.connect(lambda: self._remove(path, name))
        lay.addWidget(rm)
        return card

    def _toggle(self, path, enabled: bool):
        modrinth.set_mod_enabled(path, not enabled)
        self.render_installed()
        self.w.refresh_all()

    def _remove(self, path, name: str):
        if not dialogs.confirm(self, f"{self.cfg.t('uninstall_mod')}: {name}?",
                                self.cfg.t("uninstall_mod")):
            return
        modrinth.remove_mod(path)
        toast(self, self.cfg.t("mod_uninstalled", name), "success")
        self.render_installed()
        self.w.refresh_all()

    def _open_mods_dir(self):
        if self.instance:
            utils.open_path(self.instance.path / "mods")

    def _on_instance_changed(self, idx: int):
        if idx < 0:
            return
        iid = self.instance_combo.itemData(idx)
        inst = instmod.repo().get(iid)
        if inst:
            self.instance = inst
            self.w.select_instance(iid)
            self.render_installed()
            self.render_results()

    def _on_loader(self, btn):
        key = btn.property("key") or ""
        self.loader_filter = key
        self.render_results()
        if self.query:
            self._do_search()

    def _on_search_text(self, text: str):
        self.query = text.strip()
        if self._search_timer:
            self._search_timer.stop()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(420)
        self._search_timer.timeout.connect(self._do_search)
        if self.query:
            self._search_timer.start()

    def _on_tab(self, idx: int):
        if idx == 1 and self.query and not self.results_list.count():
            self._do_search()

    def _game_version(self) -> str:
        if self.instance and not self.instance.is_fabric_like:
            return ""
        return self.instance.base_mc if self.instance else ""

    def _mod_loaders(self) -> List[str]:
        if self.loader_filter:
            return [self.loader_filter]
        if self.instance:
            return [self.instance.loader] if self.instance.is_fabric_like else ["fabric", "forge"]
        return ["fabric", "forge"]

    def _do_search(self):
        from ...workers import background

        if not self.query:
            self.results_list_host_visible(False)
            return
        loaders = self._mod_loaders()
        gv = self._game_version()
        self.search_status.setText(self.cfg.t("mods_searching"))

        def work():
            return modrinth.search(self.query, loaders, gv, "mod", 30)

        self.worker = background(work, on_result=self.render_results,
                                 on_error=self._search_error)

    def _search_error(self, e: str):
        self.search_status.setText(f"{self.cfg.t('mods_error')}: {e}")

    def results_list_host_visible(self, v: bool):
        self.results_scroll.setVisible(v)
        self.results_empty.setVisible(not v)

    def render_results(self, projects=None):
        self._clear_layout(self.results_list)
        if projects is None:
            projects = []
        if not projects and self.query:
            self.search_status.setText(self.cfg.t("empty_search"))
        else:
            self.search_status.setText("" if not projects else
                                       self.cfg.t("search_results", len(projects)))
        self.results_list_host_visible(bool(projects))
        for p in projects:
            row = self._project_row(p)
            self.results_list.addWidget(row)
            self.results_list.setAlignment(row, Qt.AlignTop)
        self.results_list.addStretch(1)

    def _project_row(self, p: modrinth.Project) -> QWidget:
        card = Card()
        card.setMinimumHeight(76)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(12)
        if p.icon:
            lay.addWidget(network_image(p.icon, 44))
        else:
            box = QLabel()
            box.setPixmap(icons.make_pixmap("package", theme.TEXT_MUTED, 30))
            box.setFixedSize(44, 44)
            lay.addWidget(box)
        info = QVBoxLayout()
        info.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(7)
        top.addWidget(ElidedLabel(p.title, size=13, bold=True), 1)
        top.addWidget(Badge(f"↓ {p.downloads_text()}", theme.TEXT_MUTED))
        info.addLayout(top)
        if p.description:
            d = ElidedLabel(p.description, size=12, color=theme.TEXT_MUTED)
            d.setToolTip(p.description)
            info.addWidget(d)
        lay.addLayout(info, 1)
        btn = PrimaryButton(self.cfg.t("install_mod"))
        btn.setMinimumWidth(126)
        btn.setIcon(icons.make_icon("download", "#ffffff", 15))
        btn.clicked.connect(lambda: self._open_versions(p))
        lay.addWidget(btn, 0)
        link = IconButton("external", theme.TEXT_MUTED, 32)
        link.setToolTip(self.cfg.t("open_modrinth"))
        link.clicked.connect(lambda: __import__("webbrowser").open(p.url))
        lay.addWidget(link, 0)
        return card

    def _open_versions(self, p: modrinth.Project):
        dlg = dialogs.ModVersionsDialog(p, self._mod_loaders(), self._game_version(), self)
        dlg.installed.connect(self._install_version)
        dlg.exec()

    def _install_version(self, project_id: str, version_id: str):
        if not self.instance:
            dialogs.warn(self, self.cfg.t("instance_none_hint"), self.cfg.t("error"))
            return
        self.tabs.setCurrentIndex(0)
        self.w.install_mod_to_instance(self.instance, project_id, version_id)
        self.render_installed()
