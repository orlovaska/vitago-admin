from __future__ import annotations

from typing import Any

from app.core.exceptions import ApiError
from app.domain.models import RouteForm
from app.infrastructure.repositories.base import BaseRepository


class RouteRepository(BaseRepository):
    def get(self, route_id: int) -> RouteForm:
        payload = self._client.get(f"/admin/routes/{route_id}")
        if not payload.get("success") or not payload.get("route"):
            raise ApiError(payload.get("message") or "Маршрут не найден")
        return RouteForm.from_api(payload["route"])

    def create(self, application_id: int, form: RouteForm) -> int:
        payload = self._client.post(
            "/admin/routes",
            json={"applicationId": application_id, "route": form.to_api()},
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при создании маршрута")
        return int(payload["routeId"])

    def update(self, route_id: int, form: RouteForm) -> None:
        payload = self._client.put(f"/admin/routes/{route_id}", json={"route": form.to_api()})
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при сохранении маршрута")

    def delete(self, route_id: int) -> None:
        payload = self._client.delete(f"/admin/routes/{route_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при удалении маршрута")
