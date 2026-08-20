from __future__ import annotations

from PyQt5.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QLineEdit, QSpinBox, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.enums import AppStore
from app.domain.models import AppVersion
from app.presentation.dialogs.job_dialog import JobDialog
from app.presentation.widgets.common import notify_error


class VersionDialog(JobDialog):
    def __init__(
        self,
        container: Container,
        application_id: int,
        versions: tuple[AppVersion, ...] = (),
        parent: QWidget | None = None,
        store: AppStore | None = None,
    ) -> None:
        super().__init__(parent)
        self._container = container
        self._application_id = application_id
        self._versions = versions
        self.setWindowTitle("Добавить версию")
        self.resize(420, 280)
        self.store = QComboBox()
        for item in AppStore:
            self.store.addItem(item.label, item.value)
        if store is not None:
            index = self.store.findData(store.value)
            if index >= 0:
                self.store.setCurrentIndex(index)
        self.major = QSpinBox()
        self.minor = QSpinBox()
        self.patch = QSpinBox()
        for box in (self.major, self.minor, self.patch):
            box.setMaximum(999)
        self.major.setValue(1)
        self.release_notes = QLineEdit()
        form = QFormLayout()
        form.addRow("Стор", self.store)
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

    def _latest_for_store(self, store: AppStore) -> AppVersion | None:
        matched = [item for item in self._versions if item.store == store]
        if not matched:
            return None
        return max(matched, key=lambda item: item.as_tuple())

    def _save(self) -> None:
        store = AppStore.from_api(self.store.currentData())
        major, minor, patch = self.major.value(), self.minor.value(), self.patch.value()
        latest = self._latest_for_store(store)
        if latest and (major, minor, patch) <= latest.as_tuple():
            notify_error(self, f"Версия должна быть строго больше последней для этого стора: {latest.label}")
            return
        notes = self.release_notes.text().strip() or None
        app_id = self._application_id
        self.run_job(
            lambda: self._container.applications.create_version(app_id, major, minor, patch, notes, store),
            lambda _: self.accept(),
        )
