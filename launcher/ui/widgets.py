from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import (QEasingCurve, QObject, QPoint, QPointF, QPropertyAnimation,
                            QRect, QRectF, QSize, Qt, QTimer, Signal, Property)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGraphicsOpacityEffect,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import icons, theme


def label(text: str = "", obj: str = "", size: int = 13, color: Optional[str] = None,
          bold: bool = False, wrap: bool = False) -> QLabel:
    lab = QLabel(text)
    if obj:
        lab.setObjectName(obj)
    font = theme.ui_font(size, 700 if bold else 400)
    if color:
        from PySide6.QtGui import QColor as QC
        c = QC(color)
        lab.setStyleSheet(f"color:{c.name()}; background:transparent;")
    lab.setFont(font)
    if wrap:
        lab.setWordWrap(True)
    return lab


def title(text: str) -> QLabel:
    lab = label(text, size=26, bold=True)
    return lab


def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("Divider")
    f.setFixedHeight(1)
    return f


def elide(text: str, width: int, font: Optional[QFont] = None) -> str:
    fm = QFontMetrics(font or ui_font(13))
    return fm.elidedText(text or "", Qt.ElideRight, max(20, width))


def hline() -> QFrame:
    return divider()


def spacer(h: int = 0, w: int = 0) -> QWidget:
    wgt = QWidget()
    if h:
        wgt.setFixedHeight(h)
    if w:
        wgt.setFixedWidth(w)
    if not h and not w:
        wgt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return wgt


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", size: int = 13, color: Optional[str] = None,
                 bold: bool = False, parent=None):
        super().__init__(parent)
        self._full = text
        self.setFont(theme.ui_font(size, 700 if bold else 400))
        if color:
            self.setStyleSheet(f"color:{color};background:transparent;")
        self.setText(text)

    def setText(self, text: str) -> None:
        self._full = text or ""
        self._apply()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply()

    def _apply(self) -> None:
        super().setText(QFontMetrics(self.font()).elidedText(
            self._full, Qt.ElideRight, max(20, self.width() - 2)))
        if self.toolTip() != self._full and self._full:
            self.setToolTip(self._full)


class Card(QFrame):
    clicked = Signal()

    def __init__(self, parent=None, selected: bool = False, clickable: bool = True):
        super().__init__(parent)
        self.setObjectName("CardSelected" if selected else "Card")
        self._selected = selected
        self._clickable = clickable
        self._hover = False
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    def set_selected(self, sel: bool) -> None:
        self._selected = sel
        self.setObjectName("CardSelected" if sel else "Card")
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._clickable and e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(e)


class FlatCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFlat")


class PrimaryButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("Primary")
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(theme.ui_font(13, 700))


class GhostButton(QPushButton):
    def __init__(self, text: str = "", parent=None, icon_name: str = ""):
        super().__init__(text, parent)
        self.setObjectName("Ghost")
        self.setCursor(Qt.PointingHandCursor)
        if icon_name:
            self.setIcon(icons.make_icon(icon_name, theme.TEXT_DIM, 16))
        self.setFont(theme.ui_font(12, 600))


class IconButton(QPushButton):
    def __init__(self, icon_name: str = "", color: str = "", size: int = 36,
                 parent=None, tip: str = ""):
        super().__init__(parent)
        self._icon_name = icon_name
        self._color = color or theme.TEXT_DIM
        self._icon_size = max(12, int(size * 0.55))
        self.setFixedSize(size, size)
        self.setIcon(icons.make_icon(icon_name, self._color, self._icon_size))
        self.setIconSize(QSize(self._icon_size, self._icon_size))
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{background:transparent;border:none;}"
                           f"QPushButton:hover{{background:{theme.CARD_HOVER};"
                           "border-radius:8px;}")
        if tip:
            self.setToolTip(tip)

    def set_color(self, color: str) -> None:
        self._color = color
        self.setIcon(icons.make_icon(self._icon_name, color, self._icon_size))
        self.setIconSize(QSize(self._icon_size, self._icon_size))


class Chip(QPushButton):
    def __init__(self, text: str, parent=None, checkable: bool = True):
        super().__init__(text, parent)
        self.setObjectName("Chip")
        self.setCheckable(checkable)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(theme.ui_font(12, 600))


class ComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(QColor(theme.TEXT_DIM))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        cx = self.width() - 17
        cy = self.height() / 2
        p.drawPolyline([QPointF(cx - 4, cy - 2), QPointF(cx, cy + 2.5),
                        QPointF(cx + 4, cy - 2)])
        p.end()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


class Avatar(QWidget):
    def __init__(self, size: int = 30, parent=None):
        super().__init__(parent)
        self._size = size
        self._pix: Optional[QPixmap] = None
        self._letter = "?"
        self.setFixedSize(size, size)

    def set_size(self, size: int) -> None:
        self._size = size
        self.setFixedSize(size, size)
        self.update()

    def set_image(self, path: Optional[Path]) -> None:
        if path and Path(path).exists():
            self._pix = round_pixmap(path, self._size)
        else:
            self._pix = None
        self.update()

    def set_name(self, name: str) -> None:
        name = (name or "?").strip()
        self._letter = (name[0].upper() if name else "?")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        d = self._size
        box = QRectF(0, 0, d - 1, d - 1)

        if self._pix is not None:
            path = QPainterPath()
            path.addEllipse(box)
            p.setClipPath(path)
            scaled = self._pix.scaled(
                QSize(d, d), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap(0, 0, scaled)
            p.setClipping(False)
            p.setPen(QPen(QColor(theme.BORDER_LIGHT), 1.0))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(box.adjusted(0.5, 0.5, -0.5, -0.5))
        else:
            hue = sum(ord(c) for c in self._letter) % 360
            top = QColor.fromHsv(hue, 90, 150)
            bottom = QColor.fromHsv((hue + 40) % 360, 110, 105)
            grad = QLinearGradient(0, 0, d, d)
            grad.setColorAt(0.0, top)
            grad.setColorAt(1.0, bottom)
            p.setBrush(grad)
            p.setPen(QPen(QColor(theme.mix(theme.BORDER_LIGHT, theme.BG, 0.3)), 1.0))
            p.drawEllipse(box.adjusted(0.5, 0.5, -0.5, -0.5))

            f = QFont(theme.ui_font(0, 700))
            f.setPixelSize(int(d * 0.46))
            p.setFont(f)
            p.setPen(QColor("#ffffff"))
            p.drawText(box, Qt.AlignCenter, self._letter)
        p.end()


class RoundCheckBox(QCheckBox):
    SIZE = 22
    GAP = 9

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(self.SIZE)
        self.setStyleSheet(
            f"QCheckBox{{color:{theme.TEXT};spacing:{self.GAP}px;}}"
            f"QCheckBox::indicator{{width:{self.SIZE}px;height:{self.SIZE}px;"
            "border:none;background:transparent;}"
            f"QCheckBox:disabled{{color:{theme.TEXT_MUTED};}}")
        self.setAttribute(Qt.WA_Hover, True)

    def sizeHint(self) -> QSize:
        h = self.SIZE
        w = h + self.GAP + self.fontMetrics().horizontalAdvance(self.text())
        return QSize(w, h)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        d = self.SIZE
        box = QRectF(0.5, (self.height() - d) / 2, d - 1, d - 1)
        radius = box.width() / 2

        if self.isChecked():
            grad = QLinearGradient(box.topLeft(), box.bottomRight())
            grad.setColorAt(0.0, theme.mix(theme.accent(self._accent()), "#ffffff", 0.22))
            grad.setColorAt(1.0, theme.accent(self._accent()))
            p.setBrush(grad)
            p.setPen(QPen(QColor(theme.accent(self._accent())), 1.4))
            p.drawEllipse(box)
            pen = QPen(QColor("#ffffff"), 2.2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            path = QPainterPath()
            path.moveTo(box.left() + box.width() * 0.26, box.top() + box.height() * 0.52)
            path.lineTo(box.left() + box.width() * 0.44, box.top() + box.height() * 0.70)
            path.lineTo(box.left() + box.width() * 0.76, box.top() + box.height() * 0.32)
            p.drawPath(path)
        else:
            p.setBrush(QColor(theme.mix(theme.BG, theme.CARD, 0.35)))
            edge = theme.BORDER_LIGHT
            if self.underMouse() and self.isEnabled():
                edge = theme.mix(theme.BORDER_LIGHT, theme.accent(self._accent()), 0.45)
            if not self.isEnabled():
                edge = theme.BORDER
            p.setPen(QPen(QColor(edge), 1.5))
            p.drawEllipse(box)
        p.end()

    def _accent(self) -> str:
        return getattr(self, "_accent_name", "blue")

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()


class Badge(QLabel):
    def __init__(self, text: str = "", color: str = "", parent=None):
        super().__init__(text, parent)
        self.set_color(color or theme.INFO)
        self.setAlignment(Qt.AlignCenter)
        self.setFont(theme.ui_font(11, 700))
        self.setContentsMargins(0, 0, 0, 0)

    def set_color(self, color: str) -> None:
        c = QColor(color)
        bg = f"rgba({c.red()}, {c.green()}, {c.blue()}, 0.16)"
        self.setStyleSheet(
            f"background:{bg};color:{color};"
            f"border-radius:{theme.RADIUS_BADGE}px;padding:3px 8px;"
            "font-weight:700;font-size:11px;")


class SearchBox(QLineEdit):
    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setMinimumHeight(38)
        act = self.addAction(icons.make_icon("search", theme.TEXT_MUTED, 16),
                             QLineEdit.LeadingPosition)
        act.setToolTip("")


class Toast(QFrame):
    def __init__(self, parent, text: str = "", kind: str = "info", msec: int = 3200):
        super().__init__(parent)
        colors = {
            "info": theme.INFO, "success": theme.SUCCESS,
            "warning": theme.WARNING, "error": theme.DANGER,
        }
        color = colors.get(kind, theme.INFO)
        icon_name = {"info": "info", "success": "check", "warning": "alert",
                     "error": "close"}.get(kind, "info")
        self.setFixedHeight(46)
        self.setStyleSheet(
            f"background:{theme.CARD};border:1px solid {theme.BORDER_LIGHT};"
            f"border-left:3px solid {color};border-radius:10px;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 14, 6)
        lay.setSpacing(10)
        ico = QLabel()
        ico.setPixmap(icons.make_pixmap(icon_name, color, 18))
        lay.addWidget(ico)
        txt = QLabel(text)
        txt.setFont(theme.ui_font(12, 600))
        txt.setStyleSheet(f"color:{theme.TEXT};background:transparent;")
        lay.addWidget(txt)
        lay.addStretch(1)

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(220)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.show()
        self._anim.start()
        QTimer.singleShot(msec, self._fade_out)

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._effect.opacity())
        self._anim.setEndValue(0.0)
        self._anim.setDuration(260)
        self._anim.finished.connect(self.deleteLater)
        self._anim.start()


def toast(parent, text: str, kind: str = "info", msec: int = 3200) -> Toast:
    win = parent.window() if hasattr(parent, "window") else parent
    t = Toast(win, text, kind, msec)
    t.adjustSize()
    t.setFixedWidth(min(t.sizeHint().width() + 8, max(260, win.width() - 60)))
    t.move(max(12, win.width() - t.width() - 24),
           max(12, win.height() - t.height() - 24))
    t.raise_()
    return t


class SearchField(SearchBox):
    pass


class ScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)
        self._inner = QWidget()
        self._inner.setObjectName("ScrollInner")
        lay = QVBoxLayout(self._inner)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(12)
        self.setWidget(self._inner)
        self.body = lay

    def add(self, w: QWidget) -> QWidget:
        self.body.addWidget(w)
        return w

    def add_layout(self, lay) -> None:
        self.body.addLayout(lay)


class InstanceIcon(QWidget):
    def __init__(self, color: str = "#5aa469", size: int = 52, glyph: str = "cube",
                 parent=None):
        super().__init__(parent)
        self._color = color
        self._glyph = glyph
        self.setFixedSize(size, size)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        s = min(self.width(), self.height())
        rect = QRect(0, 0, s, s)
        c = QColor(self._color)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, c.lighter(135).name())
        grad.setColorAt(1, c.darker(125).name())
        path = QPainterPath()
        path.addRoundedRect(0, 0, s, s, s * 0.26, s * 0.26)
        p.fillPath(path, grad)
        p.setPen(QColor(255, 255, 255, 40))
        p.drawPath(path)

        inner = s * 0.52
        pm = icons.make_pixmap(self._glyph, "#ffffff", int(inner), ratio=8.0)
        p.drawPixmap(int((s - inner) / 2), int((s - inner) / 2), pm)


