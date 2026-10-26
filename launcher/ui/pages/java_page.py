from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout,
                               QWidget)

from ... import java as javamod
from ...config import get_config, suggested_ram_mb, total_ram_mb
from ... import workers
from ...workers import background
from .. import dialogs, icons, theme
from ..widgets import (Badge, Card, Chip, ElidedLabel, FlatCard, GhostButton, IconButton,
                       PrimaryButton, ProgressRow, ScrollArea, label, toast)


class JavaPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self.worker = None
        self._scan = None
        self._scan_error = False
        self._scan_generation = 0
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        head = QHBoxLayout()
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(label(self.cfg.t("java_title"), size=25, bold=True))
        self.subtitle = ElidedLabel("", size=13, color=theme.TEXT_DIM)
        box.addWidget(self.subtitle)
        head.addLayout(box, 1)
        self.btn_refresh = GhostButton(self.cfg.t("refresh"), icon_name="refresh")
        self.btn_refresh.clicked.connect(lambda _=False: self.refresh(force=True))
        head.addWidget(self.btn_refresh)
        self.btn_manual = GhostButton(self.cfg.t("java_browse"), icon_name="folder")
        self.btn_manual.clicked.connect(self._manual)
        head.addWidget(self.btn_manual)
        root.addLayout(head)

        self.download_card = FlatCard()
        dl = QHBoxLayout(self.download_card)
        dl.setContentsMargins(14, 11, 14, 11)
        dl.setSpacing(14)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("coffee", theme.accent(self.cfg.get("accent")), 30))
        dl.addWidget(ico)
        tbox = QVBoxLayout()
        tbox.setSpacing(3)
        self.dl_title = ElidedLabel("", size=14, bold=True)
        self.dl_hint = ElidedLabel("", size=12, color=theme.TEXT_DIM)
        tbox.addWidget(self.dl_title)
        tbox.addWidget(self.dl_hint)
        dl.addLayout(tbox, 1)
        self.dl_buttons = QHBoxLayout()
        self.dl_buttons.setSpacing(8)
        dl.addLayout(self.dl_buttons)
        root.addWidget(self.download_card)

        self.progress = ProgressRow()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.found_title = label(self.cfg.t("java_found"), obj="SectionTitle")
        root.addWidget(self.found_title)

        self.list_scroll = ScrollArea()
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 6, 0)
        self.list_layout.setSpacing(9)
        self.list_scroll.setWidget(self.list_host)
        root.addWidget(self.list_scroll, 1)

        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.setAlignment(Qt.AlignCenter)
        el.setSpacing(8)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("alert", theme.WARNING, 46))
        ico.setAlignment(Qt.AlignCenter)
        el.addWidget(ico)
        lab = label(self.cfg.t("java_none"), size=16, bold=True)
        lab.setAlignment(Qt.AlignCenter)
        el.addWidget(lab)
        self.empty_hint = ElidedLabel(self.cfg.t("java_none_hint"), size=12,
                                      color=theme.TEXT_MUTED)
        self.empty_hint.setAlignment(Qt.AlignCenter)
        el.addWidget(self.empty_hint)
        cta = QHBoxLayout()
        cta.addStretch(1)
        self.empty_btn = PrimaryButton("")
        self.empty_btn.clicked.connect(lambda: self._download(self._suggested_major()))
        cta.addWidget(self.empty_btn)
        cta.addStretch(1)
        el.addLayout(cta)
        self.empty.setVisible(False)
        root.addWidget(self.empty, 1)

    def refresh(self, force: bool = False):
        self.cfg = get_config()
        cached = javamod.cached_javas()
        age = javamod.java_cache_age()
        needs_scan = force or age is None or age > javamod.JAVA_CACHE_TTL
        self._paint_javas(cached, searching=needs_scan)
        if not needs_scan:
            return
        if (workers.is_alive(self._scan)
                or workers.is_alive(getattr(self.w, "_java_scan", None))):
            return

        self._scan_error = False
        self._scan_generation = javamod.java_cache_generation()

        def scan(ctx):
            return javamod.detect_javas(
                max_age=0 if force else javamod.JAVA_CACHE_TTL,
                cancelled=ctx.is_cancelled)

        self._scan = workers.background(
            scan,
            on_result=self._scan_done, on_error=self._scan_failed,
            on_finish=self._scan_finished, parent=self.w)

    def _scan_done(self, javas) -> None:
        try:
            if not self.isVisible() and not javas:
                return
            self._paint_javas(javas, searching=False)
        except RuntimeError:
            return

    def _scan_failed(self, _e) -> None:
        self._scan_error = True

    def _scan_finished(self) -> None:
        self._scan = None
        try:
            if (not getattr(self.w, "_closing", False)
                    and not self._scan_error and self.isVisible()
                    and javamod.java_cache_state() is None
                    and javamod.java_cache_generation() != self._scan_generation):
                QTimer.singleShot(0, lambda: self.refresh(force=True))
        except RuntimeError:
            return

    def _paint_javas(self, javas, searching: bool = False) -> None:
        javas = list(javas)
        suggested = self._suggested_major()
        found = self.cfg.t("java_found_short")
        self.subtitle.setText(f"{len(javas)} · " + found
                              + (" · " + self.cfg.t("java_scanning") if searching
                                 else ""))
        self.empty_btn.setText(f"{self.cfg.t('java_download')} Java {suggested}")
        self.empty_btn.setIcon(icons.make_icon("download", "#ffffff", 15))
        self.empty_hint.setText(self.cfg.t("java_none_hint"))
        self._render_download_block()
        self._render_list(javas)

    def _suggested_major(self) -> int:
        inst, needed = self._needs_for_instances()
        return needed if needed in (8, 17, 21, 25) else javamod.preferred_java()

    def _needs_for_instances(self) -> tuple:
        sel = self.w.selected_instance()
        if sel is None:
            sel = next(iter(instmod_repo().all()), None)
        if sel is None:
            return None, javamod.preferred_java()
        return sel, javamod.required_java(sel.base_mc)

    def _render_download_block(self):
        while self.dl_buttons.count():
            item = self.dl_buttons.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        inst, needed = self._needs_for_instances()
        cfg = get_config()
        if inst is not None:
            self.dl_title.setText(cfg.t("java_need_for", inst.base_mc, f"Java {needed}"))
            self.dl_title.setToolTip(f"{inst.id} · {inst.mc_version}")
        else:
            self.dl_title.setText(cfg.t("java_title"))
            self.dl_title.setToolTip("")
        self.dl_hint.setText(cfg.t("java_compat"))

        have = {j.major for j in javamod.cached_javas()}
        order = [needed, 25, 21] if needed == 25 else ([needed, 21, 25] if needed == 21
                                                      else [21, 25])
        for major in dict.fromkeys(order):
            if major in have:
                continue
            btn = PrimaryButton(f"Java {major}")
            btn.setFixedWidth(112)
            btn.setIcon(icons.make_icon("download", "#ffffff", 15))
            btn.setToolTip(cfg.t("java_download_tooltip", major))
            btn.clicked.connect(lambda _=False, m=major: self._download(m))
            self.dl_buttons.addWidget(btn)

        for major in sorted(have):
            badge = Badge(f"Java {major} ✓", theme.SUCCESS)
            self.dl_buttons.addWidget(badge)

        for major in (17, 8):
            if major in have:
                continue
            btn = GhostButton(f"Java {major}")
            btn.setFixedWidth(92)
            btn.setToolTip(cfg.t("java_download_tooltip", major))
            btn.clicked.connect(lambda _=False, m=major: self._download(m))
            self.dl_buttons.addWidget(btn)

    def _render_list(self, javas):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.list_scroll.setVisible(bool(javas))
        self.found_title.setVisible(bool(javas))
        self.empty.setVisible(not javas)
        for j in javas:
            self.list_layout.addWidget(self._row(j))

    def _row(self, j: javamod.JavaInfo) -> QWidget:
        card = Card(clickable=False)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(13, 9, 11, 10)
        lay.setSpacing(12)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap("coffee",
                                         theme.SUCCESS if j.bundled else theme.TEXT_MUTED, 24))
        lay.addWidget(ico)
        box = QVBoxLayout()
        box.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(label(f"Java {j.major}", size=14, bold=True))
        top.addWidget(Badge(j.version or "?", theme.TEXT_MUTED))
        if j.bundled:
            top.addWidget(Badge(self.cfg.t("java_bundled"), theme.SUCCESS))
        if j.custom:
            top.addWidget(Badge(self.cfg.t("java_selected"), theme.INFO))
        if not j.bundled and not j.custom:
            top.addWidget(Badge(self.cfg.t("java_system"), theme.TEXT_MUTED))
        top.addStretch(1)
        box.addLayout(top)
        path_lab = ElidedLabel(str(j.path), size=12, color=theme.TEXT_MUTED)
        path_lab.setToolTip(str(j.path))
        box.addWidget(path_lab)
        lay.addLayout(box, 1)

        inst, _needed = self._needs_for_instances()
        if inst is not None:
            state = javamod.java_ok(inst.base_mc, j)
            colors = {"ok": theme.SUCCESS, "low": theme.WARNING, "high": theme.INFO}
            texts = {"ok": self.cfg.t("java_ok"), "low": self.cfg.t("java_low"),
                     "high": self.cfg.t("java_high")}
            col = QWidget()
            cl = QVBoxLayout(col)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(2)
            cl.addWidget(Badge(texts[state], colors[state]))
            lay.addWidget(col, 0)

        btns = QHBoxLayout()
        btns.setSpacing(6)
        if j.bundled:
            rm = IconButton("trash", theme.DANGER, 32, tip=self.cfg.t("java_delete"))
            rm.clicked.connect(lambda: self._delete(j))
            btns.addWidget(rm)
        else:
            use = GhostButton(self.cfg.t("java_use"))
            use.clicked.connect(lambda: self._use(j))
            btns.addWidget(use)
        lay.addLayout(btns)
        return card

    def _download(self, major: int):
        self.progress.setVisible(True)
        self.progress.set(self.cfg.t("java_progress", major), -1)

        def work(ctx):
            info = javamod.download_java(major, ctx.progress, ctx.status)
            return info

        self.worker = background(
            work,
            on_result=lambda info: self._download_done(info),
            on_error=self._download_error, parent=self)

    def _download_done(self, info: javamod.JavaInfo):
        self.progress.setVisible(False)
        toast(self, self.cfg.t("java_ready", info.major), "success")
        self.refresh()
        self.w.refresh_all()

    def _download_error(self, e: str):
        self.progress.setVisible(False)
        dialogs.error(self, e, self.cfg.t("java_title"))

    def _delete(self, j: javamod.JavaInfo):
        if not dialogs.confirm(self, f"{self.cfg.t('java_delete')} Java {j.major}?",
                               self.cfg.t("java_delete")):
            return
        javamod.delete_bundled(j)
        self.refresh()

    def _use(self, j: javamod.JavaInfo):
        self.cfg.set("custom_java", str(j.path))
        javamod.invalidate_java_cache()
        self.cfg.save()
        toast(self, self.cfg.t("java_path") + ": " + j.version, "success")
        self.refresh()
        self.w.refresh_all()

    def _manual(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.cfg.t("java_manual"), "", "Java (java.exe java);;Все файлы (*)")
        if not path:
            return
        info = javamod.probe_java(Path(path))
        if not info:
            dialogs.warn(self, self.cfg.t("java_invalid"), self.cfg.t("java_test"))
            return
        self.cfg.set("custom_java", str(info.path))
        javamod.invalidate_java_cache()
        self.cfg.save()
        toast(self, f"{self.cfg.t('java_ok')}: Java {info.major}", "success")
        self.refresh()
        self.w.refresh_all()


def instmod_repo():
    from ... import instances

    return instances.repo()
