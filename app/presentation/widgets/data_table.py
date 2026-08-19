from __future__ import annotations

from collections.abc import Sequence

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QGuiApplication, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QHeaderView,
    QMenu,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

_SETTINGS_ORG = "Vitago"
_SETTINGS_APP = "AdminPanel"
_KEY_PREFIX = "tableColumns/"
_MIN_WIDTH = 24


class DataTable(QTableWidget):
    def __init__(self, headers: Sequence[str], parent: QWidget | None = None, *, name: str = "") -> None:
        super().__init__(0, len(headers), parent)
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        self._store_key = _KEY_PREFIX + (name or "|".join(headers))
        self._restoring = False
        self.setHorizontalHeaderLabels(list(headers))
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setVisible(True)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.sectionResized.connect(self._on_section_resized)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_copy_menu)
        if not self._restore_widths():
            header.setStretchLastSection(True)

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
        self._restore_widths()

    def selected_ids(self) -> list[object]:
        rows = sorted({index.row() for index in self.selectionModel().selectedIndexes()})
        if not rows and self.currentRow() >= 0:
            rows = [self.currentRow()]
        ids: list[object] = []
        seen: set[object] = set()
        for row in rows:
            item = self.item(row, 0)
            if item is None:
                continue
            value = item.data(Qt.UserRole)
            if value in seen:
                continue
            seen.add(value)
            ids.append(value)
        return ids

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
            return
        super().keyPressEvent(event)

    def copy_selection(self) -> None:
        text = self._selection_text()
        if text:
            QGuiApplication.clipboard().setText(text)

    def _show_copy_menu(self, pos) -> None:
        index = self.indexAt(pos)
        if index.isValid():
            self.setCurrentCell(index.row(), index.column())
        menu = QMenu(self)
        copy_action = QAction("Копировать", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selection)
        copy_action.setEnabled(bool(self._selection_text()))
        menu.addAction(copy_action)
        menu.exec_(self.viewport().mapToGlobal(pos))

    def _selection_text(self) -> str:
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            item = self.currentItem()
            return item.text() if item is not None else ""
        rows = sorted({index.row() for index in indexes})
        cols = sorted({index.column() for index in indexes})
        selected = {(index.row(), index.column()) for index in indexes}
        lines: list[str] = []
        for row in rows:
            cells: list[str] = []
            for col in cols:
                if (row, col) not in selected:
                    cells.append("")
                    continue
                item = self.item(row, col)
                cells.append(item.text() if item is not None else "")
            lines.append("\t".join(cells))
        return "\n".join(lines)

    def _on_section_resized(self, _index: int, _old: int, _new: int) -> None:
        if self._restoring or not self.isVisible():
            return
        self._save_widths()

    def _save_widths(self) -> None:
        widths = [self.columnWidth(index) for index in range(self.columnCount())]
        if len(widths) != self.columnCount() or any(width < _MIN_WIDTH for width in widths):
            return
        self._settings.setValue(self._store_key, widths)

    def _restore_widths(self) -> bool:
        widths = _as_int_list(self._settings.value(self._store_key))
        if widths is None or len(widths) != self.columnCount():
            return False
        if any(width < _MIN_WIDTH for width in widths):
            return False
        self._restoring = True
        self.horizontalHeader().setStretchLastSection(False)
        try:
            for index, width in enumerate(widths):
                self.setColumnWidth(index, width)
        finally:
            self._restoring = False
        return True


def _as_int_list(raw: object) -> list[int] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
        try:
            return [int(part) for part in parts]
        except ValueError:
            return None
    try:
        return [int(item) for item in list(raw)]  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
