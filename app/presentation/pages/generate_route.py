from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import QFileDialog, QLabel, QPlainTextEdit

from app.core.container import Container
from app.domain.enums import PageId
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import ScrollPage
from app.presentation.widgets.common import Card, GhostButton, PageHeader, PrimaryButton, notify_error, notify_info
from app.services.geojson import convert_geojson_to_route


class GenerateRoutePage(ScrollPage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._points: list[dict[str, Any]] = []
        back = GhostButton("← Назад")
        back.clicked.connect(lambda: self.navigator.go(PageId.DASHBOARD))
        self.content_layout.addWidget(back)
        self.content_layout.addWidget(
            PageHeader("Генерация маршрута", "Загрузите GeoJSON и преобразуйте его в JSON точек")
        )
        card = Card()
        self.file_label = QLabel("Файл не выбран")
        pick = PrimaryButton("Выберите GeoJSON файл")
        generate = PrimaryButton("Сгенерировать маршрут")
        download = GhostButton("Скачать JSON")
        pick.clicked.connect(self._pick)
        generate.clicked.connect(self._generate)
        download.clicked.connect(self._download)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        card.body.addWidget(self.file_label)
        card.body.addWidget(pick)
        card.body.addWidget(generate)
        card.body.addWidget(download)
        card.body.addWidget(self.preview)
        self.content_layout.addWidget(card)
        self._file: Path | None = None

    def _pick(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "GeoJSON", "", "GeoJSON (*.geojson *.json)")
        if not path:
            return
        self._file = Path(path)
        self.file_label.setText(self._file.name)

    def _generate(self) -> None:
        if not self._file:
            notify_error(self, "Пожалуйста, выберите файл")
            return
        try:
            geojson = json.loads(self._file.read_text(encoding="utf-8"))
            points = convert_geojson_to_route(geojson)
            self._points = [
                {"latitude": item.latitude, "longitude": item.longitude, **({"name": item.name} if item.name else {})}
                for item in points
            ]
            self.preview.setPlainText(json.dumps(self._points, ensure_ascii=False, indent=2))
            notify_info(self, f"Маршрут успешно сгенерирован. Точек: {len(self._points)}")
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _download(self) -> None:
        if not self._points:
            notify_error(self, "Сначала сгенерируйте маршрут")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить JSON", "route.json", "JSON (*.json)")
        if not path:
            return
        Path(path).write_text(json.dumps(self._points, ensure_ascii=False, indent=2), encoding="utf-8")
        notify_info(self, "Файл сохранен")
