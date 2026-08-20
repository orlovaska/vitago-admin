from __future__ import annotations

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QKeySequence, QShowEvent
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QShortcut,
    QSizePolicy,
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
from app.presentation.pages.promocodes import PromocodesPage
from app.presentation.pages.resources import ResourcesPage
from app.presentation.pages.reviews import ReviewsPage
from app.presentation.pages.secrets import SecretsPage
from app.presentation.pages.server_resources import ServerResourcesPage
from app.presentation.pages.transcript_align import TranscriptAlignPage
from app.presentation.theme.apply import apply_appearance
from app.presentation.theme.scale import (
    DEFAULT_UI_SCALE,
    UI_SCALE_STEPS,
    next_ui_scale,
    normalize_ui_scale,
    prev_ui_scale,
    scale_px,
)
from app.presentation.widgets.common import GhostButton, confirm


NAV_ITEMS = (
    (PageId.DASHBOARD, "Контент маршрутов"),
    (PageId.PROMOCODES, "Промокоды"),
    (PageId.RESOURCES, "Ресурсы"),
    (PageId.SERVER_RESOURCES, "Ресурсы на сервере"),
    (PageId.REVIEWS, "Отзывы"),
    (PageId.GENERATE_ROUTE, "GeoJSON"),
    (PageId.TRANSCRIPT_ALIGN, "Транскрипция"),
    (PageId.SECRETS, "Секреты сервера"),
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
        self._ui_scale = normalize_ui_scale(self._settings.value("uiScale", DEFAULT_UI_SCALE))

        self.setWindowTitle("Vitago Admin")
        self.resize(1280, 840)

        self.stack = QStackedWidget()
        self.pages = {
            PageId.LOGIN: LoginPage(container, self.navigator),
            PageId.DASHBOARD: DashboardPage(container, self.navigator),
            PageId.APPLICATION: ApplicationPage(container, self.navigator),
            PageId.PROMOCODES: PromocodesPage(container, self.navigator),
            PageId.RESOURCES: ResourcesPage(container, self.navigator),
            PageId.SERVER_RESOURCES: ServerResourcesPage(container, self.navigator),
            PageId.REVIEWS: ReviewsPage(container, self.navigator),
            PageId.GENERATE_ROUTE: GenerateRoutePage(container, self.navigator),
            PageId.TRANSCRIPT_ALIGN: TranscriptAlignPage(container, self.navigator),
            PageId.SECRETS: SecretsPage(container, self.navigator),
            PageId.ENV: EnvPage(container, self.navigator),
        }
        self._index = {page_id: self.stack.addWidget(page) for page_id, page in self.pages.items()}

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(self.sidebar)
        brand = QLabel("Vitago\nAdmin")
        brand.setObjectName("pageTitle")
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.nav.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        for page_id, title in NAV_ITEMS:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, page_id)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav)
        self.theme_button = GhostButton("Тема: тёмная")
        self.theme_button.clicked.connect(self._toggle_theme)
        self.zoom_out_button = GhostButton("−")
        self.zoom_out_button.setToolTip("Уменьшить интерфейс (Ctrl+−)")
        self.zoom_out_button.clicked.connect(self._zoom_out)
        self.zoom_in_button = GhostButton("+")
        self.zoom_in_button.setToolTip("Увеличить интерфейс (Ctrl+=)")
        self.zoom_in_button.clicked.connect(self._zoom_in)
        self.scale_label = QLabel()
        self.scale_label.setObjectName("muted")
        self.scale_label.setAlignment(Qt.AlignCenter)
        zoom_row = QWidget()
        zoom_layout = QHBoxLayout(zoom_row)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(6)
        zoom_layout.addWidget(self.zoom_out_button)
        zoom_layout.addWidget(self.scale_label, 1)
        zoom_layout.addWidget(self.zoom_in_button)
        self.logout_button = GhostButton("Выйти")
        self.logout_button.clicked.connect(self._logout)
        side_layout.addWidget(brand)
        side_layout.addSpacing(12)
        side_layout.addWidget(self.nav, 1)
        side_layout.addWidget(self.theme_button)
        side_layout.addWidget(zoom_row)
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
        self._bind_zoom_shortcuts()
        self._apply_theme()
        if self.container.session.is_authenticated:
            self.navigator.go(self._restore_page())
        else:
            self.navigator.go(PageId.LOGIN)

    def _restore_page(self) -> PageId:
        raw = str(self._settings.value("lastPage", PageId.DASHBOARD.value) or PageId.DASHBOARD.value)
        try:
            page = PageId(raw)
        except ValueError:
            return PageId.DASHBOARD
        if page is PageId.LOGIN or page not in self._index:
            return PageId.DASHBOARD
        return page

    def _on_navigate(self, command: NavigateCommand) -> None:
        if command.page_id is not PageId.LOGIN and not self.container.session.is_authenticated:
            self.stack.setCurrentIndex(self._index[PageId.LOGIN])
            self.sidebar.hide()
            return
        self.sidebar.setVisible(command.page_id is not PageId.LOGIN)
        self.stack.setCurrentIndex(self._index[command.page_id])
        self.pages[command.page_id].enter(command.payload)
        if command.page_id is not PageId.LOGIN:
            self._settings.setValue("lastPage", command.page_id.value)
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

    def _bind_zoom_shortcuts(self) -> None:
        for sequence, handler in (
            (QKeySequence.ZoomIn, self._zoom_in),
            (QKeySequence("Ctrl+="), self._zoom_in),
            (QKeySequence.ZoomOut, self._zoom_out),
            (QKeySequence("Ctrl+0"), self._zoom_reset),
        ):
            shortcut = QShortcut(sequence, self)
            shortcut.activated.connect(handler)

    def _on_session(self, authenticated: bool) -> None:
        if not authenticated:
            self.navigator.go(PageId.LOGIN)

    def _toggle_theme(self) -> None:
        self._theme = ThemeMode.LIGHT if self._theme is ThemeMode.DARK else ThemeMode.DARK
        self._settings.setValue("themeMode", self._theme.value)
        self._apply_theme()

    def _zoom_in(self) -> None:
        self._set_ui_scale(next_ui_scale(self._ui_scale))

    def _zoom_out(self) -> None:
        self._set_ui_scale(prev_ui_scale(self._ui_scale))

    def _zoom_reset(self) -> None:
        self._set_ui_scale(DEFAULT_UI_SCALE)

    def _set_ui_scale(self, percent: int) -> None:
        value = normalize_ui_scale(percent)
        if value == self._ui_scale:
            self._refresh_scale_label()
            return
        self._ui_scale = value
        self._settings.setValue("uiScale", value)
        self._apply_theme()

    def _apply_theme(self) -> None:
        apply_appearance(self, self._theme, self._ui_scale)
        self.sidebar.setFixedWidth(scale_px(220, self._ui_scale))
        self.theme_button.setText("Тема: светлая" if self._theme is ThemeMode.LIGHT else "Тема: тёмная")
        self._refresh_scale_label()

    def _refresh_scale_label(self) -> None:
        self.scale_label.setText(f"{self._ui_scale}%")
        self.zoom_out_button.setEnabled(self._ui_scale > UI_SCALE_STEPS[0])
        self.zoom_in_button.setEnabled(self._ui_scale < UI_SCALE_STEPS[-1])

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._apply_theme()

    def _logout(self) -> None:
        if not confirm(self, "Выход из аккаунта", "Выйти из аккаунта?"):
            return
        self.container.session.clear()
        self.navigator.go(PageId.LOGIN)
