from __future__ import annotations

import math
from typing import Callable, Dict, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)

Painter = Callable[[QPainter, float], None]


def _pen(p: QPainter, color: str, w: float) -> None:
    pen = QPen(QColor(color))
    pen.setWidthF(w)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)


def _poly(p: QPainter, pts, close=True, color=None, w=1.8):
    poly = QPolygonF([QPointF(x, y) for x, y in pts])
    if close:
        fill = color or p.pen().color().name()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(fill)))
        p.drawPolygon(poly)
    else:
        _pen(p, p.pen().color().name(), w)
        p.drawPolyline(poly)


def i_home(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.08)
    p.drawLine(QPointF(s * .18, s * .45), QPointF(s * .5, s * .18))
    p.drawLine(QPointF(s * .5, s * .18), QPointF(s * .82, s * .45))
    path = QPainterPath()
    path.moveTo(s * .12, s * .48)
    path.lineTo(s * .5, s * .16)
    path.lineTo(s * .88, s * .48)
    path.lineTo(s * .88, s * .84)
    path.lineTo(s * .12, s * .84)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(s * .42, s * .84), QPointF(s * .42, s * .6))
    p.drawLine(QPointF(s * .42, s * .6), QPointF(s * .58, s * .6))
    p.drawLine(QPointF(s * .58, s * .6), QPointF(s * .58, s * .84))


def i_cube(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    top = [(s * .5, s * .14), (s * .86, s * .33), (s * .5, s * .52), (s * .14, s * .33)]
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in top]))
    p.drawLine(QPointF(s * .14, s * .33), QPointF(s * .14, s * .7))
    p.drawLine(QPointF(s * .14, s * .7), QPointF(s * .5, s * .88))
    p.drawLine(QPointF(s * .5, s * .88), QPointF(s * .86, s * .7))
    p.drawLine(QPointF(s * .86, s * .7), QPointF(s * .86, s * .33))
    p.drawLine(QPointF(s * .5, s * .52), QPointF(s * .5, s * .88))


def i_package(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .16, s * .26, s * .68, s * .56), s * .08, s * .08)
    p.drawLine(QPointF(s * .16, s * .42), QPointF(s * .84, s * .42))
    p.drawLine(QPointF(s * .5, s * .26), QPointF(s * .5, s * .42))
    p.drawLine(QPointF(s * .5, s * .26), QPointF(s * .84, s * .42))


def i_coffee(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .18, s * .34, s * .46, s * .38), s * .06, s * .06)
    p.drawArc(QRectF(s * .58, s * .4, s * .3, s * .26), -70 * 16, 180 * 16)
    p.drawLine(QPointF(s * .12, s * .82), QPointF(s * .76, s * .82))
    p.drawLine(QPointF(s * .32, s * .24), QPointF(s * .3, s * .12))
    p.drawLine(QPointF(s * .5, s * .24), QPointF(s * .5, s * .1))


def i_gear(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    p.save()
    p.setBrush(Qt.NoBrush)
    path = QPainterPath()
    teeth = 8
    for i in range(teeth * 2):
        a0 = math.pi * i / teeth
        r_out = s * 0.38 if i % 2 == 0 else s * 0.31
        path.lineTo(s * .5 + math.cos(a0) * r_out, s * .5 + math.sin(a0) * r_out)
    path.closeSubpath()
    _pen(p, c, s * 0.075)
    p.drawPath(path)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .14, s * .14)
    p.restore()


def i_terminal(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .14, s * .2, s * .72, s * .58), s * .1, s * .1)
    p.drawPolyline(QPolygonF([QPointF(s * .3, s * .4), QPointF(s * .44, s * .5),
                              QPointF(s * .3, s * .6)]))
    p.drawLine(QPointF(s * .52, s * .62), QPointF(s * .7, s * .62))


def i_play(p: QPainter, s: float) -> None:
    color = p.pen().color().name()
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(color)))
    p.drawPolygon(QPolygonF([QPointF(s * .26, s * .16), QPointF(s * .84, s * .5),
                             QPointF(s * .26, s * .84), QPointF(s * .26, s * .64),
                             QPointF(s * .56, s * .5), QPointF(s * .26, s * .36)]))


