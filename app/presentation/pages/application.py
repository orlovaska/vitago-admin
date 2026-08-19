from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QWidget
from PyQt5.QtGui import QGuiApplication

from app.core.container import Container
from app.domain.enums import PageId
from app.domain.models import Application, Resource
from app.presentation.dialogs.point_dialog import PointDialog
from app.presentation.dialogs.promocode_dialog import PromocodeDialog
from app.presentation.dialogs.route_dialog import RouteDialog
from app.presentation.dialogs.version_dialog import VersionDialog
from app.presentation.forms.application_form import ApplicationForm
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import ScrollPage
from app.presentation.widgets.common import (
    Card,
    DangerButton,
    GhostButton,
    PageHeader,
    PrimaryButton,
    StatusDot,
    confirm,
    notify_error,
    notify_info,
)
from app.services.points_validator import to_import_payload, validate_points_json


class ApplicationPage(ScrollPage):
    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._app_id: int | None = None
        self._application: Application | None = None
        self._resources: list[Resource] = []

        back = GhostButton("← Назад")
        back.clicked.connect(lambda: self.navigator.go(PageId.DASHBOARD))
        self.header = PageHeader("Приложение")
        self.content_layout.addWidget(back, alignment=Qt.AlignLeft)
        self.content_layout.addWidget(self.header)
        self.info_card = Card()
        self.versions_card = Card()
        self.routes_card = Card()
        self.content_layout.addWidget(self.info_card)
        self.content_layout.addWidget(self.versions_card)
        self.content_layout.addWidget(self.routes_card)
        self.content_layout.addStretch()

    def on_enter(self, payload: dict[str, Any]) -> None:
        self._app_id = int(payload.get("application_id") or 0)
        if not self._app_id:
            notify_error(self, "ID приложения не указан")
            return
        self.tasks.submit(self._load, self._render, lambda msg: notify_error(self, msg))

    def _load(self) -> tuple[Application, list[Resource]]:
        return self.container.applications.get(self._app_id), self.container.resources.list_all()

    def _render(self, result: tuple[Application, list[Resource]]) -> None:
        application, resources = result
        self._application = application
        self._resources = resources
        self.header.title_label.setText(application.bundle_id)
        self._fill_info(application)
        self._fill_versions(application)
        self._fill_routes(application)

    def _clear(self, card: Card) -> None:
        while card.body.count():
            item = card.body.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _fill_info(self, app: Application) -> None:
        self._clear(self.info_card)
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(QLabel(f"Bundle ID: {app.bundle_id}"))
        row_layout.addWidget(QLabel(f"Custom Scheme: {app.custom_scheme}"))
        if app.payment_service_postfix:
            row_layout.addWidget(QLabel(f"Постфикс: {app.payment_service_postfix}"))
        row_layout.addStretch()
        self.info_card.body.addWidget(row)

        payments = QWidget()
        payments_layout = QHBoxLayout(payments)
        payments_layout.setContentsMargins(0, 0, 0, 0)
        for label, field, value in (
            ("Google Play", "usePaymentGooglePlay", app.use_payment_google_play),
            ("App Store", "usePaymentAppStore", app.use_payment_app_store),
            ("RuStore", "usePaymentRuStore", app.use_payment_ru_store),
        ):
            btn = GhostButton(f"{'Выключить' if value else 'Включить'} {label}")
            btn.clicked.connect(lambda _=False, f=field, v=value, name=label: self._toggle_payment(f, not v, name))
            payments_layout.addWidget(StatusDot(value, label))
            payments_layout.addWidget(btn)
        payments_layout.addStretch()
        self.info_card.body.addWidget(payments)

        if app.redirect_urls.success_url:
            for caption, url in (
                ("Success", app.redirect_urls.success_url),
                ("Fail", app.redirect_urls.fail_url),
                ("Go to site", app.redirect_urls.go_to_our_site_url),
            ):
                self.info_card.body.addWidget(self._copy_row(caption, url))

        edit = PrimaryButton("Редактировать ресурсы")
        delete = DangerButton("Удалить приложение")
        edit.clicked.connect(self._edit_resources)
        delete.clicked.connect(self._delete_app)
        self.info_card.body.addWidget(edit, alignment=Qt.AlignLeft)
        self.info_card.body.addWidget(delete, alignment=Qt.AlignLeft)

    def _copy_row(self, caption: str, url: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(f"{caption}: {url}")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy = GhostButton("Копировать")
        copy.clicked.connect(lambda: QGuiApplication.clipboard().setText(url))
        layout.addWidget(label)
        layout.addWidget(copy)
        layout.addStretch()
        return row

    def _fill_versions(self, app: Application) -> None:
        self._clear(self.versions_card)
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Версии приложения")
        title.setObjectName("sectionTitle")
        add = PrimaryButton("Добавить версию")
        add.clicked.connect(self._add_version)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(add)
        self.versions_card.body.addWidget(header)
        if not app.versions:
            self.versions_card.body.addWidget(QLabel("Версии не найдены"))
            return
        for version in app.versions:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(f"{version.label}  ·  пользователей: {version.user_count}"))
            delete = GhostButton("Удалить")
            delete.clicked.connect(lambda _=False, vid=version.id, label=version.label: self._delete_version(vid, label))
            row_layout.addStretch()
            row_layout.addWidget(delete)
            self.versions_card.body.addWidget(row)

    def _fill_routes(self, app: Application) -> None:
        self._clear(self.routes_card)
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Маршрут")
        title.setObjectName("sectionTitle")
        add = PrimaryButton("Добавить маршрут")
        add.setEnabled(len(app.routes) == 0)
        add.setToolTip("Для клонов можно добавить только один маршрут")
        add.clicked.connect(self._add_route)
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(add)
        self.routes_card.body.addWidget(header)
        if not app.routes:
            self.routes_card.body.addWidget(QLabel("Маршруты не найдены"))
            return
        route = app.routes[0]
        self.routes_card.body.addWidget(QLabel(route.route_name))
        self.routes_card.body.addWidget(QLabel(route.description))
        self.routes_card.body.addWidget(QLabel(f"Город: {route.city}  ·  Цена: {route.price_rub:.2f} ₽  ·  Точек: {len(route.points)}"))
        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        edit = PrimaryButton("Редактировать")
        delete = DangerButton("Удалить")
        edit.clicked.connect(lambda: self._edit_route(route.id))
        delete.clicked.connect(lambda: self._delete_route(route.id, route.route_name))
        actions_layout.addWidget(edit)
        actions_layout.addWidget(delete)
        actions_layout.addStretch()
        self.routes_card.body.addWidget(actions)

        self.routes_card.body.addWidget(QLabel("Точки маршрута"))
        add_point = PrimaryButton("Добавить точку")
        add_point.clicked.connect(lambda: self._edit_point(route.id))
        import_points = GhostButton("Импорт из JSON")
        import_points.clicked.connect(lambda: self._import_points(route.id))
        self.routes_card.body.addWidget(add_point, alignment=Qt.AlignLeft)
        self.routes_card.body.addWidget(import_points, alignment=Qt.AlignLeft)
        for point in sorted(route.points, key=lambda item: item.level):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(f"{point.level}. {point.name}"))
            edit_p = GhostButton("Изменить")
            del_p = GhostButton("Удалить")
            edit_p.clicked.connect(lambda _=False, p=point, rid=route.id: self._edit_point(rid, p))
            del_p.clicked.connect(lambda _=False, p=point: self._delete_point(p))
            row_layout.addStretch()
            row_layout.addWidget(edit_p)
            row_layout.addWidget(del_p)
            self.routes_card.body.addWidget(row)

        self.routes_card.body.addWidget(QLabel("Промокоды"))
        add_promo = PrimaryButton("Добавить промокод")
        add_promo.clicked.connect(lambda: self._add_promo(route.id))
        self.routes_card.body.addWidget(add_promo, alignment=Qt.AlignLeft)
        try:
            promocodes = self.container.promocodes.list_by_route(route.id)
        except Exception as exc:  # noqa: BLE001
            self.routes_card.body.addWidget(QLabel(str(exc)))
            return
        for promo in promocodes:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            status = "активен" if promo.is_active else "выключен"
            row_layout.addWidget(QLabel(f"{promo.code}  ·  {promo.discount_percent}%  ·  {status}"))
            copy = GhostButton("Копировать ссылку")
            regen = GhostButton("Новый токен")
            delete = GhostButton("Удалить")
            copy.clicked.connect(lambda _=False, url=promo.deeplink_url: self._copy(url))
            regen.clicked.connect(lambda _=False, pid=promo.id: self._regen(pid))
            delete.clicked.connect(lambda _=False, pid=promo.id: self._delete_promo(pid))
            row_layout.addStretch()
            row_layout.addWidget(copy)
            row_layout.addWidget(regen)
            row_layout.addWidget(delete)
            self.routes_card.body.addWidget(row)

    def _toggle_payment(self, field: str, value: bool, store: str) -> None:
        action = "включить" if value else "выключить"
        if not confirm(self, "Подтверждение изменения", f"Вы точно хотите {action} оплату в {store}?"):
            return
        try:
            self.container.applications.update_payment_flag(self._app_id, field, value)
            notify_info(self, "Флаги оплаты успешно обновлены")
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _edit_resources(self) -> None:
        if not self._application:
            return
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

        editor = QDialog(self)
        editor.setWindowTitle("Редактировать приложение")
        form = ApplicationForm()
        form.set_resources(self._resources)
        form.bundle_id.setText(self._application.bundle_id)
        form.custom_scheme.setText(self._application.custom_scheme)
        form.payment_postfix.setText(self._application.payment_service_postfix or "")
        form.support_chat_url.setText(self._application.support_chat_url or "")
        form.terms.set_value(self._application.terms_resource_id)
        form.acc_recovery.set_value(self._application.acc_recovery_image_resource_id)
        form.gif.set_value(self._application.gif_resource_id)
        for widget in (
            form.bundle_id,
            form.custom_scheme,
            form.payment_postfix,
            form.support_chat_url,
            form.google_play,
            form.app_store,
            form.ru_store,
        ):
            widget.setEnabled(False)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout = QVBoxLayout(editor)
        layout.addWidget(form)
        layout.addWidget(buttons)
        buttons.rejected.connect(editor.reject)

        def save() -> None:
            try:
                self.container.applications.update_resources(
                    self._application.id,
                    {
                        "termsResourceId": form.terms.value(),
                        "accRecoveryImageResourceId": form.acc_recovery.value(),
                        "gifResourceId": form.gif.value(),
                    },
                )
                editor.accept()
                notify_info(self, "Приложение успешно обновлено")
                self.on_enter({"application_id": self._app_id})
            except Exception as exc:  # noqa: BLE001
                notify_error(self, str(exc))

        buttons.accepted.connect(save)
        editor.exec_()

    def _delete_app(self) -> None:
        if not self._application:
            return
        if not confirm(self, "Подтверждение удаления", f"Удалить приложение {self._application.bundle_id}?"):
            return
        try:
            self.container.applications.delete(self._application.id)
            notify_info(self, "Приложение успешно удалено")
            self.navigator.go(PageId.DASHBOARD)
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _add_version(self) -> None:
        latest = self._application.versions[-1] if self._application and self._application.versions else None
        dialog = VersionDialog(self.container, self._app_id, latest, self)
        if dialog.exec_():
            self.on_enter({"application_id": self._app_id})

    def _delete_version(self, version_id: int, label: str) -> None:
        if not confirm(self, "Подтверждение удаления", f"Удалить версию {label}?"):
            return
        try:
            self.container.applications.delete_version(self._app_id, version_id)
            notify_info(self, "Версия успешно удалена")
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _add_route(self) -> None:
        dialog = RouteDialog(self.container, self._resources, self._app_id, parent=self)
        if dialog.exec_():
            self.on_enter({"application_id": self._app_id})

    def _edit_route(self, route_id: int) -> None:
        dialog = RouteDialog(self.container, self._resources, self._app_id, route_id=route_id, parent=self)
        if dialog.exec_():
            self.on_enter({"application_id": self._app_id})

    def _delete_route(self, route_id: int, name: str) -> None:
        if not confirm(self, "Подтверждение удаления", f"Удалить маршрут {name}?"):
            return
        try:
            self.container.routes.delete(route_id)
            notify_info(self, "Маршрут успешно удален")
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _import_points(self, route_id: int) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Импорт точек", "", "JSON (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            notify_error(self, f"Ошибка при чтении JSON файла: {exc}")
            return
        result = validate_points_json(data)
        if not result.is_valid:
            notify_error(self, "\n".join(result.errors[:12]))
            return
        if result.unknown_fields:
            notify_info(self, "Неизвестные поля будут проигнорированы: " + ", ".join(result.unknown_fields))
        try:
            count = self.container.points.import_from_json(route_id, [to_import_payload(item) for item in data])
            notify_info(self, f"Успешно импортировано точек: {count}")
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _edit_point(self, route_id: int, point=None) -> None:
        dialog = PointDialog(self.container, self._resources, route_id, point=point, parent=self)
        if dialog.exec_():
            self.on_enter({"application_id": self._app_id})

    def _delete_point(self, point) -> None:
        if not point.id:
            return
        if not confirm(self, "Подтверждение удаления", f"Удалить точку {point.name}?"):
            return
        try:
            self.container.points.delete(point.id)
            notify_info(self, "Точка успешно удалена")
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _add_promo(self, route_id: int) -> None:
        dialog = PromocodeDialog(self.container, route_id, self)
        if dialog.exec_():
            self.on_enter({"application_id": self._app_id})

    def _copy(self, url: str | None) -> None:
        if not url:
            notify_error(self, "Ссылка недоступна")
            return
        QGuiApplication.clipboard().setText(url)
        notify_info(self, "Ссылка скопирована")

    def _regen(self, promocode_id: int) -> None:
        try:
            self.container.promocodes.regenerate_token(promocode_id)
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))

    def _delete_promo(self, promocode_id: int) -> None:
        if not confirm(self, "Удаление", "Удалить промокод?"):
            return
        try:
            self.container.promocodes.delete(promocode_id)
            self.on_enter({"application_id": self._app_id})
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
