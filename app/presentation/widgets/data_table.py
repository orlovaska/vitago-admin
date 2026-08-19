from __future__ import annotations

from collections.abc import Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget


class DataTable(QTableWidget):
    def __init__(self, headers: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(0, len(headers), parent)
        self.setHorizontalHeaderLabels(list(headers))
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.setSortingEnabled(True)

    def set_rows(self, rows: list[list[str]], ids: list[object] | None = None) -> None:
        self.setSortingEnabled(False)
        self.setRowCount(0)
        self.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col, value in enumerate(row):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if ids is not None:
                    item.setData(Qt.UserRole, ids[row_index])
                self.setItem(row_index, col, item)
        self.setSortingEnabled(True)

    def selected_ids(self) -> list[object]:
        ids: list[object] = []
        for index in self.selectionModel().selectedRows():
            item = self.item(index.row(), 0)
            if item is not None:
                ids.append(item.data(Qt.UserRole))
        return ids
