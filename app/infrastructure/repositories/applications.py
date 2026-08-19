from __future__ import annotations

from typing import Any

from app.core.exceptions import ApiError
from app.domain.enums import AppStore
from app.domain.models import Application
from app.infrastructure.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository):
    def list_all(self) -> list[Application]:
        payload = self._client.get("/admin/applications/")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось загрузить приложения")
        apps = [Application.from_api(item) for item in payload.get("applications") or []]
        return [app for app in apps if app.is_clone]

    def get(self, application_id: int) -> Application:
        payload = self._client.get(f"/admin/applications/{application_id}")
        if not payload.get("success") or not payload.get("application"):
            raise ApiError(payload.get("message") or "Приложение не найдено")
        return Application.from_api(payload["application"])

    def create(self, data: dict[str, Any]) -> Application:
        body = {**data, "isMultiRoute": False}
        payload = self._client.post("/admin/applications", json=body)
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при создании приложения")
        return Application.from_api(payload["application"])

    def update_resources(self, application_id: int, data: dict[str, Any]) -> dict[str, Any]:
        payload = self._client.put(f"/admin/applications/{application_id}", json=data)
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при обновлении приложения")
        return payload.get("application") or {}

    def update_payment_flag(self, application_id: int, field: str, value: bool) -> None:
        payload = self._client.put(
            f"/admin/applications/{application_id}/payment-flags",
            json={field: value},
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при обновлении флагов оплаты")

    def delete(self, application_id: int) -> None:
        payload = self._client.delete(f"/admin/applications/{application_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при удалении приложения")

    def create_version(
        self,
        application_id: int,
        major: int,
        minor: int,
        patch: int,
        release_notes: str | None,
        store: AppStore,
    ) -> None:
        payload = self._client.post(
            f"/admin/applications/{application_id}/versions",
            json={
                "major": major,
                "minor": minor,
                "patch": patch,
                "releaseNotes": release_notes,
                "store": store.value,
            },
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при создании версии")

    def delete_version(self, application_id: int, version_id: int) -> None:
        payload = self._client.delete(f"/admin/applications/{application_id}/versions/{version_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при удалении версии")
