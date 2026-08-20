from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication, QStyleFactory

from app.core.container import Container
from app.presentation.main_window import MainWindow
from app.presentation.widgets.resource_picker import ResourcePicker


class ApplicationFactory:
    """Factory Method: собирает Qt-приложение и главное окно."""

    @staticmethod
    def create() -> tuple[QApplication, MainWindow]:
        qt_app = QApplication.instance() or QApplication(sys.argv)
        qt_app.setApplicationName("Vitago Admin")
        qt_app.setOrganizationName("Vitago")
        qt_app.setStyle(QStyleFactory.create("Fusion"))
        container = Container.build()
        ResourcePicker.set_default_fetcher(container.resources.download)
        window = MainWindow(container)
        return qt_app, window
