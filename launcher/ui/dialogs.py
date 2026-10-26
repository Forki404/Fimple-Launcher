from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                               QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout,
                               QWidget)

from .. import modrinth
from ..config import get_config
from . import icons, theme
from .widgets import (Badge, Card, Chip, ElidedLabel, FlatCard, GhostButton, IconButton,
                      PrimaryButton, ScrollArea, SearchBox, label, network_image,
                      round_pixmap, spacer, title)


def _apply(parent: QWidget) -> None:
    dlg = QDialog(parent)
    dlg.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
    return dlg


def message(parent, text: str, kind: str = "info", title_text: str = "") -> QMessageBox:
    icons_map = {"info": QMessageBox.Information, "warning": QMessageBox.Warning,
                 "error": QMessageBox.Critical, "question": QMessageBox.Question}
    box = QMessageBox(parent)
    box.setIcon(icons_map.get(kind, QMessageBox.Information))
    box.setText(text)
    box.setWindowTitle(title_text or get_config().t("app_title"))
    box.setTextInteractionFlags(Qt.TextSelectableByMouse)
    box.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
    btn = box.addButton(get_config().t("ok"), QMessageBox.AcceptRole)
    btn.setObjectName("Primary")
    btn.setMinimumWidth(96)
    box.exec()
    return box


def info(parent, text: str, title_text: str = "") -> None:
    message(parent, text, "info", title_text)


def warn(parent, text: str, title_text: str = "") -> None:
    message(parent, text, "warning", title_text)


def error(parent, text: str, title_text: str = "") -> None:
    message(parent, text, "error", title_text)


def confirm(parent, text: str, title_text: str = "", yes_text: str = "",
            no_text: str = "") -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setText(text)
    box.setWindowTitle(title_text or get_config().t("warning"))
    box.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
    yes = box.addButton(yes_text or get_config().t("yes"), QMessageBox.YesRole)
    no = box.addButton(no_text or get_config().t("no"), QMessageBox.NoRole)
    yes.setObjectName("Primary")
    yes.setMinimumWidth(96)
    no.setMinimumWidth(96)
    box.exec()
    return box.clickedButton() is yes


def text_input(parent, title_text: str, placeholder: str = "", value: str = "") -> Optional[str]:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title_text)
    dlg.setModal(True)
    dlg.setMinimumWidth(420)
    dlg.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(22, 20, 22, 18)
    lay.setSpacing(14)
    lay.addWidget(label(title_text, size=17, bold=True))
    edit = QLineEdit(value)
    edit.setPlaceholderText(placeholder)
    edit.selectAll()
    lay.addWidget(edit)
    row = QHBoxLayout()
    row.addStretch(1)
    cancel = GhostButton(get_config().t("cancel"))
    ok = PrimaryButton(get_config().t("ok"))
    row.addWidget(cancel)
    row.addWidget(ok)
    lay.addLayout(row)

    def accept():
        dlg.accept()

    ok.clicked.connect(accept)
    edit.returnPressed.connect(accept)
    cancel.clicked.connect(dlg.reject)
    edit.setFocus()
    if dlg.exec() == QDialog.Accepted:
        return edit.text().strip() or None
    return None


class ElyLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(get_config().t("ely_title"))
        self.setModal(True)
        self.setFixedWidth(430)
        self.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
        self.result_account = None
        self._worker = None
        self._logging_in = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)

        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(icons.make_pixmap("shield", theme.accent(get_config().get("accent")), 34))
        head.addWidget(logo)
        head.addSpacing(6)
        box = QVBoxLayout()
        box.setSpacing(2)
        box.addWidget(label(get_config().t("ely_title"), size=18, bold=True))
        box.addWidget(label("authserver.ely.by", obj="Mono"))
        head.addLayout(box)
        head.addStretch(1)
        lay.addLayout(head)

        self.email = QLineEdit()
        self.email.setPlaceholderText(get_config().t("ely_email"))
        self.password = QLineEdit()
        self.password.setPlaceholderText(get_config().t("ely_password"))
        self.password.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.email)
        lay.addWidget(self.password)
        lay.addWidget(label(get_config().t("password_not_saved"), size=11,
                            color=theme.TEXT_MUTED))

        self.status = label("", size=12, color=theme.DANGER)
        self.status.setWordWrap(True)
        self.status.setVisible(False)
        lay.addWidget(self.status)

        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedHeight(6)
        self.busy.setTextVisible(False)
        self.busy.setVisible(False)
        lay.addWidget(self.busy)

        row = QHBoxLayout()
        self.show_btn = GhostButton("")
        self.show_btn.setIcon(icons.make_icon("search", theme.TEXT_DIM, 16))
        self.show_btn.setFixedWidth(38)
        self.show_btn.setToolTip(get_config().t("show_password"))
        self.show_btn.clicked.connect(self._toggle_pw)
        row.addWidget(self.show_btn)
        row.addStretch(1)
        cancel = GhostButton(get_config().t("cancel"))
        self.ok_btn = PrimaryButton(get_config().t("add_account"))
        row.addWidget(cancel)
        row.addWidget(self.ok_btn)
        lay.addLayout(row)

        cancel.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._login)
        self.password.returnPressed.connect(self._login)
        self.email.setFocus()

    def _toggle_pw(self):
        show = self.password.echoMode() == QLineEdit.Password
        self.password.setEchoMode(QLineEdit.Normal if show else QLineEdit.Password)

    def _login(self):
        from .. import accounts
        from ..workers import background

        if self._logging_in:
            return
        self.status.setVisible(False)
        email, pw = self.email.text().strip(), self.password.text()
        if not email or not pw:
            self.status.setText(get_config().t("fill_both_fields"))
            self.status.setVisible(True)
            return

        self._set_busy(True, get_config().t("signing_in"))

        def work():
            return accounts.store().login_ely(email, pw)

        self._logging_in = True
        self._worker = background(work, on_result=self._logged_in,
                                  on_error=self._login_error,
                                  on_finish=self._login_finished, parent=self)

    def _login_finished(self) -> None:
        self._logging_in = False
        self._worker = None

    def _set_busy(self, busy: bool, text: str = "") -> None:
        self.busy.setVisible(busy)
        self.ok_btn.setEnabled(not busy)
        self.email.setEnabled(not busy)
        self.password.setEnabled(not busy)
        self.show_btn.setEnabled(not busy)
        if busy:
            self.ok_btn.setText(text or "…")

    def _logged_in(self, account) -> None:
        self._set_busy(False)
        self.ok_btn.setText(get_config().t("add_account"))
        self.result_account = account
        self.accept()

    def _login_error(self, e: str) -> None:
        self._set_busy(False)
        self.ok_btn.setText(get_config().t("add_account"))
        self.status.setText(f"{get_config().t('ely_failed')}: {e}")
        self.status.setVisible(True)
        self.password.selectAll()
        self.password.setFocus()


