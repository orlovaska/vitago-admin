from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.exceptions import ApiError
from app.domain.models import Resource
from app.infrastructure.repositories.base import BaseRepository


class ResourceRepository(BaseRepository):
    def list_all(self) -> list[Resource]:
        payload = self._client.get("/admin/resources")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось загрузить ресурсы")
        return [Resource.from_api(item) for item in payload.get("resources") or []]

    def upload(self, file_paths: list[Path]) -> dict[str, Any]:
        files = [("files", (path.name, path.open("rb"), _guess_mime(path))) for path in file_paths]
        try:
            payload = self._client.post("/admin/resources/upload", files=files)
        finally:
            for _, handle in files:
                handle[1].close()
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при загрузке файлов")
        return payload

    def delete(self, resource_id: int) -> None:
        payload = self._client.delete(f"/admin/resources/{resource_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось удалить ресурс")

    def bulk_delete(self, ids: list[int]) -> dict[str, Any]:
        payload = self._client.post("/admin/resources/bulk-delete", json={"ids": ids})
        return payload


def _guess_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    mapping = {
        ".json": "application/json",
        ".png": "image/png",
        ".mp3": "audio/mpeg",
        ".pdf": "application/pdf",
    }
    return mapping.get(suffix, "application/octet-stream")
