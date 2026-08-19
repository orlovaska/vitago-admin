from __future__ import annotations

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.models import AppVersion
from app.presentation.widgets.common import notify_error


class VersionDialog(QDialog):
    def __init__(
        self,
        container: Container,
        application_id: int,
        latest: AppVersion | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._application_id = application_id
        self._latest = latest
        self.setWindowTitle("Добавить версию")
        self.resize(420, 240)
        self.major = QSpinBox()
        self.minor = QSpinBox()
        self.patch = QSpinBox()
        for box in (self.major, self.minor, self.patch):
            box.setMaximum(999)
        self.major.setValue(1)
        self.release_notes = QLineEdit()
        form = QFormLayout()
        form.addRow("Major", self.major)
        form.addRow("Minor", self.minor)
        form.addRow("Patch", self.patch)
        form.addRow("Release Notes", self.release_notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _save(self) -> None:
        major, minor, patch = self.major.value(), self.minor.value(), self.patch.value()
        if self._latest:
            current = (major, minor, patch)
            latest = self._latest.as_tuple()
            if current <= latest:
                notify_error(self, f"Версия должна быть строго больше последней: {self._latest.label}")
                return
        try:
            self._container.applications.create_version(
                self._application_id,
                major,
                minor,
                patch,
                self.release_notes.text().strip() or None,
            )
            self.accept()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
