from __future__ import annotations

from app.core.exceptions import ApiError
from app.domain.models import Review
from app.infrastructure.repositories.base import BaseRepository


class ReviewRepository(BaseRepository):
    def list_all(self) -> list[Review]:
        payload = self._client.get("/admin/reviews")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось загрузить отзывы")
        items = []
        for raw in payload.get("reviews") or []:
            if raw.get("userId") is None or raw.get("routeId") is None:
                continue
            items.append(Review.from_api(raw))
        return items

    def approve(self, user_id: int, route_id: int) -> None:
        payload = self._client.post(f"/admin/reviews/{user_id}/{route_id}/approve")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось подтвердить отзыв")

    def reject(self, user_id: int, route_id: int) -> None:
        payload = self._client.post(f"/admin/reviews/{user_id}/{route_id}/reject")
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Не удалось отклонить отзыв")
