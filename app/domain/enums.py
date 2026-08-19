from __future__ import annotations

from enum import Enum


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
    ENV = "env"
