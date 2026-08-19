from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Корень приложения: каталог исходников или папка рядом с .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_root() -> Path:
    """Каталог ресурсов: исходники или временная папка PyInstaller."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return project_root()
