from __future__ import annotations

from pathlib import Path

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QFileDialog, QGroupBox, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from app.presentation.widgets.common import GhostButton, notify_info


class JsonExample(QGroupBox):
    """Пример JSON у любого импорта: просмотр, копирование и сохранение файла."""

    def __init__(
        self,
        title: str,
        text: str,
        filename: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent)
        self._text = text
        self._filename = filename

        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setPlainText(text)
        preview.setMinimumHeight(140)
        preview.setMaximumHeight(220)

        copy = GhostButton("Копировать")
        save = GhostButton("Сохранить пример")
        copy.clicked.connect(self._copy)
        save.clicked.connect(self._save)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(copy)
        actions_layout.addWidget(save)
        actions_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(preview)
        layout.addWidget(actions)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._text)
        notify_info(self, "Пример скопирован")

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить пример", self._filename, "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(self._text, encoding="utf-8")
        notify_info(self, "Пример сохранен")
