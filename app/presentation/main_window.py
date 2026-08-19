from __future__ import annotations

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.container import Container
from app.domain.enums import PageId, ThemeMode
from app.presentation.navigation import NavigateCommand, NavigationMediator
from app.presentation.pages.application import ApplicationPage
from app.presentation.pages.dashboard import DashboardPage
from app.presentation.pages.env import EnvPage
from app.presentation.pages.generate_route import GenerateRoutePage
from app.presentation.pages.login import LoginPage
from app.presentation.pages.resources import ResourcesPage
from app.presentation.pages.reviews import ReviewsPage
from app.presentation.theme.palette import Palette
from app.presentation.theme.stylesheet import build_stylesheet
from app.presentation.theme.title_bar import apply_title_bar
from app.presentation.widgets.common import GhostButton


NAV_ITEMS = (
    (PageId.DASHBOARD, "Гиды-клоны"),
    (PageId.RESOURCES, "Ресурсы"),
    (PageId.REVIEWS, "Отзывы"),
    (PageId.GENERATE_ROUTE, "GeoJSON"),
    (PageId.ENV, "Переменные .env"),
)


class MainWindow(QMainWindow):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self.container = container
        self.navigator = NavigationMediator()
        self._settings = QSettings("Vitago", "AdminPanel")
        saved = str(self._settings.value("themeMode", ThemeMode.DARK.value))
        self._theme = ThemeMode.DARK if saved != ThemeMode.LIGHT.value else ThemeMode.LIGHT

        self.setWindowTitle("Vitago Admin")
        self.resize(1280, 840)

        self.stack = QStackedWidget()
        self.pages = {
            PageId.LOGIN: LoginPage(container, self.navigator),
            PageId.DASHBOARD: DashboardPage(container, self.navigator),
            PageId.APPLICATION: ApplicationPage(container, self.navigator),
            PageId.RESOURCES: ResourcesPage(container, self.navigator),
            PageId.REVIEWS: ReviewsPage(container, self.navigator),
            PageId.GENERATE_ROUTE: GenerateRoutePage(container, self.navigator),
            PageId.ENV: EnvPage(container, self.navigator),
        }
        self._index = {page_id: self.stack.addWidget(page) for page_id, page in self.pages.items()}

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(self.sidebar)
        brand = QLabel("Vitago\nAdmin")
        brand.setObjectName("pageTitle")
        brand.setStyleSheet("color: white; font-size: 18px; font-weight: 700;")
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        for page_id, title in NAV_ITEMS:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, page_id)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.theme_button = GhostButton("Тема: тёмная")
        self.theme_button.clicked.connect(self._toggle_theme)
        self.logout_button = GhostButton("Выйти")
        self.logout_button.clicked.connect(self._logout)
        side_layout.addWidget(brand)
        side_layout.addSpacing(12)
        side_layout.addWidget(self.nav)
        side_layout.addStretch()
        side_layout.addWidget(self.theme_button)
        side_layout.addWidget(self.logout_button)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self.navigator.navigated.connect(self._on_navigate)
        self.container.session.changed.connect(self._on_session)
        self._apply_theme()
        if self.container.session.is_authenticated:
            self.navigator.go(PageId.DASHBOARD)
        else:
            self.navigator.go(PageId.LOGIN)

    def _on_navigate(self, command: NavigateCommand) -> None:
        if command.page_id is not PageId.LOGIN and not self.container.session.is_authenticated:
            self.stack.setCurrentIndex(self._index[PageId.LOGIN])
            self.sidebar.hide()
            return
        self.sidebar.setVisible(command.page_id is not PageId.LOGIN)
        self.stack.setCurrentIndex(self._index[command.page_id])
        self.pages[command.page_id].enter(command.payload)
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if item.data(Qt.UserRole) is command.page_id:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(row)
                self.nav.blockSignals(False)
                break

    def _on_nav(self, row: int) -> None:
        if row < 0:
            return
        page_id = self.nav.item(row).data(Qt.UserRole)
        if page_id:
            self.navigator.go(page_id)

    def _on_session(self, authenticated: bool) -> None:
        if not authenticated:
            self.navigator.go(PageId.LOGIN)

    def _toggle_theme(self) -> None:
        self._theme = ThemeMode.LIGHT if self._theme is ThemeMode.DARK else ThemeMode.DARK
        self._settings.setValue("themeMode", self._theme.value)
        self._apply_theme()

    def _apply_theme(self) -> None:
        palette = Palette.for_mode(self._theme)
        self.setStyleSheet(build_stylesheet(palette))
        self.theme_button.setText("Тема: светлая" if self._theme is ThemeMode.LIGHT else "Тема: тёмная")
        apply_title_bar(self, self._theme, palette)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        apply_title_bar(self, self._theme, Palette.for_mode(self._theme))

    def _logout(self) -> None:
        self.container.session.clear()
        self.navigator.go(PageId.LOGIN)
