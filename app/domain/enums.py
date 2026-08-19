from __future__ import annotations

from enum import Enum
from typing import Any


class MimeType(str, Enum):
    JSON = "application/json"
    PNG = "image/png"
    MP3 = "audio/mpeg"
    PDF = "application/pdf"

    @classmethod
    def values(cls) -> set[str]:
        return {item.value for item in cls}


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AppStore(str, Enum):
    GOOGLE_PLAY = "PlayMarket"
    APP_STORE = "AppStore"
    RU_STORE = "RuStore"

    @property
    def label(self) -> str:
        return {
            AppStore.GOOGLE_PLAY: "Google Play",
            AppStore.APP_STORE: "App Store",
            AppStore.RU_STORE: "RuStore",
        }[self]

    @classmethod
    def from_api(cls, value: Any) -> AppStore:
        text = str(value or "").strip()
        for item in cls:
            if text == item.value:
                return item
        aliases = {
            "googleplay": cls.GOOGLE_PLAY,
            "google_play": cls.GOOGLE_PLAY,
            "playmarket": cls.GOOGLE_PLAY,
            "appstore": cls.APP_STORE,
            "app_store": cls.APP_STORE,
            "rustore": cls.RU_STORE,
            "ru_store": cls.RU_STORE,
        }
        key = text.lower().replace("-", "_").replace(" ", "")
        parsed = aliases.get(key) or aliases.get(key.replace("_", ""))
        if parsed is None:
            raise ValueError(f"Неизвестный стор версии: {value}")
        return parsed


class ThemeMode(str, Enum):
    DARK = "dark"
    LIGHT = "light"


class PageId(str, Enum):
    LOGIN = "login"
    DASHBOARD = "dashboard"
    APPLICATION = "application"
    RESOURCES = "resources"
    REVIEWS = "reviews"
    GENERATE_ROUTE = "generate_route"
    SECRETS = "secrets"
    SERVER_RESOURCES = "server_resources"
    PROMOCODES = "promocodes"
    ENV = "env"
