from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.container import Container
from app.core.env_file import (
    ENV_SCHEMA,
    HTTP_TIMEOUT_DEFAULT,
    HTTP_TIMEOUT_MAX,
    HTTP_TIMEOUT_MIN,
    clamp_http_timeout,
    env_path,
    read_env,
    spec_for,
)
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import (
    GhostButton,
    InlineNotice,
    LabeledField,
    PageHeader,
    PrimaryButton,
)


class EnvPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._inputs: dict[str, QLineEdit] = {}
        self._saved: dict[str, str] = {}

        self._root.addWidget(
            PageHeader("Переменные .env", "Локальные настройки этой админки, не секреты сервера")
        )

        self.path_label = QLabel()
        self.path_label.setObjectName("muted")
        self.path_label.setWordWrap(True)
        refresh = GhostButton("Обновить")
        refresh.clicked.connect(self._reload)
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(self.path_label, 1)
        header_layout.addWidget(refresh, 0, Qt.AlignTop)
        self._root.addWidget(header)

        self.notice = InlineNotice()
        self._root.addWidget(self.notice)

        self.rows_host = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(24)
        fields_inner = QWidget()
        fields_layout = QVBoxLayout(fields_inner)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(0)
        fields_layout.addWidget(self.rows_host)
        fields_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setWidget(fields_inner)
        self._root.addWidget(scroll, 1)

        self.save_button = PrimaryButton("Сохранить")
        self.save_button.clicked.connect(self._save)
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(self.save_button)
        actions_layout.addStretch()
        self._root.addWidget(actions)
        self._sync_save()

    def on_enter(self, payload: dict[str, Any]) -> None:
        self._reload()

    def _reload(self) -> None:
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

        for spec in ENV_SCHEMA:
            self._add_row(spec.key, values.get(spec.key, spec.default))
        self._saved = self._collect()
        self._sync_save()

    def _add_row(self, key: str, value: str) -> None:
        field = QLineEdit(value)
        field.textChanged.connect(self._sync_save)
        self._inputs[key] = field
        spec = spec_for(key)
        label = spec.label if spec else key
        hint = spec.hint if spec else ""
        if spec and spec.secret:
            field.setEchoMode(QLineEdit.Password)
        editor = field
        if spec and spec.path:
            editor = QWidget()
            picker = QHBoxLayout(editor)
            picker.setContentsMargins(0, 0, 0, 0)
            picker.addWidget(field, 1)
            browse = GhostButton("Файл…")
            browse.clicked.connect(lambda _checked=False, name=key: self._pick_file(name))
            picker.addWidget(browse)
        self.rows_layout.addWidget(LabeledField(label, editor, hint))

    def _pick_file(self, key: str) -> None:
        current = self._inputs[key].text().strip()
        chosen, _ = QFileDialog.getOpenFileName(self, "Выберите файл", current)
        if chosen:
            self._inputs[key].setText(chosen)

    def _collect(self) -> dict[str, str]:
        return {key: field.text().strip() for key, field in self._inputs.items()}

    def _is_dirty(self) -> bool:
        return self._collect() != self._saved

    def _sync_save(self, _text: str = "") -> None:
        self.save_button.setEnabled(self._is_dirty())

    def _save(self) -> None:
        if not self._is_dirty():
            return
        values = self._collect()
        if "API_BASE_URL" in values:
            values["API_BASE_URL"] = values["API_BASE_URL"].rstrip("/")
        warnings: list[str] = []
        for spec in ENV_SCHEMA:
            if spec.default and not values.get(spec.key):
                values[spec.key] = spec.default
                warnings.append(f"{spec.label}: подставлено значение по умолчанию")
        timeout = values.get("API_TIMEOUT_SECONDS", str(HTTP_TIMEOUT_DEFAULT))
        try:
            clamped = clamp_http_timeout(int(timeout))
        except ValueError:
            values["API_TIMEOUT_SECONDS"] = str(HTTP_TIMEOUT_DEFAULT)
            warnings.append(f"Таймаут должен быть числом, подставлено {HTTP_TIMEOUT_DEFAULT}")
        else:
            if str(clamped) != str(timeout).strip():
                values["API_TIMEOUT_SECONDS"] = str(clamped)
                warnings.append(f"Таймаут ограничен диапазоном {HTTP_TIMEOUT_MIN}–{HTTP_TIMEOUT_MAX} сек")
        backup_days = values.get("SERVER_DISK_BACKUP_DAYS", "0")
        try:
            if int(backup_days) < 0:
                raise ValueError
        except ValueError:
            values["SERVER_DISK_BACKUP_DAYS"] = "0"
            warnings.append("Интервал бэкапа должен быть числом дней, подставлено 0")
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
