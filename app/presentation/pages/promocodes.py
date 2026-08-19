from __future__ import annotations

from typing import Any

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QAbstractButton, QAbstractItemView, QButtonGroup, QGridLayout, QHBoxLayout, QLabel

from app.core.container import Container
from app.domain.models import Promocode, TravelRoute
from app.presentation.dialogs.promocode_dialog import PromocodeDialog
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import BasePage
from app.presentation.widgets.common import (
    Card,
    GhostButton,
    PageHeader,
    PrimaryButton,
    confirm,
    notify_error,
    notify_info,
)
from app.presentation.widgets.data_table import DataTable

_FILTER_KEY = "promocodeRouteId"


class PromocodesPage(BasePage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._settings = QSettings("Vitago", "AdminPanel")
        self._routes: list[TravelRoute] = []
        self._promos: list[Promocode] = []
        self._route_id: int | None = None
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        self._filter_group.buttonClicked[QAbstractButton].connect(self._on_filter_button)

        self._root.addWidget(PageHeader("Промокоды", "Фильтр по названию маршрута. Последний выбор запоминается."))

        filters = Card()
        self._filters_grid = QGridLayout()
        self._filters_grid.setContentsMargins(0, 0, 0, 0)
        self._filters_grid.setSpacing(8)
        filters.body.addLayout(self._filters_grid)
        self._root.addWidget(filters)

        toolbar = Card()
        row = QHBoxLayout()
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        add = PrimaryButton("Добавить промокод")
        add.clicked.connect(self._add)
        copy = GhostButton("Копировать ссылку")
        copy.clicked.connect(self._copy)
        regen = GhostButton("Новый токен")
        regen.clicked.connect(self._regen)
        delete = GhostButton("Удалить")
        delete.clicked.connect(self._delete)
        row.addWidget(self.counter)
        row.addStretch()
        row.addWidget(add)
        row.addWidget(copy)
        row.addWidget(regen)
        row.addWidget(delete)
        toolbar.body.addLayout(row)
        self._root.addWidget(toolbar)

        self.table = DataTable(
            ["Код", "Скидка", "Статус", "После оплаты", "Custom scheme", "Ссылка"],
            name="promocodes",
        )
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._root.addWidget(self.table)

    def on_enter(self, payload: dict[str, Any]) -> None:
        self.tasks.submit(self._load_routes, self._set_routes, lambda msg: notify_error(self, msg))

    def _load_routes(self) -> list[TravelRoute]:
        apps = self.container.applications.list_all()
        routes: list[TravelRoute] = []
        for app in apps:
            routes.extend(app.routes)
        return routes

    def _set_routes(self, routes: list[TravelRoute]) -> None:
        self._routes = routes
        self._route_id = self._resolve_route_id(routes)
        self._rebuild_filters()
        self._reload_promos()

    def _resolve_route_id(self, routes: list[TravelRoute]) -> int | None:
        if not routes:
            return None
        saved = self._settings.value(_FILTER_KEY)
        try:
            route_id = int(saved) if saved not in (None, "") else 0
        except (TypeError, ValueError):
            route_id = 0
        if any(item.id == route_id for item in routes):
            return route_id
        return routes[0].id

    def _rebuild_filters(self) -> None:
        self._filter_group.blockSignals(True)
        while self._filters_grid.count():
            item = self._filters_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self._filter_group.removeButton(widget)
                widget.deleteLater()
        if not self._routes:
            empty = QLabel("Маршруты не найдены")
            empty.setObjectName("muted")
            self._filters_grid.addWidget(empty, 0, 0)
            self._filter_group.blockSignals(False)
            return
        labels = [item.route_name.strip() or f"Маршрут {item.id}" for item in self._routes]
        for index, route in enumerate(self._routes):
            name = labels[index]
            if labels.count(name) > 1:
                extra = route.city.strip() or str(route.id)
                name = f"{name} ({extra})"
            button = GhostButton(name)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            self._filter_group.addButton(button, route.id)
            self._filters_grid.addWidget(button, index // 4, index % 4)
            if route.id == self._route_id:
                button.setChecked(True)
        self._filter_group.blockSignals(False)

    def _on_filter_button(self, button: QAbstractButton) -> None:
        route_id = self._filter_group.id(button)
        if route_id == self._route_id:
            return
        self._route_id = route_id
        self._settings.setValue(_FILTER_KEY, route_id)
        self._reload_promos()

    def _reload_promos(self) -> None:
        if self._route_id is None:
            self._set_promos([])
            return
        route_id = self._route_id
        self.tasks.submit(
            self.container.promocodes.list_by_route,
            self._set_promos,
            lambda msg: notify_error(self, msg),
            route_id,
        )

    def _set_promos(self, promos: list[Promocode]) -> None:
        self._promos = promos
        self.counter.setText(f"Промокодов: {len(promos)}")
        rows = []
        ids = []
        for item in promos:
            rows.append(
                [
                    item.code,
                    f"{item.discount_percent}%",
                    "активен" if item.is_active else "выключен",
                    "да" if item.show_after_payment else "нет",
                    "да" if item.use_custom_scheme else "нет",
                    item.deeplink_url or "—",
                ]
            )
            ids.append(item.id)
        self.table.set_rows(rows, ids)

    def _selected_promo(self) -> Promocode | None:
        selected = self.table.selected_ids()
        if not selected:
            return None
        promo_id = int(selected[0])
        return next((item for item in self._promos if item.id == promo_id), None)

    def _add(self) -> None:
        if self._route_id is None:
            notify_error(self, "Нет маршрута для промокода")
            return
        dialog = PromocodeDialog(self.container, self._route_id, self)
        if dialog.exec_():
            self._reload_promos()

    def _copy(self) -> None:
        promo = self._selected_promo()
        if promo is None:
            notify_error(self, "Выберите промокод")
            return
        if not promo.deeplink_url:
            notify_error(self, "Ссылка недоступна")
            return
        QGuiApplication.clipboard().setText(promo.deeplink_url)
        notify_info(self, "Ссылка скопирована")

    def _regen(self) -> None:
        promo = self._selected_promo()
        if promo is None:
            notify_error(self, "Выберите промокод")
            return
        try:
            self.container.promocodes.regenerate_token(promo.id)
            self._reload_promos()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _delete(self) -> None:
        promo = self._selected_promo()
        if promo is None:
            notify_error(self, "Выберите промокод")
            return
        if not confirm(self, "Удаление", "Удалить промокод?"):
            return
        try:
            self.container.promocodes.delete(promo.id)
            self._reload_promos()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