class VersionPicker(QWidget):
    def __init__(self, parent=None, compact: bool = False):
        super().__init__(parent)
        self.versions: List[Tuple[str, str, int]] = []
        self.query = ""
        self.filter = "release"
        self.chosen = ""
        self.on_choose: Callable[[str], None] = lambda v: None
        self._loading = True

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.search = SearchBox(get_config().t("search_versions"))
        self.search.textChanged.connect(self._on_search)
        top.addWidget(self.search, 1)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.chips: dict = {}
        for key, text_key in (("release", "type_release"), ("snapshot", "type_snapshot"),
                              ("all", "type_all")):
            chip = Chip(get_config().t(text_key))
            chip.setProperty("key", key)
            chip.clicked.connect(lambda _=False, k=key: self._set_filter(k))
            self.group.addButton(chip)
            self.chips[key] = chip
            top.addWidget(chip)
            if key == self.filter:
                chip.setChecked(True)
        lay.addLayout(top)

        self.scroll = ScrollArea()
        self.inner = QWidget()
        self.list_layout = QVBoxLayout(self.inner)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(5)
        self.scroll.setWidget(self.inner)
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(220 if compact else 300)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll.setMaximumHeight(340 if compact else 440)
        lay.addWidget(self.scroll, 1)

        self.status = label(get_config().t("versions_loading"), obj="Hint")
        self.status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status)

        self.empty = label(get_config().t("empty_search"), obj="Hint")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setVisible(False)
        lay.addWidget(self.empty)

        self.reload_btn = GhostButton(get_config().t("refresh"), icon_name="refresh")
        self.reload_btn.clicked.connect(self.load)
        self.reload_btn.setVisible(False)
        lay.addWidget(self.reload_btn, 0)

        self.load()

    def load(self) -> None:
        from .. import instances as instmod
        from ..workers import background

        self._loading = True
        self._clear()
        self.status.setVisible(True)
        self.reload_btn.setVisible(False)
        self.status.setText(get_config().t("versions_loading"))

        def work():
            return instmod.fetch_versions(force=True)

        self.worker = background(work, on_result=self._filled, on_error=self._failed)

    def _failed(self, e: str) -> None:
        self._loading = False
        cfg = get_config()
        if "minecraft_launcher_lib" in e or "No module named" in e:
            hint = cfg.t("versions_need_lib")
        else:
            hint = cfg.t("versions_error")
        self.status.setText(hint)
        self.status.setToolTip(e.splitlines()[0][:200] if e else "")
        self.reload_btn.setVisible(True)
        QTimer.singleShot(0, self.show_manual_hint)

    def _filled(self, versions) -> None:
        self.versions = versions or []
        self._loading = False
        self.status.setVisible(not self.versions)
        if not self.versions:
            self.status.setText(get_config().t("versions_error"))
            self.reload_btn.setVisible(True)
        self.render()

    def show_manual_hint(self) -> None:
        if self.versions or self._loading or not self.reload_btn.isVisible():
            return
        self.status.setText(get_config().t("versions_manual_hint"))

    def _clear(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def _on_search(self, text: str) -> None:
        self.query = text.strip().lower()
        self.render()

    def _set_filter(self, key: str) -> None:
        self.filter = key
        self.render()

    def visible_versions(self) -> List[Tuple[str, str, int]]:
        out = []
        for vid, vtype, _stamp in self.versions:
            if self.filter != "all" and vtype != self.filter:
                continue
            if self.query and self.query not in vid.lower():
                continue
            out.append((vid, vtype, _stamp))
        return out

    def render(self) -> None:
        from .. import instances as instmod

        self._clear()
        items = self.visible_versions()
        self.empty.setVisible(bool(self.versions) and not items)
        for vid, vtype, _stamp in items[:400]:
            row = self._row(vid, vtype, instmod)
            self.list_layout.addWidget(row)
            self.list_layout.setAlignment(row, Qt.AlignTop)
        self.list_layout.addStretch(1)

    def _row(self, vid: str, vtype: str, instmod) -> QWidget:
        cfg = get_config()
        installed = instmod.version_installed(vid)
        card = Card(clickable=True, selected=(vid == self.chosen))
        card.setFixedHeight(42)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 3, 10, 3)
        lay.setSpacing(9)
        lay.setAlignment(Qt.AlignVCenter)

        if installed:
            check = QLabel()
            check.setPixmap(icons.make_pixmap("check", theme.SUCCESS, 15))
            check.setFixedWidth(15)
            lay.addWidget(check, 0, Qt.AlignVCenter)
        else:
            lay.addSpacing(15)

        lay.addWidget(label(vid, size=13, bold=True), 0)
        if vtype != "release":
            lay.addWidget(Badge(cfg.t(f"type_{vtype}"), theme.WARNING), 0)
        if installed:
            lay.addWidget(Badge(cfg.t("installed"), theme.SUCCESS), 0)
        lay.addStretch(1)

        card.clicked.connect(lambda _=False, v=vid: self.choose(v))
        return card

    def choose(self, version_id: str) -> None:
        self.chosen = version_id
        self.search.setText(version_id)
        self.filter = "all"
        chip = self.chips.get("all")
        if chip is not None:
            chip.setChecked(True)
        self.render()
        self.on_choose(version_id)


