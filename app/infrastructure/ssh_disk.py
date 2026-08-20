from __future__ import annotations

import re
from dataclasses import replace
from datetime import date
from pathlib import Path

from app.core.config import Settings
from app.core.exceptions import AppError
from app.domain.models import ServerResource, ServerResourcesState
from app.infrastructure.ssh import BundledRemoteScript, SshClient

_ARCHIVE_DATE = re.compile(r"disk-(\d{4}-\d{2}-\d{2})\.tar\.gz$")


class SshDiskClient:
    """Список файлов ресурсов и архивный бэкап папки на сервере по SSH."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._days = settings.server_disk_backup_days
        self._script = BundledRemoteScript(
            settings,
            "remote-disk.sh",
            "scripts/vitago-admin-disk.sh",
        )

    def configured(self) -> bool:
        return self._script.configured()

    def missing_reason(self) -> str:
        return self._script.missing_reason()

    def list_files(self) -> ServerResourcesState:
        if not self.configured():
            return ServerResourcesState(folder="", reason=self.missing_reason(), items=())
        backup_note, last_archive = self._sync_backup()
        state = parse_disk_list(self._script.run(["list"], timeout=120))
        return replace(state, backup_note=backup_note, last_archive=last_archive)

    def _sync_backup(self) -> tuple[str, str]:
        archive, _size = parse_archive(self._script.run(["last"]))
        if self._days <= 0:
            note = "Автобэкап выключен (SERVER_DISK_BACKUP_DAYS=0)"
            if archive:
                note += f". Последний архив: {archive}"
            return note, archive
        last_day = archive_date(archive)
        if last_day is not None:
            elapsed = (date.today() - last_day).days
            if elapsed < self._days:
                left = self._days - elapsed
                return f"Следующий бэкап через {left} дн. Последний архив: {archive}", archive
        created = self._script.run(["backup"], timeout=600)
        return note_from_backup(created, archive)

    def create_backup(self) -> tuple[str, str]:
        if not self.configured():
            raise AppError(self.missing_reason())
        created = self._script.run(["backup", "force"], timeout=600)
        note, path = note_from_backup(created)
        if not path:
            raise AppError("Не удалось создать архив")
        return note, path

    def latest_archive(self) -> str:
        if not self.configured():
            raise AppError(self.missing_reason())
        archive, _size = parse_archive(self._script.run(["last"]))
        if not archive:
            raise AppError("На сервере нет архива в backups/")
        return archive

    def download_archive(self, remote_rel: str, local_path: Path) -> Path:
        if not self.configured():
            raise AppError(self.missing_reason())
        remote = self._remote_file(remote_rel)
        target = local_path.expanduser().resolve()
        self._ssh().download(remote, target, timeout=600)
        if not target.is_file():
            raise AppError(f"Файл не скачан: {target}")
        return target

    def create_backup_and_download(self, local_dir: Path | None = None) -> tuple[str, Path]:
        note, remote_rel = self.create_backup()
        target_dir = (local_dir or (Path.home() / "Downloads")).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        local = self.download_archive(remote_rel, target_dir / Path(remote_rel).name)
        return note, local

    def download_latest(self, local_dir: Path | None = None) -> Path:
        remote_rel = self.latest_archive()
        target_dir = (local_dir or (Path.home() / "Downloads")).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        return self.download_archive(remote_rel, target_dir / Path(remote_rel).name)

    def _ssh(self) -> SshClient:
        return SshClient(
            self._settings.secrets_ssh_host,
            self._settings.secrets_ssh_user,
            self._settings.secrets_ssh_key,
        )

    def _remote_file(self, relative: str) -> str:
        root = self._settings.secrets_remote_path.strip().rstrip("/")
        return f"{root}/{relative.replace(chr(92), '/').lstrip('/')}"


def note_from_backup(output: str, fallback: str = "") -> tuple[str, str]:
    path, _size, status = parse_archive_result(output)
    if status == "CREATED" and path:
        return f"Создан архив {path}", path
    if path:
        return f"Архив за сегодня уже есть: {path}", path
    return "Не удалось создать архив", fallback


def parse_disk_list(output: str) -> ServerResourcesState:
    folder = ""
    disk: dict[str, tuple[int | None, str]] = {}
    db_paths: set[str] = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        kind, _, rest = line.partition("\t")
        if kind == "FOLDER":
            folder = rest.strip()
            continue
        if kind == "DB":
            path = rest.strip()
            if path:
                db_paths.add(path)
            continue
        if kind == "DISK":
            path, _, tail = rest.partition("\t")
            size_raw, _, mtime = tail.partition("\t")
            path = path.strip()
            if not path:
                continue
            try:
                size = int(size_raw.strip()) if size_raw.strip() else None
            except ValueError:
                size = None
            disk[path] = (size, mtime.strip())

    items: list[ServerResource] = []
    for path in sorted(set(disk) | db_paths):
        size, mtime = disk.get(path, (None, ""))
        items.append(
            ServerResource(
                path=path,
                size=size,
                modified_at=mtime,
                on_disk=path in disk,
                in_db=path in db_paths,
            )
        )
    return ServerResourcesState(folder=folder, reason="", items=tuple(items))


def parse_archive(output: str) -> tuple[str, int | None]:
    path, size, _status = parse_archive_result(output)
    return path, size


def parse_archive_result(output: str) -> tuple[str, int | None, str]:
    for raw in output.splitlines():
        line = raw.strip()
        if not line.startswith("ARCHIVE\t"):
            continue
        parts = line.split("\t")
        path = parts[1].strip() if len(parts) > 1 else ""
        size: int | None = None
        status = ""
        if len(parts) > 2:
            try:
                size = int(parts[2].strip())
            except ValueError:
                status = parts[2].strip()
        if len(parts) > 3:
            status = parts[3].strip()
        return path, size, status
    return "", None, ""


def archive_date(path: str) -> date | None:
    match = _ARCHIVE_DATE.search(path.replace("\\", "/"))
    if not match:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None
