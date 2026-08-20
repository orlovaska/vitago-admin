from __future__ import annotations

from PyQt5.QtCore import QSettings, QSize
from PyQt5.QtWidgets import QDialog, QWidget

from app.presentation.widgets.common import BusyOverlay, notify_error
from app.presentation.widgets.resource_picker import ResourcePicker
from app.presentation.workers import TaskRunner

_SETTINGS_ORG = "Vitago"
_SETTINGS_APP = "AdminPanel"
_SIZE_PREFIX = "dialogSize/"
_MIN_SIZE = QSize(320, 240)


class JobDialog(QDialog):
    """Диалог с фоновыми запросами к API и корректным закрытием превью."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.tasks = TaskRunner(self)
        self._busy = BusyOverlay(self)
        self._size_restored = False
        self.tasks.busy_changed.connect(self._on_busy)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._size_restored:
            return
        self._size_restored = True
        stored = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(self._size_key())
        if isinstance(stored, QSize) and stored.width() >= _MIN_SIZE.width() and stored.height() >= _MIN_SIZE.height():
            self.resize(stored)

    def _on_busy(self, busy: bool, text: str) -> None:
        if busy:
            self._busy.show_busy(text)
            return
        self._busy.hide_busy()

    def run_job(self, fn, on_success, *, busy_text: str = "Сохранение…") -> None:
        self.tasks.submit(fn, on_success, lambda msg: notify_error(self, msg), busy_text=busy_text)

    def done(self, result: int) -> None:  # type: ignore[override]
        QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(self._size_key(), self.size())
        self.tasks.abandon()
        for picker in self.findChildren(ResourcePicker):
            picker.shutdown()
        super().done(result)

    def _size_key(self) -> str:
        return _SIZE_PREFIX + type(self).__name__
