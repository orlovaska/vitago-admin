from __future__ import annotations

from app.presentation.theme.palette import Palette


def build_stylesheet(palette: Palette) -> str:
    return f"""
    QWidget {{
        color: {palette.text};
        font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background: {palette.window};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QLabel#pageTitle {{
        font-size: 22px;
        font-weight: 700;
    }}
    QLabel#pageSubtitle, QLabel#muted {{
        color: {palette.muted};
    }}
    QLabel#sectionTitle {{
        font-size: 16px;
        font-weight: 600;
    }}
    QFrame#card, QGroupBox {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 14px;
    }}
    QGroupBox {{
        margin-top: 12px;
        padding: 16px 12px 12px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
    }}
    QFrame#sidebar {{
        background: {palette.sidebar};
        border-right: 1px solid {palette.border};
    }}
    QListWidget#nav {{
        background: transparent;
        border: none;
        outline: none;
        padding: 8px;
    }}
    QListWidget#nav::item {{
        color: {palette.sidebar_text};
        padding: 10px 12px;
        margin: 4px 0;
        border-radius: 10px;
    }}
    QListWidget#nav::item:selected {{
        background: {palette.accent};
        color: #ffffff;
    }}
    QListWidget#nav::item:hover {{
        background: {palette.accent_soft};
    }}
    QPushButton {{
        background: {palette.surface_alt};
        border: 1px solid {palette.border};
        border-radius: 10px;
        padding: 8px 14px;
        min-height: 18px;
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
    QPushButton#ghost {{
        background: transparent;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {palette.input};
        border: 1px solid {palette.border};
        border-radius: 10px;
        padding: 8px 10px;
        selection-background-color: {palette.accent};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {palette.accent};
    }}
    QTableWidget, QTableView {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 12px;
        gridline-color: {palette.border};
        selection-background-color: {palette.accent_soft};
        selection-color: {palette.text};
    }}
    QHeaderView::section {{
        background: {palette.surface_alt};
        color: {palette.muted};
        border: none;
        border-bottom: 1px solid {palette.border};
        padding: 8px;
        font-weight: 600;
    }}
    QCheckBox, QRadioButton {{
        spacing: 8px;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
    }}
    QStatusBar {{
        background: {palette.surface};
        color: {palette.muted};
    }}
    QToolTip {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
        padding: 6px;
    }}
    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: 12px;
        background: {palette.surface};
    }}
    QTabBar::tab {{
        background: {palette.surface_alt};
        padding: 8px 16px;
        margin-right: 4px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }}
    QTabBar::tab:selected {{
        background: {palette.accent};
        color: #ffffff;
    }}
    """
