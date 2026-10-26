from __future__ import annotations

import time
from typing import Dict, List, Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMenu, QMessageBox, QStackedWidget,
                               QVBoxLayout, QWidget)

from .. import accounts as accmod
from .. import appicon
from .. import instances as instmod
from .. import java as javamod
from .. import paths, utils
from ..config import get_config
from ..workers import background, is_alive
from . import dialogs, icons, shortcuts, theme
from .pages import (HomePage, InstancesPage, JavaPage, LogsPage, ModsPage, SettingsPage)
from .widgets import (Avatar, Badge, Card, ElidedLabel, FlatCard, GhostButton,
                      IconButton, InstanceIcon, PrimaryButton, divider, label,
                      round_pixmap, spacer, toast)

NAV = [
    ("home", "home", "nav_home"),
    ("instances", "cube", "nav_instances"),
    ("mods", "package", "nav_mods"),
    ("java", "coffee", "nav_java"),
    ("logs", "terminal", "nav_logs"),
    ("settings", "gear", "nav_settings"),
]


class NavButton(QFrame):
    def __init__(self, key: str, glyph: str, text: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("NavItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setStyleSheet(
            f"#NavItem{{background:transparent;border-radius:10px;}}"
            f"#NavItem:hover{{background:{theme.CARD_HOVER};}}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 0, 11, 0)
        lay.setSpacing(11)
        self.icon = QLabel()
        self.icon.setPixmap(icons.make_pixmap(glyph, theme.TEXT_DIM, 18))
        self.icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.icon)
        self.text = label(text, size=13, bold=False, color=theme.TEXT_DIM)
        self.text.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(self.text, 1)
        self._text = text
        self.active = False

    def set_active(self, active: bool) -> None:
        self.active = active
        color = theme.accent(get_config().get("accent")) if active else theme.TEXT_DIM
        self.icon.setPixmap(icons.make_pixmap(NAV_GLYPHS.get(self.key, "cube"), color, 18))
        self.text.setText(self._text)
        self.text.setStyleSheet(
            f"color:{color};background:transparent;"
            f"font-weight:{'700' if active else '400'};font-size:13px;")


NAV_GLYPHS = {k: g for k, g, _ in NAV}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = get_config()
        self.pages: Dict[str, QWidget] = {}
        self.nav_buttons: Dict[str, NavButton] = {}
        self.current_page = "home"
        self.selected_id: Optional[str] = None
        self.running_instance: Optional[instmod.Instance] = None
        self.worker = None
        self.update_info = None
        self._pending_instance = None
        self._java_scan = None
        self._java_scan_generation = -1
        self._closing = False

        insts = instmod.repo().all()
        if insts:
            self.selected_id = insts[0].id

        self.setWindowTitle(self.cfg.t("app_title"))
        self.resize(self.cfg.get("window_width") or 1180,
                    self.cfg.get("window_height") or 760)
        self.setMinimumSize(QSize(980, 640))
        self.setWindowIcon(appicon.app_icon(theme.accent(self.cfg.get("accent"))))

        self._build()
        self.apply_theme()
        self.switch_page("home")
        self._build_shortcuts()

        QTimer.singleShot(0, self._ensure_java_scan)
        QTimer.singleShot(400, self._post_start)
        QTimer.singleShot(1500, self._ticker)

    def _build(self):
        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(232)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        self.brand_logo = QLabel()
        self.brand_logo.setPixmap(appicon.app_pixmap(32, theme.accent(self.cfg.get("accent"))))
        brand.addWidget(self.brand_logo)
        self.brand_text = label("Fimple Launcher", size=17, bold=True)
        self.brand_text.setStyleSheet(
            f"color:{theme.TEXT};background:transparent;font-weight:700;font-size:17px;")
        brand.addWidget(self.brand_text)
        brand.addStretch(1)
        sl.addLayout(brand)
        sl.addSpacing(14)

        for key, glyph, text_key in NAV:
            btn = NavButton(key, glyph, self.cfg.t(text_key))
            btn.mouseReleaseEvent = self._nav_event(btn)
            self.nav_buttons[key] = btn
            sl.addWidget(btn)

        sl.addStretch(1)
        sl.addWidget(divider())

        self.account_btn = QFrame()
        self.account_btn.setObjectName("AccountCard")
        self.account_btn.setStyleSheet(
            f"#AccountCard{{background:{theme.CARD};"
            f"border:1px solid {theme.BORDER};border-radius:12px;}}")
        al = QHBoxLayout(self.account_btn)
        al.setContentsMargins(10, 9, 10, 9)
        al.setSpacing(9)
        self.account_avatar = Avatar(30)
        al.addWidget(self.account_avatar)
        abox = QVBoxLayout()
        abox.setSpacing(1)
        self.account_name = ElidedLabel("", size=12, bold=True)
        self.account_type = ElidedLabel("", size=10, color=theme.TEXT_MUTED)
        abox.addWidget(self.account_name)
        abox.addWidget(self.account_type)
        al.addLayout(abox, 1)
        self.account_settings_btn = IconButton("sliders", theme.TEXT_MUTED, 26,
                                               tip=self.cfg.t("accounts"))
        self.account_settings_btn.clicked.connect(self.open_account_settings)
        al.addWidget(self.account_settings_btn)
        sl.addWidget(self.account_btn)

        self.version_label = label(f"v{paths.app_version()}", size=10,
                                   color=theme.TEXT_MUTED)
        self.version_label.setAlignment(Qt.AlignCenter)
        sl.addWidget(self.version_label)
        root.addWidget(side)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.pages["home"] = HomePage(self)
        self.pages["instances"] = InstancesPage(self)
        self.pages["mods"] = ModsPage(self)
        self.pages["java"] = JavaPage(self)
        self.pages["logs"] = LogsPage(self)
        self.pages["settings"] = SettingsPage(self)
        for key in NAV:
            k = key[0]
            self.stack.addWidget(self.pages[k])

        self.pages["home"].request_page.connect(self.switch_page)

    def _nav_event(self, btn: NavButton):
        def handler(event):
            self.switch_page(btn.key)
            if btn.key != "home":
                event.accept()
        return handler

    def open_account_settings(self):
        self.switch_page("settings")
        page = self.pages.get("settings")
        if hasattr(page, "show_accounts"):
            page.show_accounts()

    @property
    def workers(self):
        from .. import workers as workers_mod

        return workers_mod

    def _build_shortcuts(self):
        for i, key in enumerate(shortcuts.NAV_PAGES, start=1):
            sc = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            sc.activated.connect(lambda k=key: self.switch_page(k))
        actions = {
            "hotkey_launch": self.launch_selected,
            "hotkey_refresh": self.refresh_all,
            "hotkey_quit": self.close,
        }
        for keys, label in shortcuts.ACTION_KEYS:
            slot = actions.get(label)
            if slot is not None:
                QShortcut(QKeySequence(keys), self).activated.connect(slot)
        QShortcut(QKeySequence("F5"), self).activated.connect(self.refresh_all)

    def apply_theme(self):
        accent = self.cfg.get("accent")
        self.setStyleSheet(theme.stylesheet(accent))
        self.brand_logo.setPixmap(appicon.app_pixmap(32, theme.accent(accent)))
        for key, btn in self.nav_buttons.items():
            btn.set_active(btn.key == self.current_page)
        self.version_label.setText(f"v{paths.app_version()}")
        self.setWindowIcon(appicon.app_icon(theme.accent(accent)))

    def retranslate(self):
        self.cfg = get_config()
        self.setWindowTitle(self.cfg.t("app_title"))
        for key, btn in self.nav_buttons.items():
            text_key = next(t for k, _g, t in NAV if k == key)
            btn._text = self.cfg.t(text_key)
            btn.text.setText(btn._text)
            btn.set_active(key == self.current_page)
        old = self.stack
        new_stack = QStackedWidget()
        for key, _g, _t in NAV:
            self.pages[key].deleteLater()
            self.pages[key] = self._make_page(key)
            new_stack.addWidget(self.pages[key])
        self.stack = new_stack
        root_layout = old.parentWidget().layout()
        idx = root_layout.indexOf(old)
        if idx < 0:
            idx = root_layout.count()
        root_layout.removeWidget(old)
        root_layout.insertWidget(idx, new_stack)
        old.hide()
        old.deleteLater()
        self.pages["home"].request_page.connect(self.switch_page)
        self.switch_page(self.current_page, force=True)
        self.refresh_all()
        self.apply_theme()

    def _make_page(self, key: str) -> QWidget:
        if key == "home":
            return HomePage(self)
        if key == "instances":
            return InstancesPage(self)
        if key == "mods":
            inst = self.selected_instance()
            return ModsPage(self, inst)
        if key == "java":
            return JavaPage(self)
        if key == "logs":
            return LogsPage(self)
        return SettingsPage(self)

    def switch_page(self, key: str, force: bool = False):
        if key not in self.pages:
            return
        if self.current_page == key and not force:
            return
        self.current_page = key
        idx = [k[0] for k in NAV].index(key)
        self.stack.setCurrentIndex(idx)
        for k, btn in self.nav_buttons.items():
            btn.set_active(k == key)
        page = self.pages[key]
        if hasattr(page, "refresh"):
            page.refresh()
        if key == "mods":
            page.set_instance(self.selected_instance())

    def current_id(self) -> Optional[str]:
        return self.selected_id

    def selected_instance(self) -> Optional[instmod.Instance]:
        if not self.selected_id:
            return None
        return instmod.repo().get(self.selected_id)

    def select_instance(self, instance_id: Optional[str]):
        self.selected_id = instance_id
        self.refresh_all()

    def refresh_all(self):
        instmod.repo().invalidate()
        acc = accmod.store()
        cur = acc.current()
        if cur is None:
            name = self.cfg.get("nickname") or "Player"
            self.account_name.setText(name)
            self.account_type.setText(self.cfg.t("account_offline"))
            self.account_avatar.set_name(name)
            self.account_avatar.set_image(None)
        else:
            self.account_name.setText(cur.username)
            self.account_type.setText("Ely.by" if cur.type == "ely"
                                      else self.cfg.t("account_offline"))
            self.account_avatar.set_name(cur.username)
            path = acc.fetch_avatar(cur) or acc.avatar_path(cur)
            self.account_avatar.set_image(path)
        for key, page in self.pages.items():
            if key in ("home", "instances") and hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception as e:
                    utils.log(f"refresh({key}): {e}", "WARN")

    def pick_install_loader(self):
        m = QMenu(self)
        for loader, glyph in instmod.LOADER_ORDER:
            name = self.cfg.t(f"install_{loader}")
            if not instmod.loader_enabled(loader):
                act = m.addAction(icons.make_icon(glyph, theme.TEXT_MUTED, 16),
                                  f"{name} · {self.cfg.t('coming_soon')}")
                act.setEnabled(False)
                act.setToolTip(self.cfg.t("loader_soon_hint"))
                continue
            m.addAction(icons.make_icon(glyph,
                                        instmod.LOADER_COLORS.get(loader, theme.TEXT_DIM), 16),
                        name, lambda _=False, ld=loader: self.start_install(ld))
        m.exec(self.cursor().pos())

    def start_install(self, loader: str):
        if not instmod.loader_enabled(loader):
            dialogs.info(self,
                         f"{self.cfg.t(f'install_{loader}')}: "
                         f"{self.cfg.t('loader_soon_hint')}",
                         self.cfg.t("install"))
            return
        dlg = dialogs.InstallDialog(loader, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        mc, lv = dlg.chosen_mc, dlg.chosen_loader
        if not mc:
            return
        if instmod.version_installed(mc):
            self.cfg.set("last_version", mc)
            self.cfg.save()
        self._run_install(loader, mc, lv)

    def _run_install(self, loader: str, mc: str, loader_version: str):
        installer, _arg = instmod.INSTALLERS.get(loader, (None, ""))
        if installer is None:
            self.pages["home"].hide_progress()
            dialogs.error(self,
                          f"{self.cfg.t(f'install_{loader}')}: "
                          f"{self.cfg.t('loader_soon_hint')}",
                          self.cfg.t("error"))
            return
        home = self.pages["home"]
        if self.current_page != "home":
            self.switch_page("home", force=True)
        home.show_progress(f"{self.cfg.t('installing_short')} {self.cfg.t('install_' + loader)}…")
        self.cfg.set("last_version", mc)
        self.cfg.set("last_loader_version", loader_version)
        self.cfg.save()

        def work(ctx):
            return installer(mc, loader_version, ctx.progress, ctx.status, ctx.log)

        self.worker = background(
            work, on_result=lambda version_id: self._install_done(loader, mc, version_id),
            on_error=self._install_error, parent=self)

    def _install_done(self, loader: str, mc: str, version_id: str):
        cfg = get_config()
        base = instmod.build_instance_id(mc, loader,
                                         version_id if loader in ("forge", "neoforge",
                                                                  "optifine") else "")
        inst_id = base
        n = 1
        while instmod.repo().get(inst_id) is not None:
            inst_id = f"{base}-{n}"
            n += 1
        inst = instmod.repo().create(inst_id, version_id, loader)
        self.selected_id = inst.id
        home = self.pages["home"]
        home.progress.set_done(cfg.t("installed_ok", cfg.t(f"install_{loader}")))
        QTimer.singleShot(1800, home.hide_progress)
        self.refresh_all()
        self.switch_page("home", force=True)
        toast(self, f"{cfg.t('installed_ok', inst.id)}", "success")
        if cfg.get("auto_play"):
            QTimer.singleShot(700, lambda: self.launch_instance(inst))

    def _install_error(self, e: str):
        home = self.pages["home"]
        home.progress.setVisible(False)
        home.show_progress("")
        if isinstance(e, instmod.JavaMissing):
            major = e.major or 21
            if dialogs.confirm(self, str(e), self.cfg.t("java_title"),
                                yes_text=f"{self.cfg.t('java_download')} Java {major}",
                                no_text=self.cfg.t("no")):
                self.switch_page("java")
                QTimer.singleShot(300, lambda: self.pages["java"]._download(major))
            self.refresh_all()
            return
        dialogs.error(self, str(e), self.cfg.t("error"))
        self.refresh_all()

    def cancel_current(self):
        if self.worker:
            self.worker.requestInterruption()

    def launch_selected(self):
        inst = self.selected_instance()
        if inst is None:
            self.switch_page("instances")
            return
        self.launch_instance(inst)

    def launch_instance(self, inst: instmod.Instance):
        cfg = get_config()
        need = instmod.needs_java(inst)
        if need:
            answer = dialogs.confirm(
                self,
                f"{cfg.t('java_need_for', inst.base_mc, f'Java {need}')}\n"
                f"{cfg.t('java_download')}?",
                cfg.t("java_title"),
                yes_text=f"{cfg.t('java_download')} Java {need}",
                no_text=cfg.t("no"))
            if answer:
                self.switch_page("java")
                QTimer.singleShot(300, lambda: self.pages["java"]._download(need))
                return
        self.selected_id = inst.id
        try:
            res = instmod.launch(inst, on_log=self._on_game_log,
                                 on_exit=self._on_game_exit)
        except instmod.VersionMissing:
            if dialogs.confirm(self, cfg.t("version_missing", inst.mc_version),
                                cfg.t("warning"),
                                yes_text=cfg.t("reinstall"),
                                no_text=cfg.t("cancel")):
                self.start_install(inst.loader)
            return
        except Exception as e:
            dialogs.error(self, str(e), cfg.t("error"))
            return
        self.running_instance = inst
        cfg.save()
        if cfg.get("minimize_on_launch"):
            self.showMinimized()
        self.refresh_all()
        self.switch_page("home", force=True)
        toast(self, f"{cfg.t('launching')}… {inst.id}", "success")

    def _on_game_log(self, line: str):
        if hasattr(self, "pages"):
            page = self.pages.get("logs")
            if page and self.current_page == "logs":
                page.append_game(line)
            else:
                utils.log(f"[MC] {line}", "INFO")

    def _on_game_exit(self, seconds: float):
        self.running_instance = None
        if hasattr(self, "pages"):
            page = self.pages.get("logs")
            if page:
                page.append_game(f"— {self.cfg.t('done')} "
                                 f"({utils.format_playtime(seconds)}) —")
        if self.current_page in ("home", "instances"):
            self.refresh_all()

    def open_instance_mods(self, inst: instmod.Instance):
        self.selected_id = inst.id
        page = self.pages.get("mods")
        if page is not None and isinstance(page, ModsPage):
            page.set_instance(inst)
        self.switch_page("mods", force=True)

    def install_mod_to_instance(self, inst: instmod.Instance, project_id: str,
                                version_id: str = ""):
        from .. import modrinth
        home = self.pages["home"]
        home.show_progress(self.cfg.t("mods_searching"))

        def work(ctx):
            versions = modrinth.versions(project_id)
            target = None
            for v in versions:
                if v.id == version_id:
                    target = v
                    break
            if target is None:
                loaders = [inst.loader] if inst.is_fabric_like else ["fabric", "forge"]
                target = modrinth.best_version(project_id, loaders, inst.base_mc)
            if target is None:
                raise RuntimeError("Версия мода не найдена")
            loaders = [inst.loader] if inst.is_fabric_like else ["fabric", "forge"]
            return modrinth.install_mod(inst.path, target, ctx.progress, True,
                                        loaders, inst.base_mc)

        self.worker = background(
            work,
            on_result=lambda files: self._mod_done(files),
            on_error=self._install_error, parent=self)

    def _mod_done(self, files):
        home = self.pages["home"]
        home.progress.set_done(f"{self.cfg.t('mod_installed', files[0].name[:30] if files else '')}")
        QTimer.singleShot(2000, home.hide_progress)
        self.refresh_all()
        page = self.pages.get("mods")
        if page is not None and hasattr(page, "render_installed"):
            page.render_installed()
        toast(self, self.cfg.t("mod_installed", str(len(files)) + " mods"), "success")

    def _ensure_java_scan(self):
        if self._closing:
            return
        if javamod.java_cache_state() is not None:
            return
        if is_alive(self._java_scan):
            return
        java_page = self.pages.get("java")
        if java_page is not None and is_alive(getattr(java_page, "_scan", None)):
            return

        self._java_scan_generation = javamod.java_cache_generation()

        def work(ctx):
            return javamod.detect_javas(max_age=0, cancelled=ctx.is_cancelled)

        self._java_scan = background(
            work, on_result=self._java_scanned,
            on_error=lambda e: utils.log(f"Поиск Java: {e}", "WARN"),
            on_finish=self._java_scan_finished, parent=self)

    def _java_scanned(self, _javas):
        if self.current_page not in ("home", "instances", "java"):
            return
        page = self.pages.get(self.current_page)
        if page is not None and hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception as e:
                utils.log(f"refresh после поиска Java: {e}", "WARN")

    def _java_scan_finished(self):
        self._java_scan = None
        if self._closing:
            return
        if (javamod.java_cache_state() is None
                and javamod.java_cache_generation() != self._java_scan_generation):
            QTimer.singleShot(0, self._ensure_java_scan)

    def _post_start(self):
        if self.cfg.get("check_updates"):
            self.check_updates(silent=True)

    def check_updates(self, silent: bool = False):
        cfg = get_config()

        def work():
            from .. import updater

            return updater.check_update()

        self.update_worker = background(
            work, on_result=self._update_result, on_error=self._update_error, parent=self)
        if not silent:
            toast(self, cfg.t("update_checking"), "info", 1600)

    def _update_result(self, info):
        cfg = get_config()
        self.update_info = info
        cfg.set("last_update_check", time.time())
        cfg.save()
        if info.available:
            toast(self, cfg.t("update_available", info.latest.version), "warning", 6000)
        elif info.error == "repo_private":
            utils.log("Репозиторий обновлений недоступен (закрыт или переименован)",
                      "INFO")
        elif info.error:
            toast(self, cfg.t("update_failed"), "error", 3000)
        else:
            toast(self, cfg.t("update_none"), "success", 2200)

    def _update_error(self, _e: str):
        self.update_info = None

    def _ticker(self):
        page = self.pages.get(self.current_page)
        if page is not None and self.current_page in ("home", "instances"):
            if hasattr(page, "refresh"):
                try:
                    page.refresh()
                except Exception:
                    pass

    def resizeEvent(self, e):
        super().resizeEvent(e)
        page = self.pages.get("instances")
        if page is not None and hasattr(page, "render"):
            page.render()

    def closeEvent(self, e: QCloseEvent):
        from ..workers import shutdown

        self._closing = True
        try:
            self.cfg.set("window_width", self.width())
            self.cfg.set("window_height", self.height())
            self.cfg.save()
        except Exception:
            pass
        shutdown()
        if self.running_instance is not None:
            r = dialogs.confirm(
                self, "Игра ещё запущена. Закрыть лаунчер?",
                self.cfg.t("warning"), yes_text=self.cfg.t("yes"),
                no_text=self.cfg.t("no"))
            if not r:
                self._closing = False
                e.ignore()
                return
        super().closeEvent(e)

    def restart(self):
        from .. import updater

        updater.relaunch()

    def show_message(self, text: str, kind: str = "info"):
        toast(self, text, kind)


def run_main_window() -> int:
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setApplicationName("Fimple Launcher")
    app.setApplicationDisplayName("Fimple Launcher")
    win = MainWindow()
    win.show()
    return app.exec()
