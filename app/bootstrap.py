from __future__ import annotations

import sys

from PyQt5.QtCore import QtMsgType, qInstallMessageHandler
from PyQt5.QtWidgets import QApplication, QStyleFactory

from app.core.container import Container
from app.core.log import get_logger, setup_logging
from app.presentation.main_window import MainWindow
from app.presentation.widgets.resource_picker import ResourcePicker


class AdminApplication(QApplication):
    def notify(self, receiver, event):  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception:
            get_logger().exception("Необработанное исключение в событии Qt")
            return False


def _qt_message_handler(mode, context, message: str) -> None:
    text = message or ""
    if context is not None and getattr(context, "file", None):
        text = f"{text} ({context.file}:{context.line})"
    logger = get_logger()
    if mode in (QtMsgType.QtFatalMsg, QtMsgType.QtCriticalMsg):
        logger.error("Qt: %s", text)
    elif mode == QtMsgType.QtWarningMsg:
        logger.warning("Qt: %s", text)


class ApplicationFactory:
    """Factory Method: собирает Qt-приложение и главное окно."""

    @staticmethod
    def create() -> tuple[QApplication, MainWindow]:
        setup_logging()
        qInstallMessageHandler(_qt_message_handler)
        qt_app = QApplication.instance() or AdminApplication(sys.argv)
        qt_app.setApplicationName("Vitago Admin")
        qt_app.setOrganizationName("Vitago")
        qt_app.setStyle(QStyleFactory.create("Fusion"))
        container = Container.build()
        ResourcePicker.set_default_fetcher(container.resources.download)
        window = MainWindow(container)
        return qt_app, window
