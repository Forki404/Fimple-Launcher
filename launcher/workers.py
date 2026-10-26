from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6.QtCore import QThread, Signal

from . import utils


def _where_failed() -> str:
    tb = traceback.extract_tb(sys.exc_info()[2])
    for frame in reversed(tb):
        name = Path(frame.filename)
        if name.parent.name in ("launcher", "minecraft_launcher_lib"):
            continue
        return f"{name.name}:{frame.lineno} — {frame.line or ''}".strip(" —")
    if tb:
        f = tb[-1]
        return f"{Path(f.filename).name}:{f.lineno}"
    return ""


class Ctx:
    def __init__(self, worker: "Worker") -> None:
        self._w = worker

    def status(self, text: str) -> None:
        self._w.status.emit(str(text))

    def progress(self, downloaded: int, total: int, percent: int) -> None:
        self._w.progress.emit(int(downloaded), int(total), int(percent))

    def log(self, text: str) -> None:
        self._w.log_line.emit(str(text))

    @property
    def is_cancelled(self) -> bool:
        return self._w.isInterruptionRequested()

    def check_cancelled(self) -> None:
        if self._w.isInterruptionRequested():
            raise RuntimeError("Операция отменена")


class Worker(QThread):
    status = Signal(str)
    progress = Signal(int, int, int)
    log_line = Signal(str)
    result = Signal(object)
    error = Signal(str)
    done = Signal()

    def __init__(self, fn: Callable[[Ctx], Any], name: str = "worker",
                 parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.ctx = Ctx(self)
        self.setObjectName(name)

    def run(self) -> None:
        try:
            res = self._fn(self.ctx)
            if not self.isInterruptionRequested():
                self.result.emit(res)
        except Exception as e:
            utils.log(f"{self.objectName()}: {e}", "ERROR")
            self.log_line.emit(traceback.format_exc())
            where = _where_failed()
            self.error.emit(f"{e}\n{where}" if where else str(e))
        finally:
            self.done.emit()


_ACTIVE: list = []


def is_alive(worker) -> bool:
    if worker is None:
        return False
    try:
        shiboken6 = __import__("shiboken6")
        if not shiboken6.isValid(worker):
            return False
    except Exception:
        pass
    try:
        return bool(worker.isRunning())
    except RuntimeError:
        return False


def background(fn: Callable[..., Any], on_result: Optional[Callable[[Any], None]] = None,
               on_error: Optional[Callable[[str], None]] = None,
               on_finish: Optional[Callable[[], None]] = None,
               parent=None) -> Worker:
    import inspect

    try:
        wants_ctx = bool(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        wants_ctx = True

    w = Worker(lambda ctx: fn(ctx) if wants_ctx else fn(), "background", parent)
    if on_result:
        w.result.connect(on_result)
    if on_error:
        w.error.connect(on_error)
    w.done.connect(w.deleteLater)
    w.finished.connect(lambda: _ACTIVE.remove(w) if w in _ACTIVE else None)
    if on_finish:
        w.finished.connect(on_finish)
    _ACTIVE.append(w)
    w.start()
    return w


def shutdown(timeout_ms: int = 4000) -> None:
    for w in list(_ACTIVE):
        try:
            w.requestInterruption()
        except RuntimeError:
            pass
    left = []
    for w in list(_ACTIVE):
        try:
            if not w.wait(timeout_ms):
                left.append(w.objectName())
        except RuntimeError:
            pass
    _ACTIVE.clear()
    if left:
        utils.log(f"Не завершились при выходе: {', '.join(left)}", "WARN")