def round_pixmap(path: Path, size: int = 40) -> QPixmap:
    pm = QPixmap(str(path))
    if pm.isNull():
        return QPixmap()
    pm = pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing, True)
    path_obj = QPainterPath()
    path_obj.addEllipse(0, 0, size, size)
    p.setClipPath(path_obj)
    p.drawPixmap(-(pm.width() - size) // 2, -(pm.height() - size) // 2, pm)
    p.end()
    return out


class _ImageLoader(QObject):
    loaded = Signal(object)

    def __init__(self, lab: QLabel, size: int) -> None:
        super().__init__(lab)
        self._lab = lab
        self._size = size

    def fetch(self, url: str) -> None:
        data = None
        try:
            import requests

            r = requests.get(url, timeout=10,
                             headers={"User-Agent": "FimpleLauncher/1.0"})
            if r.status_code == 200 and r.content:
                data = r.content
        except Exception:
            pass
        try:
            self.loaded.emit(data)
        except RuntimeError:
            pass

    def apply(self, data) -> None:
        if not data:
            return
        try:
            size = self._size
            pm = QPixmap()
            if not pm.loadFromData(data):
                return
            pm = pm.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                           Qt.SmoothTransformation)
            mask = QPixmap(size, size)
            mask.fill(Qt.transparent)
            p = QPainter(mask)
            p.setRenderHint(QPainter.Antialiasing, True)
            path = QPainterPath()
            path.addRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
            p.setClipPath(path)
            p.drawPixmap(0, 0, pm)
            p.end()
            self._lab.setPixmap(mask)
        except RuntimeError:
            pass


