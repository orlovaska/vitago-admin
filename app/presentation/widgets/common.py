from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def hbox(*widgets: QWidget, spacing: int = 8, stretch: bool = True) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    if stretch:
        layout.addStretch()
    return layout


def vbox(*widgets: QWidget, spacing: int = 10) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(0, 0, 0, 0)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

    @property
    def body(self) -> QVBoxLayout:
        return self._layout


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.title_label)
        if subtitle:
            layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label.hide()


class PrimaryButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("primary")
        self.setCursor(Qt.PointingHandCursor)


class DangerButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("danger")
        self.setCursor(Qt.PointingHandCursor)


class GhostButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("ghost")
        self.setCursor(Qt.PointingHandCursor)


class InlineNotice(QLabel):
    """Неблокирующее предупреждение на форме вместо модального окна."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWordWrap(True)
        self.setStyleSheet("color: #d97706;")
        self.hide()

    def show_warning(self, text: str) -> None:
        self.setText(text)
        self.setVisible(bool(text))

    def clear_notice(self) -> None:
        self.setText("")
        self.hide()


class StatusDot(QLabel):
    def __init__(self, enabled: bool, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        color = "#22c55e" if enabled else "#ef4444"
        self.setText(f"<span style='color:{color}'>●</span>  {label}")


def confirm(parent: QWidget, title: str, text: str) -> bool:
    result = QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return result == QMessageBox.Yes


def notify_error(parent: QWidget, message: str) -> None:
    QMessageBox.critical(parent, "Ошибка", message)


def notify_info(parent: QWidget, message: str) -> None:
    QMessageBox.information(parent, "Готово", message)


class Toast(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "background:#111827; color:white; border-radius:10px; padding:10px 14px;"
        )
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, ms: int = 3500) -> None:
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move(parent.width() - self.width() - 24, parent.height() - self.height() - 24)
        self.show()
        self.raise_()
        self._timer.start(ms)


class LabeledField(QWidget):
    def __init__(self, label: str, widget: QWidget, helper: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        caption = QLabel(label)
        caption.setObjectName("muted")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(caption)
        layout.addWidget(widget)
        self.helper = QLabel(helper)
        self.helper.setObjectName("muted")
        self.helper.setWordWrap(True)
        if helper:
            layout.addWidget(self.helper)
        else:
            self.helper.hide()
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
