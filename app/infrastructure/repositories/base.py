from __future__ import annotations

from abc import ABC

from app.infrastructure.http.client import ApiClient


class BaseRepository(ABC):
    def __init__(self, client: ApiClient) -> None:
        self._client = client