def i_download(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.085)
    p.drawLine(QPointF(s * .5, s * .16), QPointF(s * .5, s * .62))
    p.drawPolyline(QPolygonF([QPointF(s * .3, s * .44), QPointF(s * .5, s * .64),
                              QPointF(s * .7, s * .44)]))
    p.drawPolyline(QPolygonF([QPointF(s * .2, s * .7), QPointF(s * .2, s * .84),
                              QPointF(s * .8, s * .84), QPointF(s * .8, s * .7)]))


def i_upload(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.085)
    p.drawLine(QPointF(s * .5, s * .8), QPointF(s * .5, s * .34))
    p.drawPolyline(QPolygonF([QPointF(s * .3, s * .52), QPointF(s * .5, s * .32),
                              QPointF(s * .7, s * .52)]))
    p.drawPolyline(QPolygonF([QPointF(s * .2, s * .84), QPointF(s * .2, s * .7),
                              QPointF(s * .8, s * .7), QPointF(s * .8, s * .84)]))


def i_folder(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    path = QPainterPath()
    path.moveTo(s * .14, s * .74)
    path.lineTo(s * .14, s * .3)
    path.lineTo(s * .42, s * .3)
    path.lineTo(s * .5, s * .4)
    path.lineTo(s * .86, s * .4)
    path.lineTo(s * .86, s * .74)
    path.closeSubpath()
    p.drawPath(path)


def i_plus(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.09)
    p.drawLine(QPointF(s * .5, s * .22), QPointF(s * .5, s * .78))
    p.drawLine(QPointF(s * .22, s * .5), QPointF(s * .78, s * .5))


def i_trash(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawLine(QPointF(s * .18, s * .28), QPointF(s * .82, s * .28))
    p.drawLine(QPointF(s * .4, s * .28), QPointF(s * .4, s * .18))
    p.drawLine(QPointF(s * .4, s * .18), QPointF(s * .6, s * .18))
    p.drawLine(QPointF(s * .6, s * .18), QPointF(s * .6, s * .28))
    p.drawRoundedRect(QRectF(s * .24, s * .28, s * .52, s * .56), s * .05, s * .05)
    p.drawLine(QPointF(s * .42, s * .42), QPointF(s * .42, s * .7))
    p.drawLine(QPointF(s * .58, s * .42), QPointF(s * .58, s * .7))


def i_search(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.085)
    p.drawEllipse(QPointF(s * .44, s * .44), s * .26, s * .26)
    p.drawLine(QPointF(s * .63, s * .63), QPointF(s * .84, s * .84))


def i_refresh(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.08)
    rect = QRectF(s * .2, s * .2, s * .6, s * .6)
    p.drawArc(rect, 60 * 16, 250 * 16)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(c)))
    p.drawPolygon(QPolygonF([QPointF(s * .74, s * .1), QPointF(s * .84, s * .34),
                             QPointF(s * .6, s * .3)]))


def i_check(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.1)
    p.drawPolyline(QPolygonF([QPointF(s * .22, s * .52), QPointF(s * .42, s * .72),
                              QPointF(s * .8, s * .28)]))


def i_close(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.09)
    p.drawLine(QPointF(s * .26, s * .26), QPointF(s * .74, s * .74))
    p.drawLine(QPointF(s * .74, s * .26), QPointF(s * .26, s * .74))


