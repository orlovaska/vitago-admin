from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QWidget

from app.core.container import Container
from app.domain.models import ServerResource, ServerResourcesState
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import Card, GhostButton, PageHeader, PrimaryButton, notify_error, notify_info
from app.presentation.widgets.data_table import DataTable


def _format_size(size: int | None) -> str:
    if size is None:
        return "—"
    value = float(size)
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if value < 1024 or unit == "ГБ":
            if unit == "Б":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} Б"


class ServerResourcesPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._items: tuple[ServerResource, ...] = ()
        self._root.addWidget(
            PageHeader(
                "Ресурсы на сервере",
                "Файлы в контейнере app и пути из БД. Список снимается по SSH, не через API.",
            )
        )

        toolbar = Card()
        row = QHBoxLayout()
        self.missing_only = QCheckBox("Нет на диске")
        self.orphan_only = QCheckBox("Нет в БД")
        self.missing_only.stateChanged.connect(self._refresh_table)
        self.orphan_only.stateChanged.connect(self._refresh_table)
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        refresh = GhostButton("Обновить")
        refresh.clicked.connect(self._reload)
        self.backup_button = PrimaryButton("Сделать бэкап")
        self.backup_button.clicked.connect(self._backup)
        row.addWidget(self.missing_only)
        row.addWidget(self.orphan_only)
        row.addStretch()
        row.addWidget(self.counter)
        row.addWidget(self.backup_button)
        row.addWidget(refresh)
        self.backup_label = QLabel()
        self.backup_label.setObjectName("muted")
        self.backup_label.setWordWrap(True)
        toolbar.body.addLayout(row)
        toolbar.body.addWidget(self.backup_label)
        self._root.addWidget(toolbar)

        self.table = DataTable(["Путь", "Размер", "Изменён", "На диске", "В БД"], name="server_resources")
        self._root.addWidget(self.table)

    def on_enter(self, payload: dict[str, Any]) -> None:
        self._reload()

    def _reload(self) -> None:
        self.tasks.submit(
            self.container.server_resources.list_files,
            self._set_state,
            lambda msg: notify_error(self, msg),
            busy_text="Загрузка по SSH…",
        )

    def _backup(self) -> None:
        self.backup_button.setEnabled(False)
        self.backup_label.setText("Создание и скачивание архива…")
        self.tasks.submit(
            self.container.server_resources.create_backup_and_download,
            self._on_backup_downloaded,
            self._on_backup_error,
            busy_text="Бэкап и скачивание…",
        )

    def _on_backup_downloaded(self, result: tuple[str, Path]) -> None:
        note, local = result
        self.backup_button.setEnabled(True)
        text = f"{note}. Сохранён на ПК: {local}"
        self.backup_label.setText(text)
        notify_info(self, text)

    def _on_backup_error(self, message: str) -> None:
        self.backup_button.setEnabled(True)
        self.backup_label.setText(message)
        notify_error(self, message)

    def _set_state(self, state: ServerResourcesState) -> None:
        self._items = state.items
        if state.reason:
            self.counter.setText(state.reason)
            self.backup_label.setText("")
            self.backup_button.setEnabled(False)
            self._refresh_table()
            return
        self.backup_button.setEnabled(True)
        self.backup_label.setText(state.backup_note)
        folder = f"Каталог: {state.folder}. " if state.folder else ""
        on_disk = sum(1 for item in self._items if item.on_disk)
        in_db = sum(1 for item in self._items if item.in_db)
        missing = sum(1 for item in self._items if item.in_db and not item.on_disk)
        orphans = sum(1 for item in self._items if item.on_disk and not item.in_db)
        self.counter.setText(
            f"{folder}Всего: {len(self._items)}. На диске: {on_disk}. В БД: {in_db}. Нет на диске: {missing}. Нет в БД: {orphans}"
        )
        self._refresh_table()

    def _visible(self) -> list[ServerResource]:
        items = list(self._items)
        if self.missing_only.isChecked():
            items = [item for item in items if item.in_db and not item.on_disk]
        if self.orphan_only.isChecked():
            items = [item for item in items if item.on_disk and not item.in_db]
        return items

    def _refresh_table(self) -> None:
        rows = []
        ids = []
        for item in self._visible():
            rows.append(
                [
                    item.path,
                    _format_size(item.size),
                    item.modified_at or "—",
                    "да" if item.on_disk else "нет",
                    "да" if item.in_db else "нет",
                ]
            )
            ids.append(item.path)
        self.table.set_rows(rows, ids)
