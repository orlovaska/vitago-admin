from __future__ import annotations

from app.core.config import Settings
from app.core.env_file import apply_env_updates, normalize_env_text, parse_env
from app.core.exceptions import AppError
from app.domain.models import SecretGroup, SecretItem, SecretsState
from app.infrastructure.ssh import BundledRemoteScript

SECRET_FILES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("app_config", "Контейнер app", ("app",)),
    ("db_credentials", "Контейнеры app и db", ("app", "db")),
    ("nginx_backend", "Контейнер nginx", ("nginx",)),
)
_FILE_NAMES = {item[0] for item in SECRET_FILES}
_SERVICES = {"app", "db", "nginx"}
_SERVICE_ORDER = ("db", "app", "nginx")


class SshSecretsClient:
    """Секреты и перезапуск контейнеров через скрипт админки на сервере по SSH."""

    def __init__(self, settings: Settings) -> None:
        self._script = BundledRemoteScript(
            settings,
            "remote-secrets.sh",
            "scripts/vitago-admin-secrets.sh",
        )

    def configured(self) -> bool:
        return self._script.configured()

    def missing_reason(self) -> str:
        return self._script.missing_reason()

    def load(self) -> SecretsState:
        if not self.configured():
            return SecretsState(
                writable=False,
                restart_available=False,
                restart_reason=self.missing_reason(),
                groups=(),
            )
        groups = []
        for name, label, services in SECRET_FILES:
            text = normalize_env_text(self._script.run(["read", name]))
            secrets = tuple(SecretItem(key=key, value=value) for key, value in parse_env(text).items())
            groups.append(SecretGroup(file=name, label=label, services=services, secrets=secrets, raw=text))
        return SecretsState(
            writable=True,
            restart_available=True,
            restart_reason="",
            groups=tuple(groups),
        )

    def save(self, file: str, values: dict[str, str]) -> SecretsState:
        self._assert_file(file)
        original = self._script.run(["read", file])
        return self.save_text(file, apply_env_updates(original, values))

    def save_text(self, file: str, text: str) -> SecretsState:
        self._assert_file(file)
        body = normalize_env_text(text)
        self._script.run(["write", file], stdin=body)
        return self.load()

    def restart(self, services: list[str]) -> str:
        ordered = [name for name in _SERVICE_ORDER if name in services]
        if not ordered or any(name not in _SERVICES for name in services):
            raise AppError("Некорректный список контейнеров")
        output = self._script.run(["restart", *ordered], timeout=180)
        return f"Контейнеры пересозданы: {', '.join(ordered)}" + (f"\n{output}" if output else "")

    @staticmethod
    def _assert_file(name: str) -> None:
        if name not in _FILE_NAMES:
            raise AppError(f"Неизвестный файл секретов: {name}")
