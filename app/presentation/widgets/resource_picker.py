from __future__ import annotations

import threading
from collections.abc import Callable

from PyQt5.QtCore import (
    QBuffer,
    QByteArray,
    QEvent,
    QObject,
    QSortFilterProxyModel,
    QTimer,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QPlainTextEdit,
    QSizePolicy,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.log import get_logger
from app.domain.enums import MimeType
from app.domain.models import Resource

Fetcher = Callable[[int], tuple[bytes, str]]
_LIST_ROWS = 8


class _ResourceComboBox(QComboBox):
    """Редактор без нативного popup: он забирает фокус и гасит каретку."""

    query_changed = pyqtSignal(str)
    popup_requested = pyqtSignal()
    focus_left = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._query: str | None = None
        self._from_list = False
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setCompleter(None)
        edit = self.lineEdit()
        edit.setPlaceholderText("Поиск по имени файла...")
        edit.setCompleter(None)
        edit.textEdited.connect(self._on_text_edited)
        edit.returnPressed.connect(self.commit_query)
        edit.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if watched is self.lineEdit() and event.type() == QEvent.FocusOut:
            self.focus_left.emit()
        return super().eventFilter(watched, event)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()

    def showPopup(self) -> None:  # type: ignore[override]
        self.popup_requested.emit()

    def hidePopup(self) -> None:  # type: ignore[override]
        return

    def pick_row(self, row: int) -> None:
        self._from_list = True
        self._query = None
        self.setCurrentIndex(row)
        self._sync_edit()

    def commit_query(self) -> None:
        if self._query is None:
            return
        query = self._query
        self._query = None
        if not self._from_list:
            best = self.best_match_row(query)
            if best is not None:
                self.setCurrentIndex(best)
        self._from_list = False
        self._sync_edit()

    def best_match_row(self, query: str) -> int | None:
        needle = query.strip().casefold()
        if not needle:
            return self.currentIndex()
        exact: list[int] = []
        prefix: list[int] = []
        contains: list[int] = []
        for row in range(self.count()):
            label = self.itemText(row).casefold()
            if label == needle:
                exact.append(row)
            elif label.startswith(needle):
                prefix.append(row)
            elif needle in label:
                contains.append(row)
        for group in (exact, prefix, contains):
            if group:
                return min(group, key=lambda row: (len(self.itemText(row)), row))
        return None

    def _on_text_edited(self, text: str) -> None:
        self._from_list = False
        self._query = text
        self.query_changed.emit(text)

    def _sync_edit(self) -> None:
        index = self.currentIndex()
        text = self.itemText(index) if index >= 0 else ""
        edit = self.lineEdit()
        if edit.text() != text:
            edit.setText(text)
        edit.setCursorPosition(len(text))


class _FetchSignals(QObject):
    finished = pyqtSignal(int, int, bytes, str)
    failed = pyqtSignal(int, int, str)


class _ImagePreview(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(120)

    def set_data(self, data: bytes) -> None:
        pm = QPixmap()
        pm.loadFromData(data)
        if pm.isNull():
            get_logger(__name__).warning("Не удалось декодировать изображение")
            self.setText("Не удалось загрузить")
            return
        scaled = pm.scaled(
            self.width() or 240, self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)


class _AudioPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = b""
        self._player: QMediaPlayer | None = None
        self._qbuf: QBuffer | None = None
        self._qba: QByteArray | None = None

        self._play_btn = QToolButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._play_btn.clicked.connect(self._toggle)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.sliderMoved.connect(self._seek)

        self._time = QLabel("0:00")
        self._time.setFixedWidth(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._time)

    def set_data(self, data: bytes) -> None:
        self.shutdown()
        self._data = data

    def _ensure_player(self) -> QMediaPlayer | None:
        if not self._data:
            return None
        if self._player is not None:
            return self._player
        self._qba = QByteArray(self._data)
        self._qbuf = QBuffer(self)
        self._qbuf.setData(self._qba)
        self._qbuf.open(QBuffer.ReadOnly)
        player = QMediaPlayer(self)
        player.positionChanged.connect(self._on_position)
        player.durationChanged.connect(lambda d: self._slider.setRange(0, d))
        player.stateChanged.connect(self._on_state)
        player.setMedia(QMediaContent(), self._qbuf)
        self._player = player
        return player

    def _toggle(self) -> None:
        player = self._ensure_player()
        if player is None:
            return
        if player.state() == QMediaPlayer.PlayingState:
            player.pause()
            return
        player.play()

    def _seek(self, position: int) -> None:
        if self._player is not None:
            self._player.setPosition(position)

    def _on_position(self, ms: int) -> None:
        self._slider.setValue(ms)
        secs = ms // 1000
        self._time.setText(f"{secs // 60}:{secs % 60:02d}")

    def _on_state(self, state: int) -> None:
        icon = QStyle.SP_MediaPause if state == QMediaPlayer.PlayingState else QStyle.SP_MediaPlay
        self._play_btn.setIcon(self.style().standardIcon(icon))

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()

    def shutdown(self) -> None:
        player = self._player
        self._player = None
        if player is None:
            return
        player.stop()
        player.setMedia(QMediaContent())
        app = QApplication.instance()
        if app is not None:
            app.processEvents()
        player.deleteLater()
        if self._qbuf is not None:
            self._qbuf.close()
            self._qbuf = None
        self._qba = None


class ResourcePicker(QWidget):
    """Выбор ресурса с автоматическим превью рядом с селектом."""

    changed = pyqtSignal(object)
    _default_fetcher: Fetcher | None = None

    @classmethod
    def set_default_fetcher(cls, fn: Fetcher) -> None:
        cls._default_fetcher = fn

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._resources: list[Resource] = []
        self._mime: MimeType | None = None
        self._fetcher: Fetcher | None = self._default_fetcher
        self._generation = 0
        self._closed = False
        self._signals = _FetchSignals(self)
        self._signals.finished.connect(self._on_fetched)
        self._signals.failed.connect(self._on_fetch_error)

        self._combo = _ResourceComboBox()
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_changed)
        self._combo.query_changed.connect(self._on_query)
        self._combo.popup_requested.connect(self._on_arrow)
        self._combo.focus_left.connect(self._on_focus_left)

        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setSourceModel(self._combo.model())
        self._list = QListView()
        self._list.setModel(self._proxy)
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list.clicked.connect(self._on_list_clicked)
        self._list.hide()

        self._preview_area = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_area)
        self._preview_layout.setContentsMargins(0, 4, 0, 0)
        self._preview_area.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._combo)
        layout.addWidget(self._list)
        layout.addWidget(self._preview_area)

    def set_fetcher(self, fn: Fetcher) -> None:
        self._fetcher = fn

    def set_resources(self, resources: list[Resource], mime: MimeType | None = None) -> None:
        current = self.value()
        self._resources = resources
        self._mime = mime
        self._hide_list()
        self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItem("— не выбран —", None)
        filtered = [item for item in resources if mime is None or item.mime_type == mime.value]
        for item in filtered:
            self._combo.addItem(f"{item.file_name}  (#{item.resource_id})", item.resource_id)
        self.set_value(current)
        self._combo.blockSignals(False)
        self._load_preview()

    def set_value(self, resource_id: int | None) -> None:
        if resource_id is None:
            self._combo.setCurrentIndex(0)
            return
        index = self._combo.findData(resource_id)
        self._combo.setCurrentIndex(index if index >= 0 else 0)

    def value(self) -> int | None:
        data = self._combo.currentData()
        return int(data) if data is not None else None

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        signals = self._signals
        try:
            signals.finished.disconnect(self._on_fetched)
            signals.failed.disconnect(self._on_fetch_error)
        except TypeError:
            pass
        signals.setParent(None)
        QTimer.singleShot(12_000, signals.deleteLater)
        self._stop_audio()
        self._clear_preview()

    def _on_query(self, text: str) -> None:
        self._proxy.setFilterFixedString(text)
        self._show_list()

    def _on_arrow(self) -> None:
        if self._list.isVisible() and self._combo._query is None:
            self._hide_list()
            return
        self._show_list()

    def _on_list_clicked(self, index) -> None:
        source = self._proxy.mapToSource(index)
        if source.isValid():
            self._combo.pick_row(source.row())
        self._hide_list()

    def _on_focus_left(self) -> None:
        QTimer.singleShot(0, self._commit_if_left)

    def _commit_if_left(self) -> None:
        focus = QApplication.focusWidget()
        if focus is not None and (focus is self or self.isAncestorOf(focus)):
            return
        self._combo.commit_query()
        self._hide_list()

    def _show_list(self) -> None:
        rows = max(1, min(_LIST_ROWS, self._proxy.rowCount()))
        row_h = self._list.sizeHintForRow(0)
        if row_h <= 0:
            row_h = 28
        self._list.setFixedHeight(rows * row_h + 4)
        if self._proxy.rowCount() > 0:
            self._list.setCurrentIndex(self._proxy.index(0, 0))
        self._list.show()

    def _hide_list(self) -> None:
        self._proxy.setFilterFixedString("")
        self._list.hide()

    def _on_changed(self) -> None:
        self.changed.emit(self.value())
        self._load_preview()

    def _load_preview(self) -> None:
        if self._closed:
            return
        self._stop_audio()
        self._clear_preview()
        rid = self.value()
        if rid is None or self._fetcher is None:
            self._preview_area.hide()
            return
        self._generation += 1
        generation = self._generation
        loading = QLabel("Загрузка…")
        loading.setAlignment(Qt.AlignCenter)
        self._preview_layout.addWidget(loading)
        self._preview_area.show()
        self._fetch(rid, generation)

    def _fetch(self, rid: int, generation: int) -> None:
        fetcher = self._fetcher
        if fetcher is None:
            return

        def work() -> None:
            try:
                data, content_type = fetcher(rid)
                self._signals.finished.emit(generation, rid, data, content_type)
            except Exception as exc:  # noqa: BLE001
                get_logger(__name__).exception("Не удалось загрузить ресурс #%s", rid)
                self._signals.failed.emit(generation, rid, str(exc))

        threading.Thread(target=work, daemon=True, name=f"resource-preview-{rid}").start()

    def _on_fetched(self, generation: int, rid: int, data: bytes, content_type: str) -> None:
        if self._closed or generation != self._generation or self.value() != rid:
            return
        self._clear_preview()
        mime = self._selected_mime() or content_type
        if "image" in mime:
            widget = _ImagePreview()
            widget.set_data(data)
            self._preview_layout.addWidget(widget)
        elif "audio" in mime:
            widget = _AudioPreview()
            widget.set_data(data)
            self._preview_layout.addWidget(widget)
        elif "pdf" in mime:
            lbl = QLabel("PDF-документ. Просмотр не поддерживается.")
            lbl.setWordWrap(True)
            self._preview_layout.addWidget(lbl)
        elif "json" in mime:
            try:
                import json as _json
                text = _json.dumps(_json.loads(data.decode("utf-8")), ensure_ascii=False, indent=2)
            except Exception:
                get_logger(__name__).warning("Не удалось разобрать JSON ресурса", exc_info=True)
                text = data.decode("utf-8", errors="replace")
            edit = QPlainTextEdit()
            edit.setReadOnly(True)
            edit.setPlainText(text[:4000])
            edit.setMaximumHeight(160)
            self._preview_layout.addWidget(edit)
        else:
            lbl = QLabel(f"Тип: {content_type}. Предпросмотр не поддерживается.")
            lbl.setWordWrap(True)
            self._preview_layout.addWidget(lbl)
        self._preview_area.show()

    def _on_fetch_error(self, generation: int, rid: int, msg: str) -> None:
        if self._closed or generation != self._generation or self.value() != rid:
            return
        self._clear_preview()
        lbl = QLabel(f"Ошибка: {msg}")
        lbl.setWordWrap(True)
        self._preview_layout.addWidget(lbl)
        self._preview_area.show()

    def _selected_mime(self) -> str:
        rid = self.value()
        if rid is None:
            return ""
        for item in self._resources:
            if item.resource_id == rid:
                return item.mime_type
        return ""

    def _stop_audio(self) -> None:
        for i in range(self._preview_layout.count()):
            widget = self._preview_layout.itemAt(i).widget()
            if isinstance(widget, _AudioPreview):
                widget.shutdown()

    def _clear_preview(self) -> None:
        while self._preview_layout.count():
            item = self._preview_layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if isinstance(widget, _AudioPreview):
                widget.shutdown()
            widget.deleteLater()
