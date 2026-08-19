from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from app.domain.enums import PageId


@dataclass(frozen=True)
class NavigateCommand:
    page_id: PageId
    payload: dict[str, Any] = field(default_factory=dict)


class NavigationMediator(QObject):
    """Mediator между сайдбаром, окном и страницами."""

    navigated = pyqtSignal(object)

    def go(self, page_id: PageId, **payload: Any) -> None:
        self.navigated.emit(NavigateCommand(page_id=page_id, payload=payload))
