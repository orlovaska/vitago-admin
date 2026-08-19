from __future__ import annotations

from PyQt5.QtGui import QColor, QPalette

from app.presentation.theme.palette import Palette


def build_qpalette(palette: Palette) -> QPalette:
    """Системная палитра Qt, чтобы виджеты не брали цвета Windows по умолчанию."""
    qpalette = QPalette()
    window = QColor(palette.window)
    text = QColor(palette.text)
    surface = QColor(palette.surface)
    surface_alt = QColor(palette.surface_alt)
    accent = QColor(palette.accent)
    muted = QColor(palette.muted)
    border = QColor(palette.border)
    on_accent = QColor("#ffffff")

    qpalette.setColor(QPalette.Window, window)
    qpalette.setColor(QPalette.WindowText, text)
    qpalette.setColor(QPalette.Base, surface)
    qpalette.setColor(QPalette.AlternateBase, surface_alt)
    qpalette.setColor(QPalette.Text, text)
    qpalette.setColor(QPalette.Button, surface_alt)
    qpalette.setColor(QPalette.ButtonText, text)
    qpalette.setColor(QPalette.BrightText, on_accent)
    qpalette.setColor(QPalette.Light, surface_alt)
    qpalette.setColor(QPalette.Midlight, surface)
    qpalette.setColor(QPalette.Mid, border)
    qpalette.setColor(QPalette.Dark, border)
    qpalette.setColor(QPalette.Shadow, border)
    qpalette.setColor(QPalette.Highlight, accent)
    qpalette.setColor(QPalette.HighlightedText, on_accent)
    qpalette.setColor(QPalette.Link, accent)
    qpalette.setColor(QPalette.LinkVisited, accent)
    qpalette.setColor(QPalette.ToolTipBase, surface)
    qpalette.setColor(QPalette.ToolTipText, text)
    qpalette.setColor(QPalette.PlaceholderText, muted)

    qpalette.setColor(QPalette.Disabled, QPalette.WindowText, muted)
    qpalette.setColor(QPalette.Disabled, QPalette.Text, muted)
    qpalette.setColor(QPalette.Disabled, QPalette.ButtonText, muted)
    qpalette.setColor(QPalette.Disabled, QPalette.Highlight, border)
    qpalette.setColor(QPalette.Disabled, QPalette.HighlightedText, muted)
    return qpalette
