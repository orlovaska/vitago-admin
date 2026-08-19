from __future__ import annotations

from PyQt5.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLineEdit, QSpinBox, QTextEdit, QVBoxLayout, QWidget

from app.domain.enums import MimeType
from app.domain.models import Resource, RouteForm
from app.presentation.widgets.common import LabeledField
from app.presentation.widgets.resource_picker import ResourcePicker


class RouteFormWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.route_name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(90)
        self.city = QLineEdit()
        self.subtitle = QLineEdit()
        self.route_description = QLineEdit()
        self.amount = QSpinBox()
        self.amount.setMaximum(10_000_000)
        self.distance_text = QLineEdit()
        self.distance_description = QLineEdit()
        self.duration_text = QLineEdit()
        self.duration_description = QLineEdit()
        self.lat = QDoubleSpinBox()
        self.lon = QDoubleSpinBox()
        self.zoom = QDoubleSpinBox()
        self.lat.setRange(-90, 90)
        self.lon.setRange(-180, 180)
        self.zoom.setRange(0, 22)
        self.lat.setDecimals(6)
        self.lon.setDecimals(6)
        self.zoom.setDecimals(1)
        self.audio = ResourcePicker()
        self.path_json = ResourcePicker()
        self.carousel: list[ResourcePicker] = [ResourcePicker() for _ in range(5)]

        layout = QVBoxLayout(self)
        layout.addWidget(LabeledField("Название маршрута", self.route_name, "Например: «Пеший маршрут по Казани»"))
        layout.addWidget(LabeledField("Описание маршрута", self.description))
        row = QHBoxLayout()
        city_field = LabeledField("Город", self.city, "Например: «Казань»")
        amount_field = LabeledField("Сумма (в копейках)", self.amount, "59900 = 599 ₽")
        row.addWidget(city_field)
        row.addWidget(amount_field)
        layout.addLayout(row)
        layout.addWidget(LabeledField("Подзаголовок", self.subtitle))
        layout.addWidget(LabeledField("Заголовок блока с аудио", self.route_description))
        layout.addWidget(LabeledField("Текст расстояния", self.distance_text))
        layout.addWidget(LabeledField("Описание расстояния", self.distance_description))
        layout.addWidget(LabeledField("Текст длительности маршрута", self.duration_text))
        layout.addWidget(LabeledField("Описание длительности маршрута", self.duration_description))
        coords = QHBoxLayout()
        coords.addWidget(LabeledField("Широта (центр)", self.lat))
        coords.addWidget(LabeledField("Долгота (центр)", self.lon))
        coords.addWidget(LabeledField("Начальный зум", self.zoom))
        layout.addLayout(coords)
        layout.addWidget(LabeledField("Аудио-ресурс", self.audio))
        layout.addWidget(LabeledField("JSON-ресурс маршрута", self.path_json))
        for index, picker in enumerate(self.carousel, start=1):
            layout.addWidget(LabeledField(f"Изображение карусели {index}", picker))

    def set_resources(self, resources: list[Resource]) -> None:
        self.audio.set_resources(resources, MimeType.MP3)
        self.path_json.set_resources(resources, MimeType.JSON)
        for picker in self.carousel:
            picker.set_resources(resources, MimeType.PNG)

    def set_form(self, form: RouteForm) -> None:
        self.route_name.setText(form.route_name)
        self.description.setPlainText(form.description)
        self.city.setText(form.city)
        self.subtitle.setText(form.subtitle or "")
        self.route_description.setText(form.route_description or "")
        self.amount.setValue(form.amount)
        self.distance_text.setText(form.distance_text or "")
        self.distance_description.setText(form.distance_description or "")
        self.duration_text.setText(form.route_duration_text or "")
        self.duration_description.setText(form.route_duration_description or "")
        self.lat.setValue(form.map_initial_latitude or 0)
        self.lon.setValue(form.map_initial_longitude or 0)
        self.zoom.setValue(form.map_initial_zoom or 0)
        self.audio.set_value(form.audio_resource_id)
        self.path_json.set_value(form.route_path_json_resource_id)
        for index, picker in enumerate(self.carousel):
            value = form.route_image_resource_ids[index] if index < len(form.route_image_resource_ids) else None
            picker.set_value(value)

    def to_form(self) -> RouteForm:
        images = [picker.value() for picker in self.carousel if picker.value()]
        return RouteForm(
            route_name=self.route_name.text().strip(),
            description=self.description.toPlainText().strip(),
            city=self.city.text().strip(),
            subtitle=self.subtitle.text().strip() or None,
            route_description=self.route_description.text().strip() or None,
            amount=self.amount.value(),
            distance_text=self.distance_text.text().strip() or None,
            distance_description=self.distance_description.text().strip() or None,
            route_duration_text=self.duration_text.text().strip() or None,
            route_duration_description=self.duration_description.text().strip() or None,
            map_initial_latitude=self.lat.value() or None,
            map_initial_longitude=self.lon.value() or None,
            map_initial_zoom=self.zoom.value() or None,
            audio_resource_id=self.audio.value(),
            route_path_json_resource_id=self.path_json.value(),
            route_image_resource_ids=images,
        )

    def errors(self) -> list[str]:
        missing = []
        if not self.route_name.text().strip():
            missing.append("Название маршрута")
        if not self.description.toPlainText().strip():
            missing.append("Описание маршрута")
        if not self.city.text().strip():
            missing.append("Город")
        return missing
