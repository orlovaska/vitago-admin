from __future__ import annotations

import sys

from PyQt5.QtWidgets import QApplication

from app.core.container import Container
from app.presentation.main_window import MainWindow


class ApplicationFactory:
    """Factory Method: собирает Qt-приложение и главное окно."""

    @staticmethod
    def create() -> tuple[QApplication, MainWindow]:
        qt_app = QApplication.instance() or QApplication(sys.argv)
        qt_app.setApplicationName("Vitago Admin")
        qt_app.setOrganizationName("Vitago")
        container = Container.build()
        window = MainWindow(container)
        return qt_app, window
