from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QProgressBar, QVBoxLayout, QWidget)

from .config import get_config, suggested_ram_mb, total_ram_mb
from .ui import icons, theme
from .ui.widgets import (GhostButton, IconButton, PrimaryButton, label, spacer)


class Logo(QWidget):
    def __init__(self, size: int = 92, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._t = 0.0

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        s = self.width()
        p.translate(s / 2, s / 2)
        p.rotate(self._t * 60)
        c = QColor(theme.accent(get_config().get("accent")))
        pen = QPen(c.lighter(140))
        pen.setWidthF(s * 0.08)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF_(-s * .28, -s * .28, s * .56, s * .56), s * .16, s * .16)
        p.drawRoundedRect(QRectF_(-s * .12, -s * .12, s * .24, s * .24), s * .08, s * .08)
        p.end()

    def tick(self, dt: float = 0.016):
        self._t += dt
        self.update()


def QRectF_(x, y, w, h):
    from PySide6.QtCore import QRectF

    return QRectF(x, y, w, h)


class Splash(QMainWindow):
    finished = Signal()
    refused = Signal()

    def __init__(self, check_updates: bool = True, check_java: bool = True):
        super().__init__()
        self.cfg = get_config()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SplashScreen)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(560, 400)
        self._drag_pos: Optional[QPoint] = None
        self.update_info = None
        self.worker = None
        self._done = False
        self._java_checked = False
        self._update_done_flag = False
        self._java_major = 21
        self._stage = "done"
        self._check_updates = check_updates
        self._check_java = check_java

        self._build()
        self._ticker = QTimer(self)
        spinner = getattr(self, "logo", None)
        if spinner is not None:
            self._ticker.timeout.connect(spinner.tick)
        self._ticker.start(16)
        QTimer.singleShot(350, self.start_flow)

    def _build(self):
        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(34, 30, 34, 26)
        outer.setSpacing(0)

        head = QHBoxLayout()
        head.setSpacing(14)
        from . import appicon

        self.app_icon = appicon.app_icon(theme.accent(self.cfg.get("accent")))
        if self.app_icon.isNull():
            self.logo = Logo(60)
            head.addWidget(self.logo)
        else:
            logo = QLabel()
            logo.setPixmap(appicon.app_pixmap(60, theme.accent(self.cfg.get("accent"))))
            head.addWidget(logo)
        box = QVBoxLayout()
        box.setSpacing(1)
        t = label("Fimple Launcher", size=21, bold=True)
        t.setStyleSheet(f"color:{theme.TEXT};background:transparent;"
                        "font-weight:700;font-size:21px;")
        box.addWidget(t)
        box.addWidget(label("Minecraft", size=12, color=theme.TEXT_MUTED))
        head.addLayout(box)
        head.addStretch(1)
        close = IconButton("close", theme.TEXT_MUTED, 30)
        close.clicked.connect(self.reject_flow)
        head.addWidget(close)
        outer.addLayout(head)
        outer.addSpacing(22)

        self.status = label("", size=13, bold=True)
        self.substatus = label("", obj="Hint", wrap=True)
        outer.addWidget(self.status)
        outer.addWidget(self.substatus)
        outer.addSpacing(14)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        outer.addWidget(self.bar)

        self.detail = label("", obj="Mono", wrap=True)
        self.detail.setVisible(False)
        outer.addWidget(self.detail)
        outer.addSpacing(10)

        self.log_line = label("", size=11, color=theme.TEXT_MUTED)
        outer.addWidget(self.log_line)

        outer.addStretch(1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(9)
        self.btn_skip = GhostButton("Позже")
        self.btn_skip.clicked.connect(self.finish)
        self.btn_action = PrimaryButton("")
        self.btn_action.clicked.connect(self._on_action)
        self.btn_cancel = GhostButton("Выйти")
        self.btn_cancel.clicked.connect(self.reject_flow)
        self.actions.addWidget(self.btn_skip)
        self.actions.addStretch(1)
        self.actions.addWidget(self.btn_cancel)
        self.actions.addWidget(self.btn_action)
        outer.addLayout(self.actions)

        self.setStyleSheet(theme.stylesheet(self.cfg.get("accent")) +
                           f"#Root{{background:{theme.BG};"
                           f"border-radius:{theme.RADIUS_CARD}px;}}")

    def _log(self, text: str) -> None:
        self.log_line.setText(text)

    def set_state(self, status: str, sub: str = "", percent: int = -1,
                  log: str = "") -> None:
        self.status.setText(status)
        if sub:
            self.substatus.setText(sub)
        if percent >= 0:
            self.bar.setRange(0, 100)
            self.bar.setValue(percent)
        else:
            self.bar.setRange(0, 0)
        if log:
            self._log(log)

    def set_detail(self, text: str) -> None:
        self.detail.setText(text)
        self.detail.setVisible(bool(text))

    def set_buttons(self, action: str = "", skip: str = "", show: bool = True) -> None:
        self.btn_action.setText(action)
        self.btn_action.setVisible(bool(action))
        self.btn_skip.setText(skip)
        self.btn_skip.setVisible(bool(skip))
        self.btn_cancel.setVisible(show)

    def start_flow(self) -> None:
        self._stage = "done"
        self._done = False
        self._update_done_flag = False
        self.set_buttons()
        QTimer.singleShot(0, self._run_update_stage)

    def _run_update_stage(self) -> None:
        if self._check_updates:
            self.check_update()
        else:
            self.after_update()

    def check_update(self) -> None:
        from . import updater
        from .workers import background

        self.set_state("Проверка обновлений…", updater.REPO_URL)
        self._log(f"GET {updater.RELEASES_API}/latest")

        def work(ctx):
            return updater.check_update()

        self.worker = background(work, on_result=self._update_ready,
                                 on_error=lambda e: self.after_update(), parent=self)

    def _update_ready(self, info) -> None:
        self.update_info = info
        if info.error or not info.latest:
            self._log(f"Проверка обновлений недоступна: {info.error or 'нет релизов'}")
            self.after_update()
            return
        if not info.available:
            self._log(f"Установлена последняя версия ({info.current})")
            self.after_update()
            return

        from . import utils

        size = utils.human_size(info.size) if info.size else "?"
        notes = (info.latest.body or "").strip().splitlines()[:6]
        self.set_state(
            f"Доступно обновление: {info.latest.version}",
            f"У вас {info.current} · {size} · {updater_tag(info)}",
        )
        self.set_detail("\n".join(notes))
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.set_buttons(action="Скачать и установить", skip="Позже", show=True)
        self.btn_skip.clicked.disconnect()
        self.btn_skip.clicked.connect(self.finish)
        self._stage = "update"
        self._log(f"Релиз {info.latest.tag}: {info.latest.url}")

    def _on_action(self) -> None:
        stage = self._stage
        if stage == "update":
            self._download_update()
        elif stage == "java":
            self._on_java_action()
        elif stage == "restart":
            self.restart()
        else:
            self.finish()

    def _download_update(self) -> None:
        from . import updater
        from .workers import background

        rel = self.update_info.latest
        self._stage = "update"
        self.btn_action.setEnabled(False)
        self.set_buttons(action="Скачивание…", skip="", show=True)
        self.set_state("Загрузка обновления…", f"{rel.version}")
        self._log(f"Скачиваем релиз {rel.tag}")

        def work(ctx):
            archive = updater.download_release(rel, ctx.progress, ctx.status)
            return updater.apply_update(archive, rel, status=ctx.status)

        self.worker = background(work, on_result=self._update_done,
                                 on_error=self._update_error, parent=self)

    def _update_done(self, result):
        deferred = bool(getattr(result, "deferred", False))
        entry = getattr(result, "entry", result)
        version = rel_version(self)

        if deferred:
            self.set_state("Обновление готово", f"Версия {version} · перезапуск…")
            self.bar.setRange(0, 100)
            self.bar.setValue(100)
            self._log(f"Файлы будут заменены после закрытия: {entry}")
            self.set_buttons(show=False)
            self._update_done_flag = True
            self._stage = "restart"
            QTimer.singleShot(900, self._quit_for_update)
            return

        write_version_file(version)
        self.set_state("Обновление установлено", f"Новая версия {version}")
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self._log(f"Готово: {entry}")
        self.set_buttons(action="Перезапустить", skip="", show=True)
        self.btn_action.setEnabled(True)
        self._update_done_flag = True
        self._stage = "restart"

    def _quit_for_update(self) -> None:
        self._done = True
        self._ticker.stop()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _update_error(self, e: str) -> None:
        self.btn_action.setEnabled(True)
        self._stage = "update"
        self.set_buttons(action="Повторить", skip="Пропустить", show=True)
        self.btn_skip.clicked.disconnect()
        self.btn_skip.clicked.connect(self.finish)
        self.set_state("Не удалось обновиться", str(e))
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self._log(f"Ошибка обновления: {e}")

    def after_update(self) -> None:
        from . import java as javamod
        from .workers import background

        if self._done:
            return
        self._java_checked = True
        if not self._check_java:
            self.after_java()
            return

        self.set_state("Поиск Java…", "Проверяем установленные версии")
        self.bar.setRange(0, 0)

        def work(ctx):
            return javamod.detect_javas(max_age=0, cancelled=ctx.is_cancelled)

        self.worker = background(work, on_result=self._java_scan_done,
                                 on_error=self._java_scan_error, parent=self)

    def _java_scan_done(self, javas) -> None:
        if self._done:
            return
        from . import java as javamod

        if javas:
            best = max(javas, key=lambda j: j.major)
            self._log(f"Java {best.major} ({best.version}) уже установлена")
            self.after_java()
            return
        need = javamod.preferred_java(self._target_mc_version())
        self._java_major = need
        if need == 25:
            hint = "Minecraft 1.21 и новее работает на Java 25 (поддерживает и 21-ю)"
        elif need == 21:
            hint = "Для Minecraft 1.17–1.20.6 нужна Java 21"
        else:
            hint = f"Для Minecraft {self._target_mc_version()} нужна Java {need}"
        self.set_state("Java не найдена", hint)
        self.set_buttons(action=f"Скачать Java {need}", skip="Другая версия", show=True)
        self.btn_skip.clicked.disconnect()
        self.btn_skip.clicked.connect(self._java_version_menu)
        self._stage = "java"
        self._log("Java не найдена в системе")

    def _java_scan_error(self, e: str) -> None:
        if self._done:
            return
        from . import utils

        utils.log(f"Поиск Java не удался: {e}", "WARN")
        self._log(f"Поиск Java не удался: {e}")
        self.after_java()

    def _java_version_menu(self) -> None:
        from PySide6.QtWidgets import QMenu

        from .ui import icons as ui_icons
        from .ui import theme as ui_theme

        m = QMenu(self)
        for major in (25, 21, 17, 8):
            act = m.addAction(ui_icons.make_icon("coffee", ui_theme.TEXT_DIM, 16),
                              f"Скачать Java {major}")
            act.triggered.connect(lambda _=False, v=major: self._on_java_action(v))
        m.addSeparator()
        m.addAction(ui_icons.make_icon("close", ui_theme.TEXT_DIM, 16),
                    "Пропустить").triggered.connect(self.after_java)
        m.exec(self.btn_skip.mapToGlobal(QPoint(0, self.btn_skip.height() + 6)))

    def _on_java_action(self, major: Optional[int] = None) -> None:
        from . import java as javamod
        from .workers import background

        major = int(major or self._java_major)
        self._java_major = major
        self._stage = "java"
        self.btn_action.setEnabled(False)
        self.set_buttons(action="Загрузка…", skip="", show=True)
        self.set_state(f"Загрузка Java {major}…", "Temurin (Adoptium), ~200 МБ")
        self._log(f"Adoptium Temurin {major}")

        def work(ctx):
            return javamod.download_java(major, ctx.progress, ctx.status)

        self.worker = background(work, on_result=self._java_done,
                                 on_error=self._java_error, parent=self)

    def _java_done(self, info) -> None:
        if info.major != self._java_major:
            self._log(f"Скачана Java {info.major} вместо запрошенной {self._java_major}")
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.set_state(f"Java {info.major} установлена", str(info.path))
        self._stage = "done"
        self._log(f"{info.version} · {info.path}")
        QTimer.singleShot(900, self.after_java)

    def _java_error(self, e: str) -> None:
        self.btn_action.setEnabled(True)
        self._stage = "java"
        self.set_buttons(action="Повторить", skip="Другая версия", show=True)
        self.btn_skip.clicked.disconnect()
        self.btn_skip.clicked.connect(self._java_version_menu)
        self.set_state("Не удалось скачать Java", str(e))
        self.bar.setRange(0, 100)
        self.bar.setValue(0)

    def _target_mc_version(self) -> str:
        try:
            from . import instances as inst

            items = inst.repo().all()
            if items:
                return items[0].base_mc
        except Exception:
            pass
        return ""

    def after_java(self) -> None:
        self.set_state("Запуск…", f"Будет выделено {self._ram_text()} памяти")
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.set_buttons(show=False)
        QTimer.singleShot(320, self.finish)

    @staticmethod
    def _ram_text() -> str:
        ram = suggested_ram_mb()
        return (f"{ram // 1024} ГБ" if ram >= 1024 else f"{ram} МБ")

    def finish(self) -> None:
        if self._done:
            return
        self._done = True
        self._ticker.stop()
        self.finished.emit()
        self.close()

    def restart(self) -> None:
        if self._done:
            return
        self._done = True
        self._ticker.stop()
        from . import updater

        self._log("Перезапуск…")
        updater.relaunch()
        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def reject_flow(self) -> None:
        self._done = True
        self._ticker.stop()
        self.refused.emit()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


def rel_version(splash: Splash) -> str:
    info = splash.update_info
    return info.latest.version if info and info.latest else "?"


def updater_tag(info) -> str:
    rel = info.latest
    if rel and rel.assets:
        a = rel.pick_asset()
        if a:
            return a.get("name", "")
    return ""


def write_version_file(version: str) -> None:
    import json

    from . import paths

    try:
        (paths.base_dir() / "version.json").write_text(
            json.dumps({"version": version, "updated": int(time.time())}, indent=2),
            encoding="utf-8")
    except Exception:
        pass
