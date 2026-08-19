from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv

from app.core.env_file import ENV_SCHEMA, ensure_env_file, env_path as default_env_path


@dataclass(frozen=True)
class Settings:
    """Конфигурация приложения. Singleton через Settings.load()."""

    api_base_url: str
    default_support_chat_url: str
    api_timeout_seconds: int

    _instance: ClassVar[Settings | None] = None

    @classmethod
    def load(cls, env_path: Path | None = None) -> Settings:
        if cls._instance is not None:
            return cls._instance

        ensure_env_file()
        load_dotenv(env_path or default_env_path())
        defaults = {item.key: item.default for item in ENV_SCHEMA}

        api_base_url = (os.getenv("API_BASE_URL") or defaults["API_BASE_URL"]).rstrip("/")

        timeout_raw = os.getenv("API_TIMEOUT_SECONDS") or defaults["API_TIMEOUT_SECONDS"]
        try:
            timeout = int(timeout_raw)
        except ValueError:
            timeout = int(defaults["API_TIMEOUT_SECONDS"] or "30")

        cls._instance = cls(
            api_base_url=api_base_url,
            default_support_chat_url=os.getenv("DEFAULT_SUPPORT_CHAT_URL")
            or defaults["DEFAULT_SUPPORT_CHAT_URL"],
            api_timeout_seconds=timeout,
        )
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def resource_url(self, resource_id: int) -> str:
        return f"{self.api_base_url}/resource/{resource_id}"
