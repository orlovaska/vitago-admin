from __future__ import annotations

from app.core.exceptions import ApiError
from app.infrastructure.repositories.base import BaseRepository


class AuthRepository(BaseRepository):
    def login(self, login: str, password: str) -> tuple[str, str]:
        payload = self._client.post("/admin/auth/login", json={"login": login, "password": password})
        if not payload.get("success"):
            raise ApiError(payload.get("message") or "Ошибка авторизации")
        return str(payload["accessToken"]), str(payload.get("login") or login)
