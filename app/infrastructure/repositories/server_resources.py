from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.domain.models import ServerResourcesState
from app.infrastructure.ssh_disk import SshDiskClient


class ServerResourcesRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings

    def list_files(self) -> ServerResourcesState:
        return SshDiskClient(self._settings).list_files()

    def create_backup(self) -> tuple[str, str]:
        return SshDiskClient(self._settings).create_backup()

    def download_latest(self, local_dir: Path | None = None) -> Path:
        return SshDiskClient(self._settings).download_latest(local_dir)

    def create_backup_and_download(self, local_dir: Path | None = None) -> tuple[str, Path]:
        return SshDiskClient(self._settings).create_backup_and_download(local_dir)
