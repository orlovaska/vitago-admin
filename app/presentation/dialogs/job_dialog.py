from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QWidget

from app.presentation.widgets.common import BusyOverlay, notify_error
from app.presentation.widgets.resource_picker import ResourcePicker
from app.presentation.workers import TaskRunner


class JobDialog(QDialog):
    """Диалог с фоновыми запросами к API и корректным закрытием превью."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tasks = TaskRunner(self)
        self._busy = BusyOverlay(self)
        self.tasks.busy_changed.connect(self._on_busy)

    def _on_busy(self, busy: bool, text: str) -> None:
        if busy:
            self._busy.show_busy(text)
            return
        self._busy.hide_busy()

    def run_job(self, fn, on_success, *, busy_text: str = "Сохранение…") -> None:
        self.tasks.submit(fn, on_success, lambda msg: notify_error(self, msg), busy_text=busy_text)

    def done(self, result: int) -> None:  # type: ignore[override]
        self.tasks.abandon()
        for picker in self.findChildren(ResourcePicker):
            picker.shutdown()
        super().done(result)
