from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QComboBox, QWidget

from app.domain.enums import MimeType
from app.domain.models import Resource


class ResourcePicker(QComboBox):
    changed = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().setPlaceholderText("Поиск по имени файла...")
        self._resources: list[Resource] = []
        self._mime: MimeType | None = None
        self.currentIndexChanged.connect(self._emit)

    def set_resources(self, resources: list[Resource], mime: MimeType | None = None) -> None:
        current = self.value()
        self._resources = resources
        self._mime = mime
        self.blockSignals(True)
        self.clear()
        self.addItem("— не выбран —", None)
        filtered = [item for item in resources if mime is None or item.mime_type == mime.value]
        for item in filtered:
            self.addItem(f"{item.file_name}  (#{item.resource_id})", item.resource_id)
        self.set_value(current)
        self.blockSignals(False)

    def set_value(self, resource_id: int | None) -> None:
        if resource_id is None:
            self.setCurrentIndex(0)
            return
        index = self.findData(resource_id)
        self.setCurrentIndex(index if index >= 0 else 0)

    def value(self) -> int | None:
        data = self.currentData()
        return int(data) if data is not None else None

    def _emit(self) -> None:
        self.changed.emit(self.value())
