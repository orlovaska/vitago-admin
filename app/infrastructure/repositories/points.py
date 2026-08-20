from __future__ import annotations

from typing import Any

from app.core.exceptions import ApiError
from app.domain.models import Point
from app.infrastructure.repositories.base import BaseRepository


class PointRepository(BaseRepository):
    def get(self, point_id: int) -> Point:
        payload = self._client.get(f"/admin/points/{point_id}")
        if not payload.get("success") or not payload.get("point"):
            raise ApiError(payload.get("message") or "Точка не найдена")
        return Point.from_form_dto(
            payload["point"],
            point_id=point_id,
            route_id=payload.get("routeId"),
        )

    def create(self, route_id: int, point: Point) -> int:
        payload = self._client.post(
            "/admin/points",
            json={"routeId": route_id, "point": point.to_form_dto()},
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при создании точки")
        return int(payload["pointId"])

    def update(self, point_id: int, point: Point) -> None:
        payload = self._client.put(f"/admin/points/{point_id}", json={"point": point.to_form_dto()})
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при сохранении точки")

    def set_transcript_cues(self, point_id: int, cues: list[dict] | None, *, locale: str = "ru") -> None:
        payload = self._client.put(
            f"/admin/points/{point_id}/transcript-cues",
            json={"cues": cues, "locale": locale},
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось сохранить таймкоды")

    def delete(self, point_id: int) -> None:
        payload = self._client.delete(f"/admin/points/{point_id}")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при удалении точки")

    def import_from_json(self, route_id: int, points: list[dict[str, Any]]) -> int:
        payload = self._client.post(
            "/admin/points/import-from-json",
            json={"routeId": route_id, "points": points},
        )
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка при импорте точек")
        return int(payload.get("pointsCount") or 0)
