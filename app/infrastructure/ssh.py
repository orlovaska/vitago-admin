from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from shlex import quote

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.paths import bundled_root, project_root

DEFAULT_SSH_KEY = ".ssh/id_ed25519"


class SshClient:
    """SSH/SCP с ключом из настроек админки."""

    def __init__(self, host: str, user: str, key_path: str) -> None:
        self._host = host.strip()
        self._user = user.strip()
        self._key_path = resolve_ssh_key_path(key_path)

    @property
    def target(self) -> str:
        if self._user:
            return f"{self._user}@{self._host}"
        return self._host

    def run(self, command: str, *, timeout: int = 30, stdin: str | None = None) -> str:
        args = [self._bin("ssh"), *self._opts(), self.target, command]
        return self._exec(args, timeout, stdin)

    def upload(self, local: Path, remote_path: str, *, timeout: int = 30) -> None:
        args = [self._bin("scp"), *self._opts(), str(local), f"{self.target}:{remote_path}"]
        self._exec(args, timeout)

    def _opts(self) -> list[str]:
        return [
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "IdentitiesOnly=yes",
            "-i",
            self._key_path,
        ]

    @staticmethod
    def _bin(name: str) -> str:
        if sys.platform != "win32":
            return name
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates = [
            system_root / "System32" / "OpenSSH" / f"{name}.exe",
            program_files / "Git" / "usr" / "bin" / f"{name}.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return name

    @staticmethod
    def _exec(args: list[str], timeout: int, stdin: str | None = None) -> str:
        kwargs: dict[str, object] = {
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
            "input": stdin,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            result = subprocess.run(args, **kwargs)  # noqa: S603
        except FileNotFoundError as exc:
            raise AppError("Не найден ssh/scp. Установите OpenSSH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AppError("Таймаут SSH-команды") from exc
        if result.returncode != 0:
            message = (result.stderr or result.stdout or f"exit {result.returncode}").strip()
            raise AppError(message)
        return (result.stdout or "").strip()


def ssh_key_candidates(value: str) -> list[Path]:
    raw = value.strip().strip('"').strip("'") or DEFAULT_SSH_KEY
    path = Path(raw).expanduser()
    if path.is_absolute():
        return [path]
    return [project_root() / path, bundled_root() / path]


def find_ssh_key(value: str = "") -> Path | None:
    seen: set[Path] = set()
    for path in ssh_key_candidates(value):
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved.resolve()
    return None


def resolve_ssh_key_path(value: str) -> str:
    found = find_ssh_key(value)
    if found is not None:
        return str(found)
    shown = ssh_key_candidates(value)[0]
    raise AppError(f"SSH-ключ не найден: {shown}")


class BundledRemoteScript:
    """Копирует скрипт админки на сервер и запускает его по SSH."""

    def __init__(self, settings: Settings, local_name: str, remote_rel: str) -> None:
        self._host = settings.secrets_ssh_host.strip()
        self._user = settings.secrets_ssh_user.strip()
        self._key = settings.secrets_ssh_key.strip()
        self._remote_path = settings.secrets_remote_path.strip().rstrip("/")
        self._local_name = local_name
        self._remote_rel = remote_rel.replace("\\", "/").lstrip("/")
        self._ready = False

    def configured(self) -> bool:
        return bool(self._host and self._remote_path and find_ssh_key(self._key))

    def missing_reason(self) -> str:
        missing = []
        if not self._host:
            missing.append("SECRETS_SSH_HOST")
        if not find_ssh_key(self._key):
            missing.append(f"SSH-ключ ({self._key or DEFAULT_SSH_KEY})")
        if not self._remote_path:
            missing.append("SECRETS_REMOTE_PATH")
        if not missing:
            return ""
        return "Нужно для SSH: " + ", ".join(missing)

    def run(self, args: list[str], *, stdin: str | None = None, timeout: int = 30) -> str:
        self._ensure()
        remote_script = f"{self._remote_path}/{self._remote_rel}"
        command = (
            f"sed -i 's/\\r$//' {quote(remote_script)} && "
            f"VITAGO_ROOT={quote(self._remote_path)} bash {quote(remote_script)} "
            + " ".join(quote(item) for item in args)
        )
        return SshClient(self._host, self._user, self._key).run(command, timeout=timeout, stdin=stdin)

    def _ensure(self) -> None:
        if self._ready:
            return
        local = bundled_root() / "scripts" / self._local_name
        if not local.is_file():
            raise AppError(f"Не найден скрипт админки: {local}")
        ssh = SshClient(self._host, self._user, self._key)
        ssh.run(f"mkdir -p {quote(self._remote_path)}/scripts")
        ssh.upload(local, f"{self._remote_path}/{self._remote_rel}")
        self._ready = True
