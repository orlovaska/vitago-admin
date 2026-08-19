from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.container import Container
from app.domain.models import Resource
from app.presentation.forms.application_form import ApplicationForm
from app.presentation.forms.point_form import PointFormWidget
from app.presentation.forms.route_form import RouteFormWidget
from app.presentation.widgets.common import PrimaryButton, notify_error, notify_info


class CloneWizardDialog(QDialog):
    """Шаблонный метод: шаги создания клона приложения."""

    def __init__(self, container: Container, resources: list[Resource], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._resources = resources
        self._step = 0
        self._app_id: int | None = None
        self._route_id: int | None = None
        self.setWindowTitle("Добавление клона")
        self.resize(760, 820)

        self.app_form = ApplicationForm()
        self.app_form.set_resources(resources)
        self.app_form.set_support_url(container.settings.default_support_chat_url)
        self.route_form = RouteFormWidget()
        self.route_form.set_resources(resources)
        self.point_form = PointFormWidget()
        self.point_form.set_resources(resources)
        self.major = QSpinBox()
        self.minor = QSpinBox()
        self.patch = QSpinBox()
        self.major.setMaximum(999)
        self.minor.setMaximum(999)
        self.patch.setMaximum(999)
        self.major.setValue(1)
        self.release_notes = QLineEdit()
        version_page = QWidget()
        version_layout = QFormLayout(version_page)
        version_layout.addRow("Major", self.major)
        version_layout.addRow("Minor", self.minor)
        version_layout.addRow("Patch", self.patch)
        version_layout.addRow("Release Notes", self.release_notes)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._wrap(self.app_form))
        self.stack.addWidget(self._wrap(self.route_form))
        self.stack.addWidget(self._wrap(self.point_form))
        self.stack.addWidget(self._wrap(version_page))

        self.hint = QLabel("Шаг 1 из 4: приложение")
        self.next_button = PrimaryButton("Далее")
        self.next_button.clicked.connect(self._next)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.hint)
        layout.addWidget(self.stack)
        layout.addWidget(self.next_button)
        layout.addWidget(buttons)

    def _wrap(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        return scroll

    def _next(self) -> None:
        try:
            if self._step == 0:
                errors = self.app_form.errors()
                if errors:
                    notify_error(self, "Заполните обязательные поля: " + ", ".join(errors))
                    return
                created = self._container.applications.create(self.app_form.to_payload())
                self._app_id = created.id
                notify_info(self, "Приложение успешно создано")
            elif self._step == 1:
                errors = self.route_form.errors()
                if errors:
                    notify_error(self, "Заполните обязательные поля: " + ", ".join(errors))
                    return
                if not self._app_id:
                    notify_error(self, "ID приложения не найден")
                    return
                self._route_id = self._container.routes.create(self._app_id, self.route_form.to_form())
                notify_info(self, "Маршрут успешно создан")
            elif self._step == 2:
                errors = self.point_form.errors()
                if errors:
                    notify_error(self, "\n".join(errors))
                    return
                if not self._route_id:
                    notify_error(self, "ID маршрута не найден")
                    return
                self._container.points.create(self._route_id, self.point_form.to_point(route_id=self._route_id))
                notify_info(self, "Точка успешно создана")
            else:
                if not self._app_id:
                    notify_error(self, "ID приложения не найден")
                    return
                self._container.applications.create_version(
                    self._app_id,
                    self.major.value(),
                    self.minor.value(),
                    self.patch.value(),
                    self.release_notes.text().strip() or None,
                )
                notify_info(self, "Клон успешно создан")
                self.accept()
                return
            self._step += 1
            self.stack.setCurrentIndex(self._step)
            titles = ("приложение", "маршрут", "первая точка", "версия")
            self.hint.setText(f"Шаг {self._step + 1} из 4: {titles[self._step]}")
            if self._step == 3:
                self.next_button.setText("Завершить")
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
