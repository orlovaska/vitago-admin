from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from app.core.exceptions import AppError
from app.core.log import get_logger

_LINGERING: list[tuple[QThread, TaskWorker]] = []


class TaskWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    progress = pyqtSignal(object)

    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        with_progress: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self._with_progress = with_progress

    def run(self) -> None:
        try:
            kwargs = dict(self._kwargs)
            if self._with_progress:
                kwargs["on_progress"] = self.progress.emit
            result = self._fn(*self._args, **kwargs)
            self.finished.emit(result)
        except AppError as exc:
            get_logger(__name__).warning("%s", exc)
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            get_logger(__name__).exception("Фоновая задача завершилась с ошибкой")
            self.failed.emit(str(exc))


class TaskRunner(QObject):
    """Запускает блокирующие вызовы репозиториев вне UI-потока."""

    busy_changed = pyqtSignal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._jobs: list[tuple[QThread, TaskWorker]] = []
        self._alive = True
        self.destroyed.connect(self.abandon)

    def abandon(self, *_args: Any) -> None:
        self._alive = False
        for thread, worker in list(self._jobs):
            try:
                worker.finished.disconnect()
                worker.failed.disconnect()
                worker.progress.disconnect()
            except TypeError:
                pass
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(lambda _=None, t=thread, w=worker: _release_lingering(t, w))
            _LINGERING.append((thread, worker))
        self._jobs.clear()

    def submit(
        self,
        fn: Callable[..., Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
        *args: Any,
        busy_text: str | None = "Загрузка с сервера…",
        on_progress: Callable[[Any], None] | None = None,
        **kwargs: Any,
    ) -> None:
        thread = QThread()
        worker = TaskWorker(fn, *args, with_progress=on_progress is not None, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self._emit_ok(on_success, result))
        worker.failed.connect(lambda msg: self._emit_err(on_error, msg))
        if on_progress is not None:
            worker.progress.connect(lambda payload: self._emit_progress(on_progress, payload))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup(thread, worker, notify_idle=busy_text is not None))
        self._jobs.append((thread, worker))
        if busy_text is not None:
            self.busy_changed.emit(True, busy_text)
        thread.start()

    def _emit_ok(self, callback: Callable[[Any], None], result: Any) -> None:
        if self._alive:
            callback(result)

    def _emit_err(self, callback: Callable[[str], None] | None, message: str) -> None:
        if self._alive and callback is not None:
            callback(message)

    def _emit_progress(self, callback: Callable[[Any], None], payload: Any) -> None:
        if self._alive:
            callback(payload)

    def _cleanup(self, thread: QThread, worker: TaskWorker, *, notify_idle: bool = True) -> None:
        self._jobs = [job for job in self._jobs if job[0] is not thread]
        worker.deleteLater()
        thread.deleteLater()
        if self._alive and not self._jobs and notify_idle:
            self.busy_changed.emit(False, "")


def _release_lingering(thread: QThread, worker: TaskWorker) -> None:
    _LINGERING[:] = [job for job in _LINGERING if job[0] is not thread]
    worker.deleteLater()
    thread.deleteLater()
