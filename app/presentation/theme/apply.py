from __future__ import annotations

from PyQt5.QtWidgets import QApplication, QStyleFactory, QWidget

from app.domain.enums import ThemeMode
from app.presentation.theme.palette import Palette
from app.presentation.theme.qt_palette import build_qpalette
from app.presentation.theme.scale import DEFAULT_UI_SCALE, scale_px
from app.presentation.theme.stylesheet import build_stylesheet
from app.presentation.theme.title_bar import apply_title_bar


def apply_appearance(window: QWidget, mode: ThemeMode, ui_scale: int = DEFAULT_UI_SCALE) -> Palette:
    """Fusion + QPalette + stylesheet, чтобы не всплывали системные цвета Windows."""
    palette = Palette.for_mode(mode)
    app = QApplication.instance()
    qpalette = build_qpalette(palette)
    if app is not None:
        app.setStyle(QStyleFactory.create("Fusion"))
        app.setPalette(qpalette)
        app.setStyleSheet(build_stylesheet(palette, ui_scale))
        font = app.font()
        font.setFamily("Segoe UI")
        font.setPixelSize(scale_px(13, ui_scale))
        app.setFont(font)
    window.setPalette(qpalette)
    apply_title_bar(window, mode, palette)
    return palette