class InstallDialog(QDialog):
    def __init__(self, loader: str = "vanilla", parent=None,
                 versions: Optional[List[str]] = None):
        super().__init__(parent)
        t = get_config().t
        self.loader = loader
        self.setWindowTitle(t(f"install_{loader}"))
        self.setModal(True)
        self.resize(620, 700 if loader != "vanilla" else 640)
        self.setMinimumWidth(560)
        self.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
        self.chosen_mc = ""
        self.chosen_loader = ""
        self.status = label("", size=12, color=theme.WARNING)
        self.status.setVisible(False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(13)

        head = QHBoxLayout()
        glyph = {"vanilla": "grass", "forge": "hammer", "fabric": "layers",
                 "quilt": "layers", "neoforge": "hammer", "optifine": "sun"}.get(loader, "cube")
        logo = QLabel()
        logo.setPixmap(icons.make_pixmap(glyph, theme.accent(get_config().get("accent")), 30))
        head.addWidget(logo)
        head.addSpacing(6)
        box = QVBoxLayout()
        box.setSpacing(2)
        box.addWidget(label(t(f"install_{loader}"), size=18, bold=True))
        box.addWidget(label(self._subtitle(loader), obj="Hint"))
        head.addLayout(box)
        head.addStretch(1)
        lay.addLayout(head)

        lay.addWidget(label(t("enter_version"), size=12, color=theme.TEXT_DIM, bold=True))
        last = get_config().get("last_version") or ""
        self.mc_edit = QLineEdit()
        self.mc_edit.setText(last)
        self.mc_edit.setPlaceholderText(t("enter_version_hint"))
        lay.addWidget(self.status)
        if loader in ("forge", "fabric", "quilt", "neoforge", "optifine"):
            self.java_hint = label("", obj="Hint")
        lay.addWidget(self.mc_edit)

        self.picker = VersionPicker(self)
        self.picker.on_choose = self._on_pick
        if last:
            self.picker.chosen = last
            self.picker.search.setText(last)
        lay.addWidget(self.picker, 1)
        lay.addStretch(0)

        if loader in ("forge", "fabric", "quilt", "neoforge", "optifine"):
            lay.addWidget(label(t("enter_loader_version"), size=12,
                                color=theme.TEXT_DIM, bold=True))
            self.loader_edit = QLineEdit()
            self.loader_edit.setText(get_config().get("last_loader_version") or "")
            self.loader_edit.setPlaceholderText(t("enter_loader_version_hint") +
                                                " — " + t("auto_latest"))
            lay.addWidget(self.loader_edit)
            lay.addWidget(self.java_hint)
            self._update_java_hint(self.mc_edit.text())

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = GhostButton(t("cancel"))
        self.ok_btn = PrimaryButton(t("install"))
        buttons.addWidget(cancel)
        buttons.addWidget(self.ok_btn)
        lay.addLayout(buttons)
        cancel.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self._accept)
        self.mc_edit.textChanged.connect(self._update_java_hint)
        self.mc_edit.setFocus()

    def _on_pick(self, version_id: str) -> None:
        self.mc_edit.setText(version_id)
        self._update_java_hint(version_id)

    @staticmethod
    def _subtitle(loader: str) -> str:
        return {
            "vanilla": "Официальная версия Mojang",
            "forge": "Моды через Minecraft Forge",
            "fabric": "Лёгкие моды, быстрая загрузка",
            "quilt": "Форк Fabric с поддержкой Forge-модов",
            "neoforge": "Современный Forge",
            "optifine": "Оптимизация FPS и анимации",
        }.get(loader, "")

    def _update_java_hint(self, text: str):
        from .. import java as javamod

        text = (text or "").strip()
        if not hasattr(self, "java_hint"):
            return
        if not text:
            self.java_hint.setText("")
            return
        need = javamod.required_java(text)
        self.java_hint.setText(get_config().t("java_need_for", text, f"Java {need}"))

    def _accept(self):
        mc = self.mc_edit.text().strip() or self.picker.chosen
        if not mc:
            self.mc_edit.setFocus()
            self.status.setText(get_config().t("enter_version_required"))
            self.status.setVisible(True)
            return
        self.status.setVisible(False)
        self.chosen_mc = mc
        self.chosen_loader = self.loader_edit.text().strip() if hasattr(self, "loader_edit") else ""
        self.accept()