def i_user(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawEllipse(QPointF(s * .5, s * .36), s * .17, s * .17)
    p.drawArc(QRectF(s * .22, s * .56, s * .56, s * .5), 180 * 16, 180 * 16)


def i_globe(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .34, s * .34)
    p.drawLine(QPointF(s * .16, s * .5), QPointF(s * .84, s * .5))
    p.drawArc(QRectF(s * .3, s * .16, s * .4, s * .68), 90 * 16, 180 * 16)
    p.drawArc(QRectF(s * .3, s * .16, s * .4, s * .68), 270 * 16, 180 * 16)


def i_edit(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawPolyline(QPolygonF([QPointF(s * .66, s * .16), QPointF(s * .84, s * .34),
                              QPointF(s * .38, s * .8), QPointF(s * .2, s * .86),
                              QPointF(s * .26, s * .68), QPointF(s * .66, s * .16)]))


def i_copy(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .16, s * .16, s * .46, s * .54), s * .07, s * .07)
    p.drawRoundedRect(QRectF(s * .38, s * .3, s * .46, s * .54), s * .07, s * .07)


def i_external(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.08)
    p.drawPolyline(QPolygonF([QPointF(s * .62, s * .18), QPointF(s * .84, s * .18),
                              QPointF(s * .84, s * .4)]))
    p.drawLine(QPointF(s * .84, s * .18), QPointF(s * .48, s * .54))
    p.drawPolyline(QPolygonF([QPointF(s * .68, s * .82), QPointF(s * .2, s * .82),
                              QPointF(s * .2, s * .34), QPointF(s * .6, s * .34)]))


def i_cpu(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .26, s * .26, s * .48, s * .48), s * .07, s * .07)
    p.drawRoundedRect(QRectF(s * .4, s * .4, s * .2, s * .2), s * .03, s * .03)
    for i in (0.36, 0.5, 0.64):
        p.drawLine(QPointF(s * i, s * .14), QPointF(s * i, s * .26))
        p.drawLine(QPointF(s * i, s * .74), QPointF(s * i, s * .86))
        p.drawLine(QPointF(s * .14, s * i), QPointF(s * .26, s * i))
        p.drawLine(QPointF(s * .74, s * i), QPointF(s * .86, s * i))


def i_palette(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.07)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .36, s * .36)
    for cx, cy in ((.38, .38), (.62, .38), (.38, .62)):
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(c)))
        p.drawEllipse(QPointF(s * cx, s * cy), s * .06, s * .06)
        p.setBrush(Qt.NoBrush)


def i_grass(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.07)
    p.drawRoundedRect(QRectF(s * .2, s * .3, s * .6, s * .54), s * .06, s * .06)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(c)))
    p.drawRect(QRectF(s * .2, s * .3, s * .6, s * .16))
    p.setBrush(Qt.NoBrush)


def i_hammer(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.09)
    p.drawLine(QPointF(s * .3, s * .86), QPointF(s * .68, s * .34))
    p.drawRoundedRect(QRectF(s * .52, s * .14, s * .34, s * .26), s * .05, s * .05)


def i_layers(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.07)
    for dy in (0.0, 0.16, 0.32):
        p.drawPolygon(QPolygonF([QPointF(s * .5, s * (.22 + dy)),
                                 QPointF(s * .82, s * (.4 + dy)),
                                 QPointF(s * .5, s * (.58 + dy)),
                                 QPointF(s * .18, s * (.4 + dy))]))


def i_alert(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.08)
    p.drawLine(QPointF(s * .5, s * .18), QPointF(s * .5, s * .56))
    p.drawEllipse(QPointF(s * .5, s * .74), s * .045, s * .045)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .38, s * .38)


def i_info(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.08)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .36, s * .36)
    p.drawLine(QPointF(s * .5, s * .46), QPointF(s * .5, s * .72))
    p.drawEllipse(QPointF(s * .5, s * .3), s * .05, s * .05)


def i_chevron_left(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.09)
    p.drawPolyline(QPolygonF([QPointF(s * .62, s * .22), QPointF(s * .38, s * .5),
                              QPointF(s * .62, s * .78)]))


def i_chevron_right(p: QPainter, s: float) -> None:
    _pen(p, p.pen().color().name(), s * 0.09)
    p.drawPolyline(QPolygonF([QPointF(s * .38, s * .22), QPointF(s * .62, s * .5),
                              QPointF(s * .38, s * .78)]))


def i_sun(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.07)
    p.drawEllipse(QPointF(s * .5, s * .5), s * .19, s * .19)
    for i in range(8):
        a = math.pi * i / 4
        p.drawLine(QPointF(s * .5 + math.cos(a) * s * .28, s * .5 + math.sin(a) * s * .28),
                   QPointF(s * .5 + math.cos(a) * s * .38, s * .5 + math.sin(a) * s * .38))


