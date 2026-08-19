from __future__ import annotations

from typing import Any

from PyQt5.QtWidgets import QCheckBox, QHBoxLayout, QLabel

from app.core.container import Container
from app.domain.enums import ReviewStatus
from app.domain.models import Review
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import Card, GhostButton, PageHeader, PrimaryButton, confirm, notify_error, notify_info
from app.presentation.widgets.data_table import DataTable


class ReviewsPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._reviews: list[Review] = []
        self._root.addWidget(PageHeader("Одобрение отзывов", "Модерация отзывов пользователей"))

        filters = Card()
        row = QHBoxLayout()
        self.pending = QCheckBox("Непроверенные")
        self.approved = QCheckBox("Подтвержденные")
        self.rejected = QCheckBox("Отклоненные")
        self.pending.setChecked(True)
        for box in (self.pending, self.approved, self.rejected):
            box.stateChanged.connect(self._refresh_table)
            row.addWidget(box)
        self.counter = QLabel()
        row.addStretch()
        row.addWidget(self.counter)
        filters.body.addLayout(row)
        self._root.addWidget(filters)

        actions = QHBoxLayout()
        approve = PrimaryButton("Подтвердить выбранный")
        reject = GhostButton("Отклонить выбранный")
        approve.clicked.connect(lambda: self._act("approve"))
        reject.clicked.connect(lambda: self._act("reject"))
        actions.addWidget(approve)
        actions.addWidget(reject)
        actions.addStretch()
        self._root.addLayout(actions)

        self.table = DataTable(
            ["User ID", "Route ID", "Пользователь", "Маршрут", "Текст", "Оценка", "Статус", "Создано"],
            name="reviews",
        )
        self._root.addWidget(self.table)

    def on_enter(self, payload: dict[str, Any]) -> None:
        self.tasks.submit(self.container.reviews.list_all, self._set, lambda msg: notify_error(self, msg))

    def _set(self, reviews: list[Review]) -> None:
        self._reviews = reviews
        self._refresh_table()

    def _selected_filters(self) -> set[ReviewStatus]:
        selected = set()
        if self.pending.isChecked():
            selected.add(ReviewStatus.PENDING)
        if self.approved.isChecked():
            selected.add(ReviewStatus.APPROVED)
        if self.rejected.isChecked():
            selected.add(ReviewStatus.REJECTED)
        return selected or {ReviewStatus.PENDING}

    def _visible(self) -> list[Review]:
        allowed = self._selected_filters()
        return [item for item in self._reviews if item.status in allowed]

    def _refresh_table(self) -> None:
        visible = self._visible()
        self.counter.setText(f"Всего отзывов: {len(visible)}")
        labels = {
            ReviewStatus.PENDING: "На проверке",
            ReviewStatus.APPROVED: "Подтвержден",
            ReviewStatus.REJECTED: "Отклонен",
        }
        rows = []
        ids = []
        for item in visible:
            route = f"{item.route_name or ''} ({item.route_city or ''})".strip() or f"ID: {item.route_id}"
            created = item.created_at.strftime("%d.%m.%Y %H:%M") if item.created_at else ""
            rows.append(
                [
                    str(item.user_id),
                    str(item.route_id),
                    item.user_alias or "",
                    route,
                    item.text or "",
                    str(item.rating),
                    labels[item.status],
                    created,
                ]
            )
            ids.append(item.row_id)
        self.table.set_rows(rows, ids)

    def _act(self, action: str) -> None:
        selected = self.table.selected_ids()
        if not selected:
            notify_error(self, "Выберите отзыв")
            return
        row_id = str(selected[0])
        user_id, route_id = (int(part) for part in row_id.split("-"))
        if action == "reject" and not confirm(self, "Отклонение", "Отклонить этот отзыв?"):
            return
        try:
            if action == "approve":
                self.container.reviews.approve(user_id, route_id)
                notify_info(self, "Отзыв подтвержден")
            else:
                self.container.reviews.reject(user_id, route_id)
                notify_info(self, "Отзыв отклонен")
            self.on_enter({})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
