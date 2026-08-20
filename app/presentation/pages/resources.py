from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QWidget

from app.core.container import Container
from app.core.log import get_logger
from app.domain.models import Resource
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import Card, DangerButton, GhostButton, PageHeader, PrimaryButton, confirm_delete, notify_error, notify_info
from app.presentation.widgets.data_table import DataTable
from app.services.csv_export import export_csv


class ResourcesPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._resources: list[Resource] = []
        self._root.addWidget(PageHeader("Управление ресурсами", "Изображения, аудио, JSON и PDF"))

        toolbar = Card()
        row = QHBoxLayout()
        self.unused_only = QCheckBox("Только неиспользованные")
        self.unused_only.stateChanged.connect(self._refresh_table)
        upload = PrimaryButton("Загрузить файлы")
        bulk = DangerButton("Удалить выбранные")
        export_btn = GhostButton("Экспорт в CSV")
        download = GhostButton("Скачать выбранные")
        upload.clicked.connect(self._upload)
        bulk.clicked.connect(self._bulk_delete)
        export_btn.clicked.connect(self._export)
        download.clicked.connect(self._download)
        row.addWidget(self.unused_only)
        row.addStretch()
        row.addWidget(download)
        row.addWidget(upload)
        row.addWidget(bulk)
        row.addWidget(export_btn)
        toolbar.body.addLayout(row)
        self._root.addWidget(toolbar)

        self.table = DataTable(["ID", "Путь", "MIME", "Использование", "Создано"], name="resources")
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
        self.tasks.submit(
            lambda: self.container.resources.upload(paths),
            lambda payload: self._after_upload(payload),
            lambda msg: notify_error(self, msg),
            busy_text="Загрузка файлов…",
        )

    def _after_upload(self, payload: dict) -> None:
        notify_info(self, payload.get("message") or "Файлы загружены")
        self.on_enter({})

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
        if not confirm_delete(self, f"Удалить {len(unused)} выбранных ресурсов?"):
            return
        self.tasks.submit(
            lambda: self.container.resources.bulk_delete(unused),
            lambda payload: self._after_bulk_delete(payload),
            lambda msg: notify_error(self, msg),
            busy_text="Удаление…",
        )

    def _after_bulk_delete(self, payload: dict) -> None:
        notify_info(self, payload.get("message") or "Ресурсы удалены")
        self.on_enter({})

    def _download(self) -> None:
        selected = {int(item) for item in self.table.selected_ids() if item is not None}
        items = [r for r in self._resources if r.resource_id in selected]
        if not items:
            notify_error(self, "Не выбрано ни одного ресурса")
            return
        target_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения")
        if not target_dir:
            return
        dest = Path(target_dir)

        def work() -> tuple[int, int]:
            ok, failed = 0, 0
            for item in items:
                try:
                    data, _ = self.container.resources.download(item.resource_id)
                    (dest / item.file_name).write_bytes(data)
                    ok += 1
                except Exception:  # noqa: BLE001
                    get_logger(__name__).exception("Не удалось скачать ресурс #%s", item.resource_id)
                    failed += 1
            return ok, failed

        def done(result: tuple[int, int]) -> None:
            ok, failed = result
            msg = f"Скачано: {ok}"
            if failed:
                msg += f", ошибок: {failed}"
            notify_info(self, msg)

        self.tasks.submit(work, done, lambda msg: notify_error(self, msg), busy_text="Скачивание…")

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
