from __future__ import annotations

import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.domain.enums import MimeType
from app.domain.models import Point, Resource
from app.presentation.widgets.common import (
    GhostButton,
    LabeledField,
    NoWheelDoubleSpinBox,
    NoWheelSpinBox,
    notify_error,
)
from app.presentation.widgets.resource_picker import ResourcePicker
from app.services.transcript_align import parse_cues_json


class PointFormWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(80)
        self.address = QLineEdit()
        self.working_hours = QLineEdit()
        self.lat = NoWheelDoubleSpinBox()
        self.lon = NoWheelDoubleSpinBox()
        self.lat.setRange(-90, 90)
        self.lon.setRange(-180, 180)
        self.lat.setDecimals(6)
        self.lon.setDecimals(6)
        self.yandex = QLineEdit()
        self.google = QLineEdit()
        self.two_gis = QLineEdit()
        self.is_free = QCheckBox("Бесплатная точка")
        self.level = NoWheelSpinBox()
        self.level.setMinimum(1)
        self.level.setMaximum(1000)
        self.radius = NoWheelSpinBox()
        self.radius.setMaximum(10_000)
        self.radius.setValue(40)
        self.image = ResourcePicker()
        self.marker = ResourcePicker()
        self.locked = ResourcePicker()
        self.audio = ResourcePicker()

        self.transcript = QPlainTextEdit()
        self.transcript.setPlaceholderText("Сплошной текст транскрипта (как в TXT)")
        self.transcript.setMinimumHeight(100)
        self.transcript.setMaximumHeight(160)
        self.transcript.textChanged.connect(self._refresh_transcript_title)

        self.cues_json = QPlainTextEdit()
        self.cues_json.setPlaceholderText('JSON таймкодов: [ { "start": 0.0, "end": 0.4, "text": "слово" }, … ]')
        self.cues_json.setMinimumHeight(140)
        self.cues_json.setMaximumHeight(220)
        self.cues_json.textChanged.connect(self._refresh_transcript_title)

        self.cues_status = QLabel()
        self.cues_status.setObjectName("muted")
        self.cues_status.setWordWrap(True)

        load_transcript = GhostButton("Загрузить текст…")
        load_cues = GhostButton("Загрузить JSON…")
        clear_cues = GhostButton("Очистить JSON")
        load_transcript.clicked.connect(self._load_transcript_file)
        load_cues.clicked.connect(self._load_cues_file)
        clear_cues.clicked.connect(self._clear_cues)

        transcript_actions = QHBoxLayout()
        transcript_actions.setContentsMargins(0, 0, 0, 0)
        transcript_actions.addWidget(load_transcript)
        transcript_actions.addWidget(load_cues)
        transcript_actions.addWidget(clear_cues)
        transcript_actions.addStretch()

        self._transcript_body = QWidget()
        body_layout = QVBoxLayout(self._transcript_body)
        body_layout.setContentsMargins(0, 8, 0, 0)
        body_layout.setSpacing(8)
        body_layout.addWidget(LabeledField("Текст", self.transcript))
        body_layout.addWidget(LabeledField("Таймкоды (JSON)", self.cues_json))
        body_layout.addWidget(self.cues_status)
        body_layout.addLayout(transcript_actions)

        self.transcript_group = QGroupBox("Транскрипция")
        self.transcript_group.setCheckable(True)
        self.transcript_group.setChecked(False)
        self.transcript_group.setFlat(False)
        group_layout = QVBoxLayout(self.transcript_group)
        group_layout.addWidget(self._transcript_body)
        self.transcript_group.toggled.connect(self._on_transcript_toggled)
        self._transcript_body.setVisible(False)

        layout = QVBoxLayout(self)
        layout.addWidget(LabeledField("Название точки", self.name))
        layout.addWidget(LabeledField("Описание", self.description))
        layout.addWidget(LabeledField("Адрес", self.address))
        layout.addWidget(LabeledField("Часы работы", self.working_hours))
        coords = QHBoxLayout()
        coords.addWidget(LabeledField("Широта", self.lat))
        coords.addWidget(LabeledField("Долгота", self.lon))
        layout.addLayout(coords)
        layout.addWidget(LabeledField("Ссылка на Яндекс.Карты", self.yandex))
        layout.addWidget(LabeledField("Ссылка на Google Maps", self.google))
        layout.addWidget(LabeledField("Ссылка на 2ГИС", self.two_gis))
        layout.addWidget(self.is_free)
        settings = QHBoxLayout()
        settings.addWidget(LabeledField("Уровень", self.level))
        settings.addWidget(LabeledField("Радиус автовоспроизведения (м)", self.radius))
        layout.addLayout(settings)
        layout.addWidget(LabeledField("Изображение точки", self.image))
        layout.addWidget(LabeledField("Маркер на карте", self.marker))
        layout.addWidget(LabeledField("Заблокированный маркер", self.locked))
        layout.addWidget(LabeledField("Аудио-ресурс", self.audio))
        layout.addWidget(self.transcript_group)
        self._refresh_transcript_title()

    def _on_transcript_toggled(self, checked: bool) -> None:
        self._transcript_body.setVisible(checked)
        # Checkable QGroupBox иначе оставляет детей disabled при collapse.
        self._transcript_body.setEnabled(True)
        for child in self._transcript_body.findChildren(QWidget):
            child.setEnabled(True)

    def set_resources(self, resources: list[Resource]) -> None:
        self.image.set_resources(resources, MimeType.PNG)
        self.marker.set_resources(resources, MimeType.PNG)
        self.locked.set_resources(resources, MimeType.PNG)
        self.audio.set_resources(resources, MimeType.MP3)

    def set_point(self, point: Point) -> None:
        self.name.setText(point.name)
        self.description.setPlainText(point.description or "")
        self.address.setText(point.address or "")
        self.working_hours.setText(point.working_hours or "")
        self.lat.setValue(point.latitude)
        self.lon.setValue(point.longitude)
        self.yandex.setText(point.yandex_map_link)
        self.google.setText(point.google_map_link)
        self.two_gis.setText(point.two_gis_map_link)
        self.is_free.setChecked(point.is_free)
        self.level.setValue(point.level)
        self.radius.setValue(point.auto_play_radius_m)
        self.image.set_value(point.image_resource_id)
        self.marker.set_value(point.marker_resource_id)
        self.locked.set_value(point.locked_marker_resource_id)
        self.audio.set_value(point.audio_resource_id)
        self.transcript.setPlainText(point.transcript or "")
        if point.transcript_cues is not None:
            self.cues_json.setPlainText(json.dumps(list(point.transcript_cues), ensure_ascii=False, indent=2))
        else:
            self.cues_json.clear()
        self._refresh_transcript_title()

    def to_point(self, point_id: int | None = None, route_id: int | None = None) -> Point:
        return Point(
            id=point_id,
            travel_route_id=route_id,
            name=self.name.text().strip(),
            description=self.description.toPlainText().strip() or None,
            address=self.address.text().strip() or None,
            working_hours=self.working_hours.text().strip() or None,
            latitude=self.lat.value(),
            longitude=self.lon.value(),
            yandex_map_link=self.yandex.text().strip(),
            google_map_link=self.google.text().strip(),
            two_gis_map_link=self.two_gis.text().strip(),
            is_free=self.is_free.isChecked(),
            level=self.level.value(),
            auto_play_radius_m=self.radius.value(),
            image_resource_id=self.image.value(),
            marker_resource_id=self.marker.value(),
            locked_marker_resource_id=self.locked.value(),
            audio_resource_id=self.audio.value(),
            transcript=self.transcript.toPlainText().strip() or None,
            transcript_cues=self._cues_from_editor(),
        )

    def errors(self) -> list[str]:
        errors: list[str] = []
        if not self.name.text().strip():
            errors.append("Название точки обязательно")
        for label, field in (
            ("Яндекс.Карты", self.yandex),
            ("Google Maps", self.google),
            ("2ГИС", self.two_gis),
        ):
            value = field.text().strip()
            if not value:
                errors.append(f"Ссылка на {label} обязательна")
            elif not value.startswith(("http://", "https://")):
                errors.append(f"Ссылка на {label} должна начинаться с http:// или https://")
        if not self.image.value():
            errors.append("Изображение точки обязательно")
        if not self.marker.value():
            errors.append("Маркер на карте обязателен")
        if not self.locked.value():
            errors.append("Заблокированный маркер обязателен")
        if not self.audio.value():
            errors.append("Аудио-ресурс обязателен")
        raw = self.cues_json.toPlainText().strip()
        if raw:
            try:
                parse_cues_json(raw)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"JSON таймкодов: {exc}")
        return errors

    def _cues_from_editor(self) -> tuple[dict, ...] | None:
        raw = self.cues_json.toPlainText().strip()
        if not raw:
            return None
        return tuple(parse_cues_json(raw))

    def _load_transcript_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Транскрипт", "", "Текст (*.txt);;Все файлы (*.*)")
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except OSError as exc:
            notify_error(self, str(exc))
            return
        self.transcript.setPlainText(text)
        if not self.transcript_group.isChecked():
            self.transcript_group.setChecked(True)

    def _load_cues_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "JSON таймкодов", "", "JSON (*.json);;Все файлы (*.*)")
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
            cues = parse_cues_json(raw)
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
            return
        self.cues_json.setPlainText(json.dumps(cues, ensure_ascii=False, indent=2))
        if not self.transcript_group.isChecked():
            self.transcript_group.setChecked(True)
        self._refresh_transcript_title()

    def _clear_cues(self) -> None:
        self.cues_json.clear()
        self._refresh_transcript_title()

    def _refresh_transcript_title(self) -> None:
        raw = self.cues_json.toPlainText().strip()
        text = self.transcript.toPlainText().strip()
        if not raw:
            status = "таймкодов нет"
            detail = "JSON пустой — таймкодов нет"
        else:
            try:
                cues = parse_cues_json(raw)
                status = f"{len(cues)} таймкодов"
                detail = f"JSON валиден: {len(cues)} слов с start/end"
            except Exception as exc:  # noqa: BLE001
                status = "ошибка JSON"
                detail = f"JSON невалиден: {exc}"
        text_bit = "есть текст" if text else "текста нет"
        self.transcript_group.setTitle(f"Транскрипция — {text_bit}, {status}")
        self.cues_status.setText(detail)