def i_link(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.08)
    p.drawArc(QRectF(s * .12, s * .34, s * .44, s * .32), 90 * 16, 180 * 16)
    p.drawArc(QRectF(s * .44, s * .34, s * .44, s * .32), 270 * 16, 180 * 16)
    p.drawLine(QPointF(s * .36, s * .5), QPointF(s * .64, s * .5))


def i_grass_block(p: QPainter, s: float) -> None:
    i_grass(p, s)


def i_shield(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    path = QPainterPath()
    path.moveTo(s * .5, s * .12)
    path.lineTo(s * .82, s * .24)
    path.lineTo(s * .82, s * .5)
    path.cubicTo(s * .82, s * .72, s * .68, s * .84, s * .5, s * .9)
    path.cubicTo(s * .32, s * .84, s * .18, s * .72, s * .18, s * .5)
    path.lineTo(s * .18, s * .24)
    path.closeSubpath()
    p.drawPath(path)


def i_book(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.07)
    p.drawPolyline(QPolygonF([QPointF(s * .5, s * .26), QPointF(s * .5, s * .84)]))
    p.drawPolyline(QPolygonF([QPointF(s * .5, s * .26), QPointF(s * .84, s * .2),
                              QPointF(s * .84, s * .74), QPointF(s * .5, s * .84)]))
    p.drawPolyline(QPolygonF([QPointF(s * .5, s * .26), QPointF(s * .16, s * .2),
                              QPointF(s * .16, s * .74), QPointF(s * .5, s * .84)]))
    _ = c


def i_sliders(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawLine(QPointF(s * .2, s * .32), QPointF(s * .8, s * .32))
    p.drawLine(QPointF(s * .2, s * .66), QPointF(s * .8, s * .66))
    p.setBrush(QBrush(QColor(c)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(QPointF(s * .64, s * .32), s * .07, s * .07)
    p.drawEllipse(QPointF(s * .36, s * .66), s * .07, s * .07)


def i_keyboard(p: QPainter, s: float) -> None:
    c = p.pen().color().name()
    _pen(p, c, s * 0.075)
    p.drawRoundedRect(QRectF(s * .14, s * .32, s * .72, s * .40), s * .08, s * .08)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(c)))
    for row in range(2):
        y = s * (.46 + row * .13)
        for col in range(4):
            p.drawRoundedRect(
                QRectF(s * (.24 + col * .14), y, s * .07, s * .06), s * .02, s * .02)
    p.drawRoundedRect(QRectF(s * .32, s * .62, s * .36, s * .055), s * .02, s * .02)


ICONS: Dict[str, Painter] = {
    "home": i_home,
    "cube": i_cube,
    "package": i_package,
    "coffee": i_coffee,
    "gear": i_gear,
    "terminal": i_terminal,
    "play": i_play,
    "download": i_download,
    "upload": i_upload,
    "folder": i_folder,
    "plus": i_plus,
    "trash": i_trash,
    "search": i_search,
    "refresh": i_refresh,
    "check": i_check,
    "close": i_close,
    "user": i_user,
    "globe": i_globe,
    "edit": i_edit,
    "copy": i_copy,
    "external": i_external,
    "cpu": i_cpu,
    "palette": i_palette,
    "grass": i_grass,
    "hammer": i_hammer,
    "layers": i_layers,
    "alert": i_alert,
    "info": i_info,
    "chevron-left": i_chevron_left,
    "chevron-right": i_chevron_right,
    "sun": i_sun,
    "link": i_link,
    "shield": i_shield,
    "book": i_book,
    "sliders": i_sliders,
    "keyboard": i_keyboard,
    "block": i_grass_block,
}


def make_icon(name: str, color: str = "#e6edf3", size: int = 20,
              ratio: float = 4.0) -> QIcon:
    fn = ICONS.get(name, i_info)
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    _pen(p, color, size * ratio / 100.0)
    fn(p, float(size))
    p.end()
    return QIcon(pm)


def make_pixmap(name: str, color: str = "#e6edf3", size: int = 20,
                ratio: float = 8.5) -> QPixmap:
    fn = ICONS.get(name, i_info)
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    _pen(p, color, size * ratio / 100.0)
    fn(p, float(size))
    p.end()
    return pm
