from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap)

from . import paths

ICON_FILES = ("icon.ico", "icon.png", "logo.ico", "logo.png", "fimple.ico",
              "fimple.png")

_cache: dict = {}


def find_icon_file(for_window: bool = True) -> Optional[Path]:
    names = ICON_FILES if for_window else tuple(
        n for n in ICON_FILES if n.endswith(".ico"))
    for folder in (paths.base_dir(), paths.resource_dir(), paths.base_dir() / "assets"):
        for name in names:
            p = folder / name
            if p.exists() and p.stat().st_size > 0:
                return p
    return None


def _square_source() -> Optional[Path]:
    ico = find_icon_file(for_window=False)
    if ico is not None:
        return ico
    png = _png_source()
    if png is None:
        return None
    pm = QPixmap(str(png))
    if pm.isNull():
        return None
    if pm.width() == pm.height():
        return png
    side = min(pm.width(), pm.height())
    square = pm.copy(0, 0, side, side)
    target = paths.cache_dir() / "ui" / "app_icon.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if square.save(str(target)):
            return target
    except Exception:
        pass
    return None


def _png_source() -> Optional[Path]:
    for folder in (paths.base_dir(), paths.resource_dir(), paths.base_dir() / "assets"):
        for name in ICON_FILES:
            if not name.endswith(".png"):
                continue
            p = folder / name
            if p.exists() and p.stat().st_size > 0:
                return p
    return None


def render(size: int, accent: str = "#3b82f6") -> QPixmap:
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    s = float(size)

    body = QColor(accent)
    grad = QLinearGradient(0, 0, 0, s)
    grad.setColorAt(0.0, body.lighter(128).name())
    grad.setColorAt(1.0, body.darker(122).name())
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, s, s), s * 0.24, s * 0.24)
    p.fillPath(path, grad)

    top = [QPointF(s * .5, s * .26), QPointF(s * .76, s * .40),
           QPointF(s * .5, s * .54), QPointF(s * .24, s * .40)]
    side_l = [QPointF(s * .24, s * .40), QPointF(s * .5, s * .54),
              QPointF(s * .5, s * .78), QPointF(s * .24, s * .64)]
    side_r = [QPointF(s * .76, s * .40), QPointF(s * .5, s * .54),
              QPointF(s * .5, s * .78), QPointF(s * .76, s * .64)]
    p.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, s * 0.018)))
    p.setBrush(QColor(255, 255, 255, 210))
    p.drawPolygon(top)
    p.setBrush(QColor(255, 255, 255, 150))
    p.drawPolygon(side_l)
    p.setBrush(QColor(255, 255, 255, 110))
    p.drawPolygon(side_r)
    p.end()
    return pm


def app_icon(accent: str = "#3b82f6", sizes: Optional[List[int]] = None) -> QIcon:
    sizes = sizes or [16, 24, 32, 48, 64, 128, 256]
    key = (accent, tuple(sizes))
    if key in _cache:
        return _cache[key]

    icon = QIcon()
    file = _square_source()
    if file is not None:
        src = QPixmap(str(file))
        if not src.isNull():
            for size in sizes:
                icon.addPixmap(src.scaled(size, size, Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation))
            if not icon.isNull():
                _cache[key] = icon
                return icon
    for size in sizes:
        icon.addPixmap(render(size, accent))
    _cache[key] = icon
    return icon


def app_pixmap(size: int, accent: str = "#3b82f6") -> QPixmap:
    file = _square_source()
    if file is not None:
        pm = QPixmap(str(file))
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return render(size, accent)


def export_ico(path: Path, accent: str = "#3b82f6", size: int = 256) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        src = _square_source()
        if src is not None:
            pm = QPixmap(str(src))
            if not pm.isNull():
                scaled = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                if scaled.toImage().save(str(path), "ICO"):
                    return True
        return render(size, accent).toImage().save(str(path), "ICO")
    except Exception:
        return False


def banner(width: int = 150) -> Optional[QPixmap]:
    png = _png_source()
    if png is None:
        return None
    pm = QPixmap(str(png))
    if pm.isNull():
        return None
    return pm.scaledToWidth(width, Qt.SmoothTransformation)


def clear_cache() -> None:
    _cache.clear()
