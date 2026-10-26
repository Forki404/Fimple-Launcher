from __future__ import annotations

import sys
import traceback
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import appicon, paths, utils
from .config import get_config
from .ui import icons, theme


def _install_excepthook(app: QApplication) -> None:
    def hook(exc_type, exc_value, exc_tb):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        utils.log(f"Необработанная ошибка:\n{text}", "ERROR")
        if exc_type is KeyboardInterrupt:
            return
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Fimple Launcher — ошибка")
            box.setText(f"{exc_type.__name__}: {exc_value}")
            box.setDetailedText(text)
            box.setStyleSheet(theme.stylesheet(get_config().get("accent")))
            box.exec()
        except Exception:
            pass

    sys.excepthook = hook
    _ = app


def main(argv: Optional[list] = None) -> int:
    argv = list(argv if argv is not None else sys.argv)
    utils.init_logging()
    utils.log(f"Запуск Fimple Launcher {paths.app_version()} · Python {sys.version.split()[0]}")

    skip_splash = "--no-splash" in argv
    no_update = "--no-update" in argv
    no_java = "--no-java" in argv

    try:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName("Fimple Launcher")
    app.setApplicationDisplayName("Fimple Launcher")
    app.setApplicationVersion(paths.app_version())
    app.setOrganizationName("Forki404")
    acc = get_config()
    app.setStyleSheet(theme.stylesheet(acc.get("accent")))
    app.setWindowIcon(appicon.app_icon(theme.accent(acc.get("accent"))))
    _install_excepthook(app)

    from . import workers
    from .ui.main_window import MainWindow

    app.aboutToQuit.connect(workers.shutdown)

    if skip_splash:
        win = MainWindow()
        win.show()
        return app.exec()

    from .bootstrap import Splash

    def on_ready():
        win = MainWindow()
        win.show()
        win.raise_()
        win.activateWindow()

    splash = Splash(check_updates=not no_update and acc.get("check_updates", True),
                    check_java=not no_java and acc.get("check_java", True))
    splash.finished.connect(on_ready)
    splash.refused.connect(lambda: app.quit())
    splash.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
