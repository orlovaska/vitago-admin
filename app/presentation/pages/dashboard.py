from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QLabel, QWidget

from app.core.container import Container
from app.domain.enums import PageId
from app.domain.models import Application
from app.presentation.dialogs.wizard_dialog import CloneWizardDialog
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import ScrollPage
from app.presentation.widgets.common import Card, PageHeader, PrimaryButton, StatusDot, notify_error


class DashboardPage(ScrollPage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        header = PageHeader("Гиды-клоны", "Управление приложениями, маршрутами и ресурсами")
        self.add_button = PrimaryButton("Добавить приложение")
        self.add_button.clicked.connect(self._open_wizard)
        top = Card()
        top.body.addWidget(header)
        top.body.addWidget(self.add_button, alignment=Qt.AlignLeft)
        self.content_layout.addWidget(top)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(12)
        self.content_layout.addWidget(self.grid_host)

        actions = Card()
        actions.body.addWidget(QLabel("Быстрые действия"))
        resources_btn = PrimaryButton("Управление ресурсами")
        reviews_btn = PrimaryButton("Одобрить отзыв")
        geo_btn = PrimaryButton("Генерация маршрута")
        resources_btn.clicked.connect(lambda: self.navigator.go(PageId.RESOURCES))
        reviews_btn.clicked.connect(lambda: self.navigator.go(PageId.REVIEWS))
        geo_btn.clicked.connect(lambda: self.navigator.go(PageId.GENERATE_ROUTE))
        actions.body.addWidget(resources_btn)
        actions.body.addWidget(reviews_btn)
        actions.body.addWidget(geo_btn)
        self.content_layout.addWidget(actions)
        self.content_layout.addStretch()

    def on_enter(self, payload: dict[str, Any]) -> None:
        self.tasks.submit(self.container.applications.list_all, self._render, self._fail)

    def _render(self, applications: list[Application]) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not applications:
            empty = Card()
            empty.body.addWidget(QLabel("Приложения не найдены"))
            self.grid.addWidget(empty, 0, 0)
            return
        for index, app in enumerate(applications):
            self.grid.addWidget(self._card(app), index // 3, index % 3)

    def _card(self, app: Application) -> Card:
        card = Card()
        title = QLabel(app.bundle_id)
        title.setObjectName("sectionTitle")
        card.body.addWidget(title)
        if app.payment_service_postfix:
            card.body.addWidget(QLabel(f"Постфикс оплаты: {app.payment_service_postfix}"))
        card.body.addWidget(QLabel(f"Маршрутов: {len(app.routes)}"))
        card.body.addWidget(QLabel(f"Версий: {len(app.versions)}"))
        card.body.addWidget(StatusDot(app.use_payment_google_play, "Google Play"))
        card.body.addWidget(StatusDot(app.use_payment_app_store, "App Store"))
        card.body.addWidget(StatusDot(app.use_payment_ru_store, "RuStore"))
        button = PrimaryButton("Открыть")
        button.clicked.connect(lambda _=False, app_id=app.id: self.navigator.go(PageId.APPLICATION, application_id=app_id))
        card.body.addWidget(button)
        return card

    def _open_wizard(self) -> None:
        try:
            resources = self.container.resources.list_all()
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
            return
        dialog = CloneWizardDialog(self.container, resources, self)
        if dialog.exec_():
            self.on_enter({})

    def _fail(self, message: str) -> None:
        notify_error(self, message)
