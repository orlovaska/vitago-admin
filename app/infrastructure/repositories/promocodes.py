from __future__ import annotations

from typing import Any

from app.core.exceptions import ApiError
from app.domain.models import Promocode
from app.infrastructure.repositories.base import BaseRepository


class PromocodeRepository(BaseRepository):
    def list_by_route(self, route_id: int) -> list[Promocode]:
        payload = self._client.get("/admin/promocodes", params={"routeId": route_id})
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось загрузить промокоды")
        return [Promocode.from_api(item) for item in payload.get("promocodes") or []]

    def create(self, data: dict[str, Any]) -> Promocode | None:
        payload = self._client.post("/admin/promocodes", json=data)
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось создать промокод")
        raw = payload.get("promocode")
        return Promocode.from_api(raw) if raw else None

    def update(self, promocode_id: int, data: dict[str, Any]) -> Promocode | None:
        payload = self._client.put(f"/admin/promocodes/{promocode_id}", json=data)
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось обновить промокод")
        raw = payload.get("promocode")
        return Promocode.from_api(raw) if raw else None

    def regenerate_token(self, promocode_id: int) -> Promocode | None:
        payload = self._client.post(f"/admin/promocodes/{promocode_id}/regenerate-token")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось обновить токен")
        raw = payload.get("promocode")
        return Promocode.from_api(raw) if raw else None

    def delete(self, promocode_id: int) -> None:
        payload = self._client.delete(f"/admin/promocodes/{promocode_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось удалить промокод")
