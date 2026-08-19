from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import ThemeMode


@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    success: str
    danger: str
    warning: str
    sidebar: str
    sidebar_text: str
    input: str

    @classmethod
    def for_mode(cls, mode: ThemeMode) -> Palette:
        if mode is ThemeMode.LIGHT:
            return cls(
                window="#f3f5fb",
                surface="#ffffff",
                surface_alt="#eef2fb",
                border="#d9e0ef",
                text="#12203a",
                muted="#5d6b86",
                accent="#3b6cff",
                accent_hover="#2f5ae6",
                accent_soft="#e8eeff",
                success="#16a34a",
                danger="#dc2626",
                warning="#d97706",
                sidebar="#10182b",
                sidebar_text="#d7def0",
                input="#ffffff",
            )
        return cls(
            window="#0b1220",
            surface="#121a2b",
            surface_alt="#18233a",
            border="#2a3854",
            text="#e8eef9",
            muted="#8b97b0",
            accent="#5b8cff",
            accent_hover="#7aa0ff",
            accent_soft="#1c2c4d",
            success="#22c55e",
            danger="#ef4444",
            warning="#f59e0b",
            sidebar="#0a101c",
            sidebar_text="#c9d4ea",
            input="#0f1728",
        )
