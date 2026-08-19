from __future__ import annotations

import sys
from ctypes import byref, c_int, sizeof

from PyQt5.QtWidgets import QWidget

from app.domain.enums import ThemeMode
from app.presentation.theme.palette import Palette

if sys.platform == "win32":
    from ctypes import windll
else:
    windll = None  # type: ignore[assignment]

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF


def apply_title_bar(window: QWidget, mode: ThemeMode, palette: Palette) -> None:
    """Красит системную шапку окна под текущую тему (Windows 10/11)."""
    if windll is None:
        return
    try:
        hwnd = int(window.winId())
        dark = mode is ThemeMode.DARK
        _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, int(dark))
        _set_attr(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, int(dark))
        caption = _hex_to_colorref(palette.window) if dark else DWMWA_COLOR_DEFAULT
        text = _hex_to_colorref(palette.text) if dark else DWMWA_COLOR_DEFAULT
        _set_attr(hwnd, DWMWA_CAPTION_COLOR, caption)
        _set_attr(hwnd, DWMWA_TEXT_COLOR, text)
    except OSError:
        return


def _set_attr(hwnd: int, attribute: int, value: int) -> None:
    data = c_int(value)
    windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, byref(data), sizeof(data))


def _hex_to_colorref(color: str) -> int:
    raw = color.lstrip("#")
    red, green, blue = int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return red | (green << 8) | (blue << 16)
