from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.container import Container
from app.presentation.widgets.common import notify_error


class PromocodeDialog(QDialog):
    def __init__(self, container: Container, route_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._route_id = route_id
        self.setWindowTitle("Создать промокод")
        self.code = QLineEdit()
        self.discount = QSpinBox()
        self.discount.setRange(0, 100)
        self.discount.setValue(50)
        self.show_after = QCheckBox("Показывать после оплаты")
        self.use_scheme = QCheckBox("Использовать custom scheme")
        self.is_active = QCheckBox("Активен")
        self.is_active.setChecked(True)
        form = QFormLayout()
        form.addRow("Код", self.code)
        form.addRow("Скидка, %", self.discount)
        form.addRow(self.show_after)
        form.addRow(self.use_scheme)
        form.addRow(self.is_active)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        if not self.code.text().strip():
            notify_error(self, "Укажите код промокода")
            return
        try:
            self._container.promocodes.create(
                {
                    "routeId": self._route_id,
                    "code": self.code.text().strip(),
                    "discountPercent": self.discount.value(),
                    "showAfterPayment": self.show_after.isChecked(),
                    "useCustomScheme": self.use_scheme.isChecked(),
                    "isActive": self.is_active.isChecked(),
                }
            )
            self.accept()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
