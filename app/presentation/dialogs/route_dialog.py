from __future__ import annotations

from PyQt5.QtWidgets import QDialogButtonBox, QScrollArea, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.models import Resource, RouteForm
from app.presentation.dialogs.job_dialog import JobDialog
from app.presentation.forms.route_form import RouteFormWidget
from app.presentation.widgets.common import notify_error


class RouteDialog(JobDialog):
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
        self._loaded = False
        self.setWindowTitle("Редактировать маршрут" if route_id else "Добавить маршрут")
        self.resize(720, 760)
        self.form = RouteFormWidget()
        self.form.set_resources(resources)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._route_id and not self._loaded:
            self._loaded = True
            self.run_job(
                lambda: self._container.routes.get(self._route_id),
                self.form.set_form,
                busy_text="Загрузка маршрута…",
            )

    def _save(self) -> None:
        errors = self.form.errors()
        if errors:
            notify_error(self, "Заполните обязательные поля: " + ", ".join(errors))
            return
        form: RouteForm = self.form.to_form()
        route_id = self._route_id

        def work() -> None:
            if route_id:
                self._container.routes.update(route_id, form)
            else:
                self._container.routes.create(self._application_id, form)

        self.run_job(work, lambda _: self.accept())
