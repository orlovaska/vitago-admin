from __future__ import annotations

import tempfile
from pathlib import Path

from app.presentation.theme.palette import Palette
from app.presentation.theme.scale import DEFAULT_UI_SCALE, scale_px


def _combo_arrow_url(color: str) -> str:
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>"
        f"<path fill='{color}' d='M3 5.5h10L8 12z'/></svg>"
    )
    path = Path(tempfile.gettempdir()) / f"vitago-admin-combo-arrow-{color.lstrip('#')}.svg"
    path.write_text(svg, encoding="utf-8")
    return path.as_posix()


def build_stylesheet(palette: Palette, ui_scale: int = DEFAULT_UI_SCALE) -> str:
    def px(base: int) -> str:
        return f"{scale_px(base, ui_scale)}px"

    combo_arrow = _combo_arrow_url(palette.muted)

    return f"""
    QWidget {{
        color: {palette.text};
        font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
        font-size: {px(13)};
    }}
    QMainWindow, QDialog, QMessageBox, QStackedWidget {{
        background: {palette.window};
        color: {palette.text};
    }}
    QScrollArea {{
        border: none;
        background: {palette.window};
    }}
    QScrollArea > QWidget > QWidget {{
        background: {palette.window};
        color: {palette.text};
    }}
    QWidget#busyOverlay {{
        background-color: rgba(0, 0, 0, 140);
    }}
    QWidget#busyOverlay QLabel#sectionTitle {{
        color: {palette.text};
        background: transparent;
    }}
    QWidget#busyOverlay QProgressBar {{
        background: {palette.input};
        border: 1px solid {palette.border};
        border-radius: {px(8)};
        min-height: {px(10)};
        max-height: {px(10)};
    }}
    QWidget#busyOverlay QProgressBar::chunk {{
        background: {palette.accent};
        border-radius: {px(8)};
    }}
    QLabel#pageTitle {{
        font-size: {px(22)};
        font-weight: 700;
        color: {palette.text};
        background: transparent;
    }}
    QLabel#pageSubtitle, QLabel#muted {{
        color: {palette.muted};
        background: transparent;
        font-size: {px(13)};
    }}
    QLabel#sectionTitle {{
        font-size: {px(16)};
        font-weight: 600;
        color: {palette.text};
        background: transparent;
    }}
    QFrame#card, QFrame#loginCard, QFrame#appCard, QGroupBox {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
        border-radius: {px(14)};
    }}
    QFrame#loginCard {{
        max-width: {px(420)};
        min-width: {px(360)};
    }}
    QFrame#appCard {{
        max-width: {px(320)};
        min-width: {px(320)};
    }}
    QGroupBox {{
        margin-top: {px(12)};
        padding: {px(16)} {px(12)} {px(12)} {px(12)};
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: {px(14)};
        padding: 0 {px(6)};
        color: {palette.text};
    }}
    #sidebar {{
        background: {palette.sidebar};
        border-right: 1px solid {palette.border};
    }}
    #sidebar QLabel, #sidebar QLabel#pageTitle {{
        color: {palette.sidebar_text};
        background: transparent;
    }}
    #sidebar QLabel#pageTitle {{
        padding-left: {px(22)};
    }}
    #sidebar QPushButton,
    #sidebar QPushButton#ghost {{
        color: {palette.sidebar_text};
        background: transparent;
        border: 1px solid {palette.sidebar_text};
        min-height: {px(22)};
    }}
    #sidebar QPushButton:hover,
    #sidebar QPushButton#ghost:hover {{
        border-color: {palette.accent};
        background: {palette.accent};
        color: #ffffff;
    }}
    #sidebar QPushButton:disabled,
    #sidebar QPushButton#ghost:disabled {{
        color: #8b97b0;
        border-color: #4a5670;
        background: transparent;
    }}
    #sidebar QLabel#muted {{
        color: {palette.sidebar_muted};
        background: transparent;
    }}
    QListWidget#nav {{
        background: transparent;
        border: none;
        outline: none;
        padding: {px(8)};
        color: {palette.sidebar_text};
        font-size: {px(14)};
    }}
    QListWidget#nav::item {{
        color: {palette.sidebar_text};
        padding: {px(12)} {px(14)};
        margin: {px(4)} 0;
        border-radius: {px(10)};
    }}
    QListWidget#nav::item:selected {{
        background: {palette.accent};
        color: #ffffff;
    }}
    QListWidget#nav::item:hover {{
        background: {palette.accent};
        color: #ffffff;
    }}
    QPushButton {{
        background: {palette.surface_alt};
        color: {palette.text};
        border: 1px solid {palette.border};
        border-radius: {px(10)};
        padding: {px(10)} {px(16)};
        min-height: {px(22)};
        font-size: {px(13)};
    }}
    QPushButton:hover {{
        border-color: {palette.accent};
    }}
    QPushButton#primary {{
        background: {palette.accent};
        color: #ffffff;
        border: none;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background: {palette.accent_hover};
    }}
    QPushButton#danger {{
        background: {palette.danger};
        color: #ffffff;
        border: none;
    }}
    QMessageBox QPushButton {{
        min-width: {px(96)};
    }}
    QPushButton#ghost {{
        background: transparent;
        color: {palette.text};
    }}
    QPushButton#ghost:checked {{
        background: {palette.accent};
        color: #ffffff;
        border: none;
        font-weight: 600;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {palette.input};
        color: {palette.text};
        border: 1px solid {palette.border};
        border-radius: {px(10)};
        padding: {px(10)} {px(12)};
        min-height: {px(22)};
        font-size: {px(13)};
        selection-background-color: {palette.accent};
        selection-color: #ffffff;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {palette.accent};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: {px(28)};
        border: none;
        border-left: 1px solid {palette.border};
        background: {palette.surface_alt};
        border-top-right-radius: {px(10)};
        border-bottom-right-radius: {px(10)};
    }}
    QComboBox::drop-down:hover {{
        background: {palette.accent_soft};
    }}
    QComboBox::down-arrow {{
        image: url("{combo_arrow}");
        width: {px(12)};
        height: {px(12)};
    }}
    QComboBox QAbstractItemView {{
        background: {palette.surface};
        color: {palette.text};
        selection-background-color: {palette.accent};
        selection-color: #ffffff;
        border: 1px solid {palette.border};
        font-size: {px(13)};
    }}
    QAbstractItemView {{
        background: {palette.surface};
        color: {palette.text};
        alternate-background-color: {palette.surface_alt};
        outline: none;
    }}
    QTableWidget, QTableView {{
        background: {palette.surface};
        color: {palette.text};
        alternate-background-color: {palette.surface_alt};
        border: 1px solid {palette.border};
        border-radius: {px(12)};
        gridline-color: {palette.border};
        selection-background-color: {palette.accent_soft};
        selection-color: {palette.text};
        font-size: {px(13)};
    }}
    QTableWidget::item, QTableView::item {{
        color: {palette.text};
        padding: {px(6)};
    }}
    QTableWidget::item:alternate, QTableView::item:alternate {{
        color: {palette.text};
    }}
    QTableWidget::item:selected, QTableView::item:selected {{
        color: {palette.text};
        background: {palette.accent_soft};
    }}
    QHeaderView {{
        background: {palette.surface_alt};
        color: {palette.text};
        border: none;
    }}
    QHeaderView::section {{
        background-color: {palette.surface_alt};
        color: {palette.text};
        border: none;
        border-right: 1px solid {palette.border};
        border-bottom: 2px solid {palette.border};
        padding: {px(8)} {px(10)};
        min-height: {px(28)};
        font-weight: 600;
        font-size: {px(13)};
    }}
    QHeaderView::section:hover {{
        background-color: {palette.accent_soft};
        color: {palette.text};
    }}
    QHeaderView::section:pressed, QHeaderView::section:checked {{
        background-color: {palette.accent};
        color: #ffffff;
    }}
    QTableCornerButton::section {{
        background-color: {palette.surface_alt};
        border: none;
        border-bottom: 2px solid {palette.border};
    }}
    QCheckBox, QRadioButton {{
        spacing: {px(8)};
        color: {palette.text};
        background: transparent;
        font-size: {px(13)};
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: {px(16)};
        height: {px(16)};
        border: 1px solid {palette.border};
        border-radius: {px(4)};
        background: {palette.input};
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {palette.accent};
        border-color: {palette.accent};
    }}
    QCheckBox#switch {{
        spacing: {px(8)};
        font-size: {px(13)};
    }}
    QCheckBox#switch::indicator {{
        width: {px(40)};
        height: {px(22)};
        border-radius: {px(11)};
        border: 1px solid {palette.border};
        background: {palette.input};
    }}
    QCheckBox#switch::indicator:checked {{
        background: {palette.accent};
        border-color: {palette.accent};
    }}
    QMenuBar {{
        background: {palette.surface};
        color: {palette.text};
        border-bottom: 1px solid {palette.border};
        padding: {px(4)} {px(8)};
        font-size: {px(13)};
    }}
    QMenuBar::item {{
        background: transparent;
        color: {palette.text};
        padding: {px(6)} {px(10)};
        border-radius: {px(6)};
    }}
    QMenuBar::item:selected {{
        background: {palette.accent_soft};
        color: {palette.text};
    }}
    QMenu {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
        font-size: {px(13)};
    }}
    QMenu::item {{
        padding: {px(8)} {px(18)};
    }}
    QMenu::item:selected {{
        background: {palette.accent_soft};
        color: {palette.text};
    }}
    QStatusBar {{
        background: {palette.surface};
        color: {palette.muted};
    }}
    QToolTip {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
        padding: {px(6)};
        font-size: {px(13)};
    }}
    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: {px(12)};
        background: {palette.surface};
    }}
    QTabBar::tab {{
        background: {palette.surface_alt};
        color: {palette.text};
        padding: {px(8)} {px(16)};
        margin-right: {px(4)};
        border-top-left-radius: {px(10)};
        border-top-right-radius: {px(10)};
        font-size: {px(13)};
    }}
    QTabBar::tab:selected {{
        background: {palette.accent};
        color: #ffffff;
    }}
    """
