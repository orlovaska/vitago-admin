from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QWidget

from app.core.container import Container
from app.domain.enums import PageId
from app.domain.models import Resource
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import Card, DangerButton, GhostButton, PageHeader, PrimaryButton, confirm, notify_error, notify_info
from app.presentation.widgets.data_table import DataTable
from app.services.csv_export import export_csv


class ResourcesPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._resources: list[Resource] = []
        back = GhostButton("← Назад")
        back.clicked.connect(lambda: self.navigator.go(PageId.DASHBOARD))
        self._root.addWidget(back)
        self._root.addWidget(PageHeader("Управление ресурсами", "Изображения, аудио, JSON и PDF"))

        toolbar = Card()
        row = QHBoxLayout()
        self.unused_only = QCheckBox("Только неиспользованные")
        self.unused_only.stateChanged.connect(self._refresh_table)
        upload = PrimaryButton("Загрузить файлы")
        bulk = DangerButton("Удалить выбранные")
        export_btn = GhostButton("Экспорт в CSV")
        upload.clicked.connect(self._upload)
        bulk.clicked.connect(self._bulk_delete)
        export_btn.clicked.connect(self._export)
        row.addWidget(self.unused_only)
        row.addStretch()
        row.addWidget(upload)
        row.addWidget(bulk)
        row.addWidget(export_btn)
        toolbar.body.addLayout(row)
        self._root.addWidget(toolbar)

        self.table = DataTable(["ID", "Путь", "MIME", "Использование", "Создано"])
        self._root.addWidget(self.table)

    def on_enter(self, payload: dict[str, Any]) -> None:
        self.tasks.submit(self.container.resources.list_all, self._set_resources, lambda msg: notify_error(self, msg))

    def _set_resources(self, resources: list[Resource]) -> None:
        self._resources = resources
        self._refresh_table()

    def _visible(self) -> list[Resource]:
        if self.unused_only.isChecked():
            return [item for item in self._resources if not item.is_used]
        return self._resources

    def _refresh_table(self) -> None:
        rows = []
        ids = []
        for item in self._visible():
            created = item.created_at.strftime("%d.%m.%Y %H:%M") if item.created_at else ""
            usage = ", ".join(item.usages) if item.usages else "—"
            rows.append([str(item.resource_id), item.file_path, item.mime_type, usage, created])
            ids.append(item.resource_id)
        self.table.set_rows(rows, ids)

    def _upload(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы")
        if not files:
            return
        paths = [Path(item) for item in files]
        try:
            payload = self.container.resources.upload(paths)
            notify_info(self, payload.get("message") or "Файлы загружены")
            self.on_enter({})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _bulk_delete(self) -> None:
        selected = [int(item) for item in self.table.selected_ids() if item is not None]
        if not selected:
            notify_error(self, "Не выбрано ни одного ресурса")
            return
        unused = [
            item.resource_id
            for item in self._resources
            if item.resource_id in selected and not item.is_used
        ]
        if not unused:
            notify_error(self, "Все выбранные ресурсы используются и не могут быть удалены")
            return
        if not confirm(self, "Подтверждение массового удаления", f"Удалить {len(unused)} выбранных ресурсов?"):
            return
        try:
            payload = self.container.resources.bulk_delete(unused)
            notify_info(self, payload.get("message") or "Ресурсы удалены")
            self.on_enter({})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _export(self) -> None:
        items = self._visible()
        if not items:
            notify_error(self, "Нет ресурсов для экспорта")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", "resources.csv", "CSV (*.csv)")
        if not path:
            return
        rows = [
            [
                str(item.resource_id),
                item.file_path,
                item.mime_type,
                "; ".join(item.usages) if item.usages else "—",
                item.created_at.strftime("%d.%m.%Y %H:%M") if item.created_at else "",
            ]
            for item in items
        ]
        export_csv(Path(path), ["ID", "Путь", "MIME", "Использование", "Создано"], rows)
        notify_info(self, f"Экспортировано ресурсов: {len(items)}")
