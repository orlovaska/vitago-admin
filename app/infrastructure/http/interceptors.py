from __future__ import annotations

from abc import ABC
from typing import Any

from requests import Response

from app.core.exceptions import ApiError, AuthError
from app.core.session import AuthSession


class Interceptor(ABC):
    """Звено Chain of Responsibility для HTTP-запросов."""

    def __init__(self) -> None:
        self._next: Interceptor | None = None

    def set_next(self, interceptor: Interceptor) -> Interceptor:
        self._next = interceptor
        return interceptor

    def handle_request(self, method: str, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        kwargs = self.process_request(method, url, kwargs)
        if self._next:
            return self._next.handle_request(method, url, kwargs)
        return kwargs

    def handle_response(self, response: Response) -> Response:
        response = self.process_response(response)
        if self._next:
            return self._next.handle_response(response)
        return response

    def process_request(self, method: str, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        return kwargs

    def process_response(self, response: Response) -> Response:
        return response


class AuthInterceptor(Interceptor):
    def __init__(self, session: AuthSession) -> None:
        super().__init__()
        self._session = session

    def process_request(self, method: str, url: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        headers = dict(kwargs.get("headers") or {})
        if self._session.token:
            headers["Authorization"] = f"Bearer {self._session.token}"
        kwargs["headers"] = headers
        return kwargs


class ErrorInterceptor(Interceptor):
    def __init__(self, session: AuthSession) -> None:
        super().__init__()
        self._session = session

    def process_response(self, response: Response) -> Response:
        if response.status_code == 401:
            self._session.clear()
            raise AuthError(self._extract_message(response, "Сессия истекла"), 401)
        if response.status_code >= 400:
            raise ApiError(self._extract_message(response), response.status_code)
        return response

    @staticmethod
    def _extract_message(response: Response, fallback: str = "Произошла неизвестная ошибка") -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or fallback
        if isinstance(payload, dict) and payload.get("message"):
            return str(payload["message"])
        return fallback
