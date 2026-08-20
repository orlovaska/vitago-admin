from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget

from app.core.container import Container
from app.domain.enums import PageId
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import Card, InlineNotice, PageHeader, PrimaryButton


def _home_page() -> PageId:
    raw = str(QSettings("Vitago", "AdminPanel").value("lastPage", PageId.DASHBOARD.value) or PageId.DASHBOARD.value)
    try:
        page = PageId(raw)
    except ValueError:
        return PageId.DASHBOARD
    if page is PageId.LOGIN:
        return PageId.DASHBOARD
    return page


class LoginPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self.login_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.submit = PrimaryButton("Войти")
        self.submit.clicked.connect(self._login)
        self.password_input.returnPressed.connect(self._login)
        self.login_input.returnPressed.connect(self._login)
        self.notice = InlineNotice()

        card = Card(object_name="loginCard")
        card.body.addWidget(PageHeader("Вход в систему", "Панель администратора Vitago"))
        card.body.addWidget(self.notice)
        card.body.addWidget(QLabel("Логин"))
        card.body.addWidget(self.login_input)
        card.body.addWidget(QLabel("Пароль"))
        card.body.addWidget(self.password_input)
        card.body.addWidget(self.submit)

        holder = QFrame()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setAlignment(Qt.AlignCenter)
        holder_layout.addWidget(card, alignment=Qt.AlignCenter)
        self._root.addWidget(holder)

    def on_enter(self, payload: dict[str, Any]) -> None:
        if self.container.settings.api_base_url:
            self.notice.clear_notice()
            return
        self.notice.show_warning(
            "Базовый URL API не задан. Войти можно, но запросы к серверу не выполнятся."
        )

    def _login(self) -> None:
        login = self.login_input.text().strip()
        password = self.password_input.text()
        if not login or not password:
            self.notice.show_warning("Укажите логин и пароль")
            return
        self.submit.setEnabled(False)
        self.tasks.submit(
            self.container.auth.login,
            self._on_success,
            self._on_error,
            login,
            password,
            busy_text="Вход…",
        )

    def _on_success(self, result: tuple[str, str]) -> None:
        token, login = result
        self.container.session.set_credentials(token, login)
        self.submit.setEnabled(True)
        self.navigator.go(_home_page())

    def _on_error(self, message: str) -> None:
        self.submit.setEnabled(True)
        self.notice.show_warning(message or "Не удалось войти")
