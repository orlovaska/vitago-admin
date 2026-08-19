from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.models import SecretsState
from app.infrastructure.ssh_secrets import SshSecretsClient


class SecretsRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings

    def load(self) -> SecretsState:
        return SshSecretsClient(self._settings).load()

    def save(self, file: str, values: dict[str, str]) -> SecretsState:
        client = SshSecretsClient(self._settings)
        if not client.configured():
            raise AppError(client.missing_reason())
        return client.save(file, values)

    def save_text(self, file: str, text: str) -> SecretsState:
        client = SshSecretsClient(self._settings)
        if not client.configured():
            raise AppError(client.missing_reason())
        return client.save_text(file, text)

    def restart(self, services: list[str]) -> str:
        client = SshSecretsClient(self._settings)
        if not client.configured():
            raise AppError(client.missing_reason())
        return client.restart(services)