class ModVersionsDialog(QDialog):
    installed = Signal(str, str)

    def __init__(self, project: modrinth.Project, loaders: Sequence[str] = (),
                 game_version: str = "", parent=None):
        super().__init__(parent)
        self.project = project
        self.loaders = list(loaders)
        self.game_version = game_version
        self._versions: List[modrinth.ModVersion] = []
        t = get_config().t
        self.setWindowTitle(project.title)
        self.setModal(True)
        self.resize(720, 560)
        self.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(12)
        if project.icon:
            head.addWidget(network_image(project.icon, 52))
        else:
            box_icon = QLabel()
            box_icon.setPixmap(icons.make_pixmap("package", theme.accent(
                get_config().get("accent")), 46))
            box_icon.setFixedSize(52, 52)
            head.addWidget(box_icon)
        info_box = QVBoxLayout()
        info_box.setSpacing(3)
        t1 = ElidedLabel(project.title, size=19, bold=True)
        info_box.addWidget(t1)
        if project.description:
            d = label(project.description, obj="Hint", wrap=True)
            d.setMaximumWidth(520)
            info_box.addWidget(d)
        meta = QHBoxLayout()
        meta.setSpacing(8)
        meta.addWidget(Badge(f"↓ {project.downloads_text()}", theme.TEXT_MUTED))
        if project.author:
            meta.addWidget(Badge(project.author, theme.TEXT_MUTED))
        info_box.addLayout(meta)
        head.addLayout(info_box, 1)
        open_btn = GhostButton(t("open_modrinth"), icon_name="external")
        open_btn.clicked.connect(lambda: __import__("webbrowser").open(project.url))
        head.addWidget(open_btn, 0)
        lay.addLayout(head)
        lay.addWidget(_divider())

        self.list_w = QScrollArea()
        self.list_w.setWidgetResizable(True)
        self.inner = QWidget()
        self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setContentsMargins(0, 0, 0, 0)
        self.inner_lay.setSpacing(8)
        self.list_w.setWidget(self.inner)
        lay.addWidget(self.list_w, 1)

        self.status = label(t("downloading"), obj="Hint")
        lay.addWidget(self.status)

        self._load()

    def _load(self):
        from ..workers import background

        def work():
            self._versions = modrinth.versions(self.project.id)
            return self._versions

        self.worker = background(work, on_result=self._fill, on_error=self._err)
        self.status.setText(get_config().t("downloading"))

    def _err(self, e: str):
        self.status.setText(f"{get_config().t('mods_error')}: {e}")

    def _fill(self, _res=None):
        t = get_config().t
        while self.inner_lay.count():
            item = self.inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        if not self._versions:
            self.status.setText(t("empty_search"))
            return
        for v in self._versions:
            self.inner_lay.addWidget(self._row(v))
        self.status.setText(t("search_results", len(self._versions)))

    def _row(self, v: modrinth.ModVersion) -> QWidget:
        t = get_config().t
        card = FlatCard()
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 10, 12, 10)
        lay.setSpacing(12)
        box = QVBoxLayout()
        box.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(ElidedLabel(v.version_number, size=14, bold=True))
        top.addWidget(Badge(v.version_type, theme.WARNING if v.version_type != "release"
                            else theme.SUCCESS))
        if set(v.loaders) & set(self.loaders):
            top.addWidget(Badge(t("ok"), theme.SUCCESS))
        top.addStretch(1)
        box.addLayout(top)
        box.addWidget(label(v.mc_text(), obj="Hint"))
        if v.dependencies:
            box.addWidget(label(f"{t('dependencies')}: {len(v.dependencies)}",
                                size=11, color=theme.TEXT_MUTED))
        lay.addLayout(box, 1)
        btn = PrimaryButton(t("install_mod"))
        btn.setMinimumWidth(120)
        btn.setIcon(icons.make_icon("download", "#ffffff", 15))
        btn.clicked.connect(lambda: self._install(v))
        lay.addWidget(btn, 0)
        return card

    def _install(self, v: modrinth.ModVersion):
        self.installed.emit(v.project_id, v.id)
        self.accept()


