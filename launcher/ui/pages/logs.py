from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QSplitter, QVBoxLayout,
                               QWidget)

from ... import paths, utils
from ...config import get_config
from .. import icons, theme
from ..widgets import (Badge, ElidedLabel, FlatCard, GhostButton, IconButton,
                       PrimaryButton, label, toast)


class LogsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self.cfg = get_config()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(14)

        head = QHBoxLayout()
        box = QVBoxLayout()
        box.setSpacing(3)
        box.addWidget(label(self.cfg.t("logs_title"), size=25, bold=True))
        self.subtitle = ElidedLabel("", size=13, color=theme.TEXT_DIM)
        box.addWidget(self.subtitle)
        head.addLayout(box, 1)
        self.btn_copy = GhostButton(self.cfg.t("copy"), icon_name="copy")
        self.btn_copy.clicked.connect(self._copy)
        head.addWidget(self.btn_copy)
        self.btn_clear = GhostButton(self.cfg.t("clear"), icon_name="trash")
        self.btn_clear.clicked.connect(self._clear)
        head.addWidget(self.btn_clear)
        self.btn_open = GhostButton(self.cfg.t("logs_open"), icon_name="folder")
        self.btn_open.clicked.connect(lambda: utils.open_path(paths.logs_dir()))
        head.addWidget(self.btn_open)
        root.addLayout(head)

        split = QSplitter(Qt.Vertical)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(8)

        card = FlatCard()
        v = QVBoxLayout(card)
        v.setContentsMargins(4, 4, 4, 4)
        v.setSpacing(6)
        v.addWidget(label(self.cfg.t("logs_launcher"), obj="SectionTitle"))
        self.output = self._console()
        self.output.setPlaceholderText(self.cfg.t("logs_placeholder"))
        v.addWidget(self.output, 1)
        split.addWidget(card)

        self.console_card = FlatCard()
        cv = QVBoxLayout(self.console_card)
        cv.setContentsMargins(4, 4, 4, 4)
        cv.setSpacing(6)
        crow = QHBoxLayout()
        crow.setSpacing(8)
        crow.addWidget(label(self.cfg.t("console_title"), obj="SectionTitle"))
        crow.addStretch(1)
        self.btn_console_clear = GhostButton(self.cfg.t("clear"))
        self.btn_console_clear.clicked.connect(self.clear_console)
        crow.addWidget(self.btn_console_clear)
        cv.addLayout(crow)
        self.console = self._console()
        self.console.setPlaceholderText(self.cfg.t("console_placeholder"))
        cv.addWidget(self.console, 1)
        split.addWidget(self.console_card)

        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        self.console_card.setVisible(False)
        root.addWidget(split, 1)

    def _console(self) -> QPlainTextEdit:
        box = QPlainTextEdit()
        box.setReadOnly(True)
        box.setFont(theme.mono_font(12))
        box.setLineWrapMode(QPlainTextEdit.NoWrap)
        box.setStyleSheet(
            f"QPlainTextEdit{{background:{theme.BG};border:none;border-radius:8px;"
            f"color:{theme.TEXT_DIM};padding:10px;}}")
        return box

    def refresh(self):
        self.cfg = get_config()
        log_file = paths.logs_dir() / f"launcher-{datetime.now():%Y-%m-%d}.log"
        text = ""
        if log_file.exists():
            try:
                lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
                text = "\n".join(lines[-500:])
            except Exception:
                text = ""
        if text.strip() and text.strip() != self.output.toPlainText():
            self.output.setPlainText(text)
            self.output.verticalScrollBar().setValue(
                self.output.verticalScrollBar().maximum())
        self.subtitle.setText(log_file.name)
        self.subtitle.setToolTip(str(log_file))

    def append(self, line: str) -> None:
        self.output.appendPlainText(line)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def append_game(self, line: str) -> None:
        self.console.appendPlainText(line)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())
        if not self.console_card.isVisible():
            self.console_card.setVisible(True)

    def clear_console(self) -> None:
        self.console.clear()
        self.console_card.setVisible(False)

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.output.toPlainText() + "\n" +
                                         self.console.toPlainText())
        toast(self, self.cfg.t("copy"), "success")

    def _clear(self) -> None:
        self.output.clear()
        self.console.clear()
        toast(self, self.cfg.t("cleared"), "success")
