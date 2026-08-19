from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.container import Container
from app.core.env_file import (
    ENV_SCHEMA,
    env_path,
    is_schema_key,
    read_env,
    spec_for,
    validate_key,
)
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import ScrollPage
from app.presentation.widgets.common import (
    Card,
    DangerButton,
    GhostButton,
    InlineNotice,
    LabeledField,
    PageHeader,
    PrimaryButton,
)


class EnvPage(ScrollPage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._inputs: dict[str, QLineEdit] = {}
        self.content_layout.addWidget(
            PageHeader("Переменные .env", "Значения пишутся в файл и сразу применяются к API-клиенту")
        )

        self.path_label = QLabel()
        self.path_label.setObjectName("muted")
        self.path_label.setWordWrap(True)
        self.notice = InlineNotice()

        self.rows_host = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)

        self.new_key = QLineEdit()
        self.new_key.setPlaceholderText("NEW_VARIABLE")
        self.new_value = QLineEdit()
        self.new_value.setPlaceholderText("значение")
        add_button = GhostButton("Добавить")
        add_button.clicked.connect(self._add_variable)
        add_row = QWidget()
        add_layout = QHBoxLayout(add_row)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.addWidget(self.new_key)
        add_layout.addWidget(self.new_value)
        add_layout.addWidget(add_button)

        save = PrimaryButton("Сохранить")
        save.clicked.connect(self._save)

        card = Card()
        card.body.addWidget(self.path_label)
        card.body.addWidget(self.notice)
        card.body.addWidget(self.rows_host)
        card.body.addWidget(LabeledField("Новая переменная", add_row))
        card.body.addWidget(save, alignment=Qt.AlignLeft)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()

    def on_enter(self, payload: dict[str, Any]) -> None:
        self.notice.clear_notice()
        self.path_label.setText(f"Файл: {env_path()}")
        self._rebuild(read_env())

    def _rebuild(self, values: dict[str, str]) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._inputs.clear()

        ordered = [spec.key for spec in ENV_SCHEMA]
        ordered.extend(key for key in values if key not in ordered)
        for key in ordered:
            self._add_row(key, values.get(key, ""))

    def _add_row(self, key: str, value: str) -> None:
        field = QLineEdit(value)
        self._inputs[key] = field
        spec = spec_for(key)
        label = spec.label if spec else key
        hint = spec.hint if spec else ""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(LabeledField(label, field, hint), 1)
        if not is_schema_key(key):
            remove = DangerButton("Удалить")
            remove.clicked.connect(lambda _checked=False, name=key: self._remove_variable(name))
            layout.addWidget(remove, 0, Qt.AlignBottom)
        self.rows_layout.addWidget(row)

    def _add_variable(self) -> None:
        key = self.new_key.text().strip()
        error = validate_key(key)
        if error:
            self.notice.show_warning(error)
            return
        if key in self._inputs:
            self.notice.show_warning(f"Переменная {key} уже есть в списке")
            return
        self.notice.clear_notice()
        self._add_row(key, self.new_value.text())
        self.new_key.clear()
        self.new_value.clear()

    def _remove_variable(self, key: str) -> None:
        self._inputs.pop(key, None)
        self._rebuild(self._collect())

    def _collect(self) -> dict[str, str]:
        return {key: field.text().strip() for key, field in self._inputs.items()}

    def _save(self) -> None:
        values = self._collect()
        if "API_BASE_URL" in values:
            values["API_BASE_URL"] = values["API_BASE_URL"].rstrip("/")
        warnings: list[str] = []
        for spec in ENV_SCHEMA:
            if spec.default and not values.get(spec.key):
                values[spec.key] = spec.default
                warnings.append(f"{spec.label}: подставлено значение по умолчанию")
        timeout = values.get("API_TIMEOUT_SECONDS", "30")
        try:
            int(timeout)
        except ValueError:
            values["API_TIMEOUT_SECONDS"] = "30"
            warnings.append("Таймаут должен быть числом, подставлено 30")
        try:
            self.container.apply_env(values)
        except Exception as exc:  # noqa: BLE001
            self.notice.show_warning(str(exc))
            return
        self._rebuild(values)
        if warnings:
            self.notice.show_warning("Сохранено. " + "; ".join(warnings))
            return
        self.notice.show_warning("Сохранено, значения применяются без перезапуска")