def network_image(url: str, size: int = 32, parent: Optional[QWidget] = None) -> QLabel:
    lab = QLabel(parent)
    lab.setFixedSize(size, size)
    lab.setAlignment(Qt.AlignCenter)
    lab.setStyleSheet("border-radius:8px;background:transparent;")

    loader = _ImageLoader(lab, size)
    loader.loaded.connect(loader.apply, Qt.QueuedConnection)

    import threading

    threading.Thread(target=loader.fetch, args=(url,), daemon=True).start()
    return lab


class ProgressRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardFlat")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 13)
        lay.setSpacing(9)
        top = QHBoxLayout()
        self.status = label("", size=12, bold=True)
        self.pct = label("", size=11, color=theme.TEXT_MUTED)
        top.addWidget(self.status, 1)
        top.addWidget(self.pct)
        lay.addLayout(top)
        self.cancel_btn = GhostButton("✕")
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.clicked.connect(self._cancel)
        top.addWidget(self.cancel_btn)
        lay.addWidget(self.progressbar())

    def progressbar(self) -> QWidget:
        from PySide6.QtWidgets import QProgressBar

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        return self.bar

    def set(self, text: str, percent: int = -1) -> None:
        self.cancel_btn.setVisible(True)
        self.cancel_btn.setEnabled(True)
        self.status.setText(text)
        if percent >= 0:
            self.bar.setValue(max(0, min(100, percent)))
            self.pct.setText(f"{int(percent)}%")
        else:
            from PySide6.QtWidgets import QProgressBar

            self.bar.setRange(0, 0)
            self.pct.setText("")

    def set_done(self, text: str) -> None:
        from PySide6.QtWidgets import QProgressBar

        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.status.setText(text)
        self.pct.setText("100%")
        self.cancel_btn.setVisible(False)

    def _cancel(self) -> None:
        parent = self.parent()
        if parent and hasattr(parent, "cancel_current"):
            parent.cancel_current()
        self.set("Отмена…", -1)
        self.cancel_btn.setEnabled(False)
