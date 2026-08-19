from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QScrollArea, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.models import Resource, RouteForm
from app.presentation.forms.route_form import RouteFormWidget
from app.presentation.widgets.common import notify_error


class RouteDialog(QDialog):
    def __init__(
        self,
        container: Container,
        resources: list[Resource],
        application_id: int,
        route_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._application_id = application_id
        self._route_id = route_id
        self.setWindowTitle("Редактировать маршрут" if route_id else "Добавить маршрут")
        self.resize(720, 760)
        self.form = RouteFormWidget()
        self.form.set_resources(resources)
        if route_id:
            try:
                self.form.set_form(container.routes.get(route_id))
            except Exception as exc:  # noqa: BLE001
                notify_error(self, str(exc))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    def _save(self) -> None:
        errors = self.form.errors()
        if errors:
            notify_error(self, "Заполните обязательные поля: " + ", ".join(errors))
            return
        form: RouteForm = self.form.to_form()
        try:
            if self._route_id:
                self._container.routes.update(self._route_id, form)
            else:
                self._container.routes.create(self._application_id, form)
            self.accept()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
