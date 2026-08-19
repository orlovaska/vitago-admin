from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QScrollArea, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.models import Point, Resource
from app.presentation.forms.point_form import PointFormWidget
from app.presentation.widgets.common import notify_error


class PointDialog(QDialog):
    def __init__(
        self,
        container: Container,
        resources: list[Resource],
        route_id: int,
        point: Point | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._route_id = route_id
        self._point = point
        self.setWindowTitle("Редактировать точку" if point else "Создать точку")
        self.resize(680, 760)
        self.form = PointFormWidget()
        self.form.set_resources(resources)
        if point:
            self.form.set_point(point)
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
            notify_error(self, "\n".join(errors))
            return
        point = self.form.to_point(
            point_id=self._point.id if self._point else None,
            route_id=self._route_id,
        )
        try:
            if self._point and self._point.id:
                self._container.points.update(self._point.id, point)
            else:
                self._container.points.create(self._route_id, point)
            self.accept()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
