from __future__ import annotations

from PyQt5.QtCore import QObject, QSettings, pyqtSignal


class AuthSession(QObject):
    """Хранит токен администратора. Observer: сигнал changed."""

    changed = pyqtSignal(bool)

    def __init__(self) -> None:
        super().__init__()
        self._settings = QSettings("Vitago", "AdminPanel")
        self._token = str(self._settings.value("adminToken", "") or "")
        self._login = str(self._settings.value("adminLogin", "") or "")

    @property
    def token(self) -> str:
        return self._token

    @property
    def login(self) -> str:
        return self._login

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token)

    def set_credentials(self, token: str, login: str) -> None:
        self._token = token
        self._login = login
        self._settings.setValue("adminToken", token)
        self._settings.setValue("adminLogin", login)
        self.changed.emit(True)

    def clear(self) -> None:
        self._token = ""
        self._login = ""
        self._settings.remove("adminToken")
        self._settings.remove("adminLogin")
        self.changed.emit(False)
