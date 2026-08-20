from __future__ import annotations

import threading
from typing import Any

import requests
from requests import Response

from app.core.config import Settings
from app.core.env_file import HTTP_CONNECT_TIMEOUT
from app.core.exceptions import ApiError
from app.core.session import AuthSession
from app.infrastructure.http.interceptors import AuthInterceptor, ErrorInterceptor, Interceptor


class ApiClient:
    """Фасад HTTP-клиента с цепочкой интерцепторов."""

    def __init__(self, settings: Settings, session: AuthSession) -> None:
        self._settings = settings
        self._local = threading.local()
        self._chain = self._build_chain(session)

    def update_settings(self, settings: Settings) -> None:
        self._settings = settings

    def _http(self) -> requests.Session:
        http = getattr(self._local, "session", None)
        if http is None:
            http = requests.Session()
            self._local.session = http
        return http

    def _timeout(self, timeout: int | None) -> tuple[int, int]:
        read = timeout or self._settings.api_timeout_seconds
        return (min(HTTP_CONNECT_TIMEOUT, read), read)

    def _build_chain(self, session: AuthSession) -> Interceptor:
        auth = AuthInterceptor(session)
        errors = ErrorInterceptor(session)
        auth.set_next(errors)
        return auth

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        files: Any | None = None,
        data: Any | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        url = f"{self._settings.api_base_url}{path}"
        timeout_value = self._timeout(timeout)
        kwargs: dict[str, Any] = {
            "params": params,
            "timeout": timeout_value,
        }
        if files is not None:
            kwargs["files"] = files
            kwargs["data"] = data
        elif json is not None:
            kwargs["json"] = json
        elif data is not None:
            kwargs["data"] = data

        kwargs = self._chain.handle_request(method, url, kwargs)
        try:
            response: Response = self._http().request(method, url, **kwargs)
        except requests.Timeout as exc:
            raise ApiError(f"Сервер не ответил за {timeout_value[1]} сек") from exc
        except requests.ConnectionError as exc:
            raise ApiError("Нет соединения с сервером") from exc
        except requests.RequestException as exc:
            raise ApiError(f"Ошибка подключения к серверу: {exc}") from exc
        self._chain.handle_response(response)
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("Сервер вернул некорректный JSON") from exc

    def get_bytes(self, path: str, timeout: int | None = None) -> tuple[bytes, str]:
        url = f"{self._settings.api_base_url}{path}"
        timeout_value = self._timeout(timeout)
        kwargs: dict[str, Any] = {"timeout": timeout_value}
        kwargs = self._chain.handle_request("GET", url, kwargs)
        try:
            response: Response = self._http().request("GET", url, **kwargs)
        except requests.Timeout as exc:
            raise ApiError(f"Сервер не ответил за {timeout_value[1]} сек") from exc
        except requests.ConnectionError as exc:
            raise ApiError("Нет соединения с сервером") from exc
        except requests.RequestException as exc:
            raise ApiError(f"Ошибка подключения к серверу: {exc}") from exc
        self._chain.handle_response(response)
        content_type = response.headers.get("content-type", "")
        return response.content, content_type

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self.request("DELETE", path, **kwargs)
