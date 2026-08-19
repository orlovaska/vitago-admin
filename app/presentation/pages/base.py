from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from app.core.container import Container
from app.presentation.navigation import NavigationMediator
from app.presentation.workers import TaskRunner


class BasePage(QWidget):
    """Template Method: страница получает зависимости и умеет обновляться при входе."""

    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.container = container
        self.navigator = navigator
        self.tasks = TaskRunner(self)
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(24, 20, 24, 20)
        self._root.setSpacing(16)

    def enter(self, payload: dict[str, Any] | None = None) -> None:
        self.on_enter(payload or {})

    def on_enter(self, payload: dict[str, Any]) -> None:
        return None


class ScrollPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)
        self.scroll.setWidget(self.content)
        self._root.addWidget(self.scroll)
