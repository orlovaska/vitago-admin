from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.container import Container
from app.core.env_file import apply_env_updates, normalize_env_text, parse_env, validate_key
from app.domain.models import SecretGroup, SecretsState
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import (
    GhostButton,
    InlineNotice,
    LabeledField,
    PageHeader,
    PrimaryButton,
    confirm,
    notify_error,
    notify_info,
)

_SENSITIVE_MARKERS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")


def _is_sensitive(key: str) -> bool:
    upper = key.upper()
    return any(marker in upper for marker in _SENSITIVE_MARKERS)


def _plain_text(text: str) -> str:
    normalized = normalize_env_text(text)
    return normalized[:-1] if normalized.endswith("\n") else normalized


class _SecretGroupPanel(QWidget):
    def __init__(
        self,
        group: SecretGroup,
        *,
        writable: bool,
        applied_text: str,
        on_changed: Any,
        on_notice: Any,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.file = group.file
        self.services = list(group.services)
        self._writable = writable
        self._on_changed = on_changed
        self._on_notice = on_notice
        self._inputs: dict[str, QLineEdit] = {}
        self._server_text = normalize_env_text(group.raw)
        self._applied_text = normalize_env_text(applied_text)

        path = QLabel(f"Файл secrets/{group.file}")
        path.setObjectName("muted")
        path.setWordWrap(True)

        self.rows_host = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_host)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(10)
        for item in group.secrets:
            self._add_row(item.key, item.value)

        self.new_key = QLineEdit()
        self.new_key.setPlaceholderText("NEW_VARIABLE")
        self.new_value = QLineEdit()
        self.new_value.setPlaceholderText("значение")
        add_button = GhostButton("Добавить")
        add_button.setEnabled(writable)
        add_button.clicked.connect(self._add_variable)
        add_row = QWidget()
        add_layout = QHBoxLayout(add_row)
        add_layout.setContentsMargins(0, 0, 0, 0)
        add_layout.addWidget(self.new_key)
        add_layout.addWidget(self.new_value)
        add_layout.addWidget(add_button)

        fields_inner = QWidget()
        fields_layout = QVBoxLayout(fields_inner)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(10)
        fields_layout.addWidget(self.rows_host)
        fields_layout.addWidget(LabeledField("Новая переменная", add_row))
        fields_layout.addStretch()

        fields_scroll = QScrollArea()
        fields_scroll.setWidgetResizable(True)
        fields_scroll.setFrameShape(QFrame.NoFrame)
        fields_scroll.setWidget(fields_inner)

        self.raw_edit = QPlainTextEdit(_plain_text(self._server_text))
        self.raw_edit.setEnabled(writable)
        self.raw_edit.setPlaceholderText("Содержимое secrets/" + group.file)
        self.raw_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        self.raw_edit.setFont(font)
        self.raw_edit.textChanged.connect(self._notify_changed)

        self.view_tabs = QTabWidget()
        self.view_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view_tabs.tabBar().setExpanding(False)
        self.view_tabs.addTab(fields_scroll, "Переменные")
        self.view_tabs.addTab(self.raw_edit, "Файл")
        self._mode = "raw"
        self.view_tabs.setCurrentIndex(1)
        self.view_tabs.currentChanged.connect(self._on_view_tab)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(path)
        layout.addWidget(self.view_tabs, 1)

    def applied_text(self) -> str:
        return self._applied_text

    def is_dirty(self) -> bool:
        return normalize_env_text(self.file_text()) != self._server_text

    def needs_restart(self) -> bool:
        return bool(self.services) and self._server_text != self._applied_text

    def restart_label(self) -> str:
        return f"Перезапустить {', '.join(self.services)}" if self.services else "Перезапустить"

    def mark_saved(self) -> None:
        self._server_text = normalize_env_text(self.file_text())
        self._notify_changed()

    def mark_applied(self) -> None:
        self._applied_text = self._server_text
        self._notify_changed()

    def _notify_changed(self) -> None:
        self._on_changed()

    def _add_row(self, key: str, value: str) -> None:
        field = QLineEdit(value)
        field.setEnabled(self._writable)
        if _is_sensitive(key):
            field.setEchoMode(QLineEdit.Password)
        field.textChanged.connect(self._notify_changed)
        self._inputs[key] = field
        self.rows_layout.addWidget(LabeledField(key, field))

    def _add_variable(self) -> None:
        key = self.new_key.text().strip()
        error = validate_key(key)
        if error:
            self._on_notice(error)
            return
        if key in self._inputs:
            self._on_notice(f"Переменная {key} уже есть в списке")
            return
        self._on_notice("")
        self._add_row(key, self.new_value.text())
        self.new_key.clear()
        self.new_value.clear()
        self._notify_changed()

    def view_mode(self) -> str:
        return self._mode

    def _on_view_tab(self, index: int) -> None:
        self.set_view_mode("fields" if index == 0 else "raw")

    def _rebuild_rows(self, values: dict[str, str]) -> None:
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._inputs.clear()
        for key, value in values.items():
            self._add_row(key, value)

    def set_view_mode(self, mode: str) -> None:
        if mode == "raw":
            if self._mode != "raw":
                self.raw_edit.blockSignals(True)
                self.raw_edit.setPlainText(_plain_text(apply_env_updates(self.raw_edit.toPlainText(), self.collect())))
                self.raw_edit.blockSignals(False)
            self._mode = "raw"
            if self.view_tabs.currentIndex() != 1:
                self.view_tabs.blockSignals(True)
                self.view_tabs.setCurrentIndex(1)
                self.view_tabs.blockSignals(False)
            self._notify_changed()
            return
        if self._mode != "fields":
            self._rebuild_rows(parse_env(self.raw_edit.toPlainText()))
        self._mode = "fields"
        if self.view_tabs.currentIndex() != 0:
            self.view_tabs.blockSignals(True)
            self.view_tabs.setCurrentIndex(0)
            self.view_tabs.blockSignals(False)
        self._notify_changed()

    def collect(self) -> dict[str, str]:
        return {key: field.text() for key, field in self._inputs.items()}

    def file_text(self) -> str:
        if self._mode == "raw":
            return self.raw_edit.toPlainText()
        return apply_env_updates(self.raw_edit.toPlainText(), self.collect())


class SecretsPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._busy = False
        self._loaded = False
        self._writable = False
        self._restart_available = False
        self._panels: list[_SecretGroupPanel] = []
        self._applied_text: dict[str, str] = {}
        self._saving_panel: _SecretGroupPanel | None = None
        self._restarting_panel: _SecretGroupPanel | None = None

        header = PageHeader("Секреты сервера", "SSH не проверен")
        self.status = header.subtitle_label
        self._root.addWidget(header)
        self.notice = InlineNotice()
        self._root.addWidget(self.notice)

        refresh = GhostButton("Обновить")
        refresh.clicked.connect(self._reload)
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.setCornerWidget(refresh, Qt.TopRightCorner)
        self.tabs.currentChanged.connect(self._sync_actions)
        self._root.addWidget(self.tabs, 1)

        self.save_button = PrimaryButton("Сохранить")
        self.save_button.clicked.connect(self._save_current)
        self.restart_button = GhostButton("Перезапустить")
        self.restart_button.clicked.connect(self._restart_current)
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.restart_button)
        actions_layout.addStretch()
        self._root.addWidget(actions)
        self._sync_actions()

    def on_enter(self, payload: dict[str, Any]) -> None:
        if self._loaded or self._busy:
            return
        self._reload()

    def _current_panel(self) -> _SecretGroupPanel | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, _SecretGroupPanel) else None

    def _sync_actions(self, _index: int = 0) -> None:
        panel = self._current_panel()
        can_write = self._writable and not self._busy
        can_restart = self._restart_available and not self._busy
        if panel is None:
            self.save_button.setEnabled(False)
            self.restart_button.setEnabled(False)
            self.restart_button.setText("Перезапустить")
            return
        self.save_button.setEnabled(can_write and panel.is_dirty())
        self.restart_button.setEnabled(can_restart and panel.needs_restart())
        self.restart_button.setText(panel.restart_label())

    def _reload(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._sync_actions()
        self.notice.clear_notice()
        self.tasks.submit(
            self.container.secrets.load,
            self._render,
            self._on_error,
            busy_text="Загрузка секретов по SSH…",
        )

    def _render(self, state: SecretsState) -> None:
        self._busy = False
        self._loaded = True
        current_file = self._current_panel().file if self._current_panel() else None
        modes = {panel.file: panel.view_mode() for panel in self._panels}
        for panel in self._panels:
            self._applied_text[panel.file] = panel.applied_text()

        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if widget:
                widget.deleteLater()
        self._panels = []

        parts = []
        parts.append("Запись по SSH доступна" if state.writable else "SSH не настроен")
        if state.restart_available:
            parts.append("перезапуск контейнеров доступен")
        else:
            parts.append(state.restart_reason or "перезапуск контейнеров недоступен")
        self.status.setText(". ".join(parts))
        self._writable = state.writable
        self._restart_available = state.restart_available

        if not state.writable:
            self.notice.show_warning(state.restart_reason or "SSH для секретов не настроен.")
        elif not state.restart_available and state.restart_reason:
            self.notice.show_warning(state.restart_reason)

        restore_index = 0
        for group in state.groups:
            applied = self._applied_text.get(group.file, normalize_env_text(group.raw))
            panel = _SecretGroupPanel(
                group,
                writable=state.writable,
                applied_text=applied,
                on_changed=self._sync_actions,
                on_notice=self._show_notice,
            )
            self._applied_text[group.file] = panel.applied_text()
            panel.set_view_mode(modes.get(group.file, "raw"))
            self._panels.append(panel)
            self.tabs.addTab(panel, group.label)
            if group.file == current_file:
                restore_index = self.tabs.count() - 1

        if self.tabs.count():
            self.tabs.setCurrentIndex(restore_index)
        self._sync_actions()

    def _show_notice(self, message: str) -> None:
        if message:
            self.notice.show_warning(message)
            return
        self.notice.clear_notice()

    def _save_current(self) -> None:
        panel = self._current_panel()
        if self._busy or panel is None or not panel.is_dirty():
            return
        self._busy = True
        self._saving_panel = panel
        self._sync_actions()
        self.notice.clear_notice()
        self.tasks.submit(
            self.container.secrets.save_text,
            self._on_saved,
            self._on_error,
            panel.file,
            panel.file_text(),
            busy_text="Запись секретов по SSH…",
        )

    def _on_saved(self, state: SecretsState) -> None:
        self._busy = False
        panel = self._saving_panel
        self._saving_panel = None
        if panel is not None:
            panel.mark_saved()
            self._applied_text[panel.file] = panel.applied_text()
        notify_info(self, "Секреты записаны на сервер. Чтобы контейнеры их подхватили, нажмите «Перезапустить».")
        self._writable = state.writable
        self._restart_available = state.restart_available
        self._sync_actions()

    def _restart_current(self) -> None:
        panel = self._current_panel()
        if self._busy or panel is None or not panel.services or not panel.needs_restart():
            return
        names = ", ".join(panel.services)
        if not confirm(
            self,
            "Перезапуск контейнеров",
            f"Будут пересозданы контейнеры: {names}. API может быть недоступен несколько секунд. Продолжить?",
        ):
            return
        self._busy = True
        self._restarting_panel = panel
        self._sync_actions()
        self.tasks.submit(
            self.container.secrets.restart,
            self._on_restarted,
            self._on_restart_error,
            panel.services,
            busy_text="Перезапуск контейнеров по SSH…",
        )

    def _on_restarted(self, message: str) -> None:
        self._busy = False
        panel = self._restarting_panel
        self._restarting_panel = None
        restarted = set(panel.services) if panel is not None else set()
        for item in self._panels:
            if set(item.services) <= restarted:
                item.mark_applied()
                self._applied_text[item.file] = item.applied_text()
        notify_info(self, message)
        self._sync_actions()

    def _on_restart_error(self, message: str) -> None:
        self._busy = False
        self._restarting_panel = None
        self._sync_actions()
        if "подключен" in message.lower() or "connection" in message.lower() or "установлен" in message.lower():
            notify_info(self, "Перезапуск, вероятно, начался. Подождите и обновите список.")
            return
        notify_error(self, message)

    def _on_error(self, message: str) -> None:
        self._busy = False
        self._saving_panel = None
        self._sync_actions()
        notify_error(self, message)
