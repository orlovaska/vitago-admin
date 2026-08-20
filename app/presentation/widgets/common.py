from __future__ import annotations

from PyQt5.QtCore import QEvent, QObject, QTimer, Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.core.log import log_error, log_warning


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
    def __init__(self, parent: QWidget | None = None, *, object_name: str = "card") -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)

    @property
    def body(self) -> QVBoxLayout:
        return self._layout


class HCarousel(QWidget):
    """Горизонтальная карусель виджетов: стрелки и прокрутка колесом."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._prev = GhostButton("‹")
        self._next = GhostButton("›")
        self._prev.setFixedWidth(36)
        self._next.setFixedWidth(36)
        self._prev.clicked.connect(lambda: self._nudge(-1))
        self._next.clicked.connect(lambda: self._nudge(1))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.viewport().installEventFilter(self)

        self._inner = QWidget()
        self._cards = QHBoxLayout(self._inner)
        self._cards.setContentsMargins(0, 0, 0, 0)
        self._cards.setSpacing(12)
        self._cards.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._cards.addStretch()
        self.scroll.setWidget(self._inner)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._prev)
        layout.addWidget(self.scroll, 1)
        layout.addWidget(self._next)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._schedule_fit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self.scroll.viewport() and event.type() == QEvent.Wheel:
            delta = event.angleDelta().y() or event.angleDelta().x()
            bar = self.scroll.horizontalScrollBar()
            bar.setValue(bar.value() - delta)
            return True
        return super().eventFilter(watched, event)

    def clear(self) -> None:
        while self._cards.count() > 1:
            item = self._cards.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._schedule_fit()

    def add_widget(self, widget: QWidget) -> None:
        widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        self._cards.insertWidget(self._cards.count() - 1, widget)
        self._schedule_fit()

    def _schedule_fit(self) -> None:
        QTimer.singleShot(0, self._fit_height)

    def _fit_height(self) -> None:
        content_h = 0
        for index in range(self._cards.count()):
            widget = self._cards.itemAt(index).widget()
            if widget is not None:
                widget.adjustSize()
                content_h = max(content_h, widget.sizeHint().height())
        if content_h <= 0:
            content_h = 40
        bar_h = self.scroll.horizontalScrollBar().sizeHint().height()
        self.scroll.setFixedHeight(content_h + bar_h)
        self.updateGeometry()

    def _nudge(self, direction: int) -> None:
        bar = self.scroll.horizontalScrollBar()
        step = max(240, int(self.scroll.viewport().width() * 0.8))
        bar.setValue(bar.value() + direction * step)


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


class Switch(QCheckBox):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("switch")
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
        if text:
            log_warning(text)
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


def confirm(
    parent: QWidget,
    title: str,
    text: str,
    *,
    ok_text: str = "Да",
    cancel_text: str = "Отмена",
) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    yes = box.button(QMessageBox.Yes)
    no = box.button(QMessageBox.No)
    if yes is not None:
        yes.setText(ok_text)
    if no is not None:
        no.setText(cancel_text)
    return box.exec_() == QMessageBox.Yes


def confirm_delete(parent: QWidget, text: str) -> bool:
    return confirm(parent, "Подтверждение удаления", text, ok_text="Удалить", cancel_text="Отмена")


def notify_error(parent: QWidget, message: str) -> None:
    log_error(message)
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


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """Значение меняется только вводом или кнопками, не колесом мыши."""

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class BusyOverlay(QWidget):
    """Полупрозрачный слой на время загрузки с сервера."""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("busyOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()
        host.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(12)
        self.label = QLabel("Загрузка с сервера…")
        self.label.setObjectName("sectionTitle")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(260)
        panel_layout.addWidget(self.label)
        panel_layout.addWidget(self.bar, alignment=Qt.AlignCenter)
        layout.addWidget(panel, alignment=Qt.AlignCenter)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self.parent() and event.type() == QEvent.Resize:
            self._fit()
        return super().eventFilter(watched, event)

    def show_busy(self, text: str = "") -> None:
        self.label.setText(text.strip() or "Загрузка с сервера…")
        self._fit()
        self.show()
        self.raise_()

    def hide_busy(self) -> None:
        self.hide()

    def _fit(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
