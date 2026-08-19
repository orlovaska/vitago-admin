from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import QObject, QThread, pyqtSignal

from app.core.exceptions import AppError


class TaskWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.finished.emit(result)
        except AppError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TaskRunner(QObject):
    """Запускает блокирующие вызовы репозиториев вне UI-потока."""

    busy_changed = pyqtSignal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._jobs: list[tuple[QThread, TaskWorker]] = []

    def submit(
        self,
        fn: Callable[..., Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None] | None = None,
        *args: Any,
        busy_text: str = "Загрузка с сервера…",
        **kwargs: Any,
    ) -> None:
        thread = QThread(self)
        worker = TaskWorker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        if on_error:
            worker.failed.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup(thread, worker))
        self._jobs.append((thread, worker))
        self.busy_changed.emit(True, busy_text)
        thread.start()

    def _cleanup(self, thread: QThread, worker: TaskWorker) -> None:
        self._jobs = [job for job in self._jobs if job[0] is not thread]
        worker.deleteLater()
        thread.deleteLater()
        if not self._jobs:
            self.busy_changed.emit(False, "")