class ChooseInstanceDialog(QDialog):
    def __init__(self, instances, parent=None, title_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title_text or get_config().t("select_instance_for_mod"))
        self.setModal(True)
        self.setFixedWidth(460)
        self.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
        self.chosen = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 16)
        lay.setSpacing(10)
        lay.addWidget(label(self.windowTitle(), size=16, bold=True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(8)
        for inst in instances:
            card = Card()
            card.setObjectName("CardFlat")
            h = QHBoxLayout(card)
            h.setContentsMargins(14, 10, 14, 10)
            h.addWidget(QLabel(inst.label))
            h.addWidget(label(inst.base_mc, obj="Dim"))
            h.addStretch(1)
            btn = PrimaryButton(get_config().t("start"))
            btn.setFixedWidth(90)
            btn.clicked.connect(lambda i=inst: self._pick(i))
            h.addWidget(btn)
            il.addWidget(card)
        scroll.setWidget(inner)
        lay.addWidget(scroll)
        cancel = GhostButton(get_config().t("cancel"))
        cancel.clicked.connect(self.reject)
        lay.addWidget(cancel, 0)

    def _pick(self, inst):
        self.chosen = inst
        self.accept()


class UpdateDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        from ..updater import UpdateInfo

        self.info = info
        self.setWindowTitle(get_config().t("update_download"))
        self.setModal(True)
        self.setFixedWidth(520)
        self.setStyleSheet(theme.stylesheet(get_config().get("accent", "blue")))
        t = get_config().t
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(12)

        head = QHBoxLayout()
        head.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("upload", theme.accent(get_config().get("accent")), 30))
        head.addWidget(ico)
        box = QVBoxLayout()
        box.setSpacing(2)
        box.addWidget(label(t("update_to", info.latest.version), size=18, bold=True))
        box.addWidget(label(t("update_current", info.current), obj="Hint"))
        head.addLayout(box)
        head.addStretch(1)
        if info.size:
            from .. import utils as _utils

            head.addWidget(Badge(f"↓ {_utils.human_size(info.size)}", theme.TEXT_MUTED))
        lay.addLayout(head)

        if info.latest.body:
            notes = QPlainTextEdit(info.latest.body[:2000])
            notes.setReadOnly(True)
            notes.setFixedHeight(150)
            notes.setFont(theme.mono_font(11))
            lay.addWidget(notes)

        row = QHBoxLayout()
        later = GhostButton(t("update_skip"))
        dl = PrimaryButton(t("update_download"))
        row.addStretch(1)
        row.addWidget(later)
        row.addWidget(dl)
        lay.addLayout(row)
        later.clicked.connect(self.reject)
        dl.clicked.connect(self.accept)


def _divider() -> QFrame:
    from .widgets import divider

    return divider()
