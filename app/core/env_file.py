from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import bundled_root, project_root

ENV_FILENAME = ".env"
ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class EnvVarSpec:
    key: str
    label: str
    hint: str = ""
    default: str = ""
    required: bool = False
    secret: bool = False
    path: bool = False


ENV_SCHEMA: tuple[EnvVarSpec, ...] = (
    EnvVarSpec(
        "API_BASE_URL",
        "Базовый URL API",
        "Без завершающего слэша",
        default="http://200.165.231.43",
    ),
    EnvVarSpec(
        "DEFAULT_SUPPORT_CHAT_URL",
        "URL чата поддержки",
        "Подставляется в визарде клона",
        default="https://t.me/vitago_support",
    ),
    EnvVarSpec(
        "API_TIMEOUT_SECONDS",
        "Таймаут HTTP-запросов (сек)",
        default="30",
    ),
    EnvVarSpec(
        "SECRETS_SSH_HOST",
        "SSH-хост секретов",
        "Сервер, где лежит vitago-backend",
        default="200.165.231.43",
    ),
    EnvVarSpec(
        "SECRETS_SSH_USER",
        "SSH-пользователь",
        "Пользователь на сервере",
        default="root",
    ),
    EnvVarSpec(
        "SECRETS_SSH_KEY",
        "SSH-ключ",
        "Относительно папки админки, если путь не абсолютный",
        default=".ssh/id_ed25519",
        secret=True,
        path=True,
    ),
    EnvVarSpec(
        "SECRETS_REMOTE_PATH",
        "Путь к vitago-backend на сервере",
        default="/opt/vitago-backend",
    ),
    EnvVarSpec(
        "SERVER_DISK_BACKUP_DAYS",
        "Бэкап папки ресурсов, дни",
        "Раз в N дней архив на сервере в backups/. 0 — не делать",
        default="0",
    ),
)

_SCHEMA_KEYS = {item.key: item for item in ENV_SCHEMA}


def env_path() -> Path:
    return project_root() / ENV_FILENAME


def example_path() -> Path:
    return bundled_root() / ".env.example"


def ensure_env_file() -> Path:
    target = env_path()
    if target.exists():
        return target
    example = example_path()
    if example.exists():
        target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        return target
    write_env({item.key: item.default for item in ENV_SCHEMA}, target)
    return target


def spec_for(key: str) -> EnvVarSpec | None:
    return _SCHEMA_KEYS.get(key)


def is_schema_key(key: str) -> bool:
    return key in _SCHEMA_KEYS


def validate_key(key: str) -> str | None:
    if not ENV_KEY_PATTERN.fullmatch(key):
        return "Имя переменной: латиница, цифры и _, не начинается с цифры"
    return None


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            values[key] = _unquote(value.strip())
    return values


def normalize_env_text(text: str) -> str:
    """Убирает лишние пустые строки, оставляя не больше одной подряд."""
    lines: list[str] = []
    prev_blank = False
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.rstrip()
        blank = not line
        if blank:
            if not lines or prev_blank:
                continue
            lines.append("")
            prev_blank = True
            continue
        lines.append(line)
        prev_blank = False
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def read_env(path: Path | None = None) -> dict[str, str]:
    values = {item.key: item.default for item in ENV_SCHEMA}
    target = path or env_path()
    if target.exists():
        values.update(parse_env(target.read_text(encoding="utf-8")))
    return values


def write_env(values: dict[str, str], path: Path | None = None) -> Path:
    target = path or env_path()
    target.write_text(_dump_env(values), encoding="utf-8")
    return target


def _dump_env(values: dict[str, str]) -> str:
    lines: list[str] = []
    written: set[str] = set()
    for spec in ENV_SCHEMA:
        if spec.hint:
            lines.append(f"# {spec.hint}")
        lines.append(f"{spec.key}={_encode(values.get(spec.key, spec.default))}")
        lines.append("")
        written.add(spec.key)
    extras = [key for key in values if key not in written]
    if extras:
        lines.append("# Дополнительные переменные")
        for key in extras:
            lines.append(f"{key}={_encode(values[key])}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        quote = value[0]
        inner = value[1:-1]
        if quote == '"':
            return inner.replace('\\"', '"').replace("\\n", "\n")
        return inner
    return value


def _encode(value: str) -> str:
    if any(char in value for char in ' \t#\'"'):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def apply_env_updates(original: str, values: dict[str, str]) -> str:
    remaining = dict(values)
    lines: list[str] = []
    for line in original.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(line)
            continue
        key = stripped.partition("=")[0].strip()
        if key in remaining:
            lines.append(f"{key}={_encode(remaining.pop(key))}")
    for key, value in remaining.items():
        lines.append(f"{key}={_encode(value)}")
    return "\n".join(lines).rstrip() + "\n"
