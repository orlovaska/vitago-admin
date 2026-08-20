from __future__ import annotations

from collections.abc import Callable

from PyQt5.QtCore import QBuffer, QByteArray, QObject, QThread, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSizePolicy,
    QSlider,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.domain.enums import MimeType
from app.domain.models import Resource

Fetcher = Callable[[int], tuple[bytes, str]]


class _FetchWorker(QObject):
    finished = pyqtSignal(bytes, str)
    failed = pyqtSignal(str)

    def __init__(self, fetcher: Fetcher, resource_id: int) -> None:
        super().__init__()
        self._fetcher = fetcher
        self.resource_id = resource_id

    def run(self) -> None:
        try:
            data, content_type = self._fetcher(self.resource_id)
            self.finished.emit(data, content_type)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _ImagePreview(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(120)

    def set_data(self, data: bytes) -> None:
        pm = QPixmap()
        pm.loadFromData(data)
        if pm.isNull():
            self.setText("Не удалось загрузить")
            return
        scaled = pm.scaled(
            self.width() or 240, self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.setPixmap(scaled)


class _AudioPreview(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._qbuf: QBuffer | None = None

        self._play_btn = QToolButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self._play_btn.clicked.connect(self._toggle)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 0)
        self._slider.sliderMoved.connect(self._player.setPosition)

        self._time = QLabel("0:00")
        self._time.setFixedWidth(44)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._time)

        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(lambda d: self._slider.setRange(0, d))
        self._player.stateChanged.connect(self._on_state)

    def set_data(self, data: bytes) -> None:
        qba = QByteArray(data)
        self._qbuf = QBuffer(self)
        self._qbuf.setData(qba)
        self._qbuf.open(QBuffer.ReadOnly)
        self._player.setMedia(QMediaContent(), self._qbuf)

    def _toggle(self) -> None:
        if self._player.state() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_position(self, ms: int) -> None:
        self._slider.setValue(ms)
        secs = ms // 1000
        self._time.setText(f"{secs // 60}:{secs % 60:02d}")

    def _on_state(self, state: int) -> None:
        icon = QStyle.SP_MediaPause if state == QMediaPlayer.PlayingState else QStyle.SP_MediaPlay
        self._play_btn.setIcon(self.style().standardIcon(icon))

    def stop(self) -> None:
        self._player.stop()


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
        self._fetch_thread: QThread | None = None
        self._loading_rid: int | None = None

        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.setInsertPolicy(QComboBox.NoInsert)
        self._combo.lineEdit().setPlaceholderText("Поиск по имени файла...")
        self._combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._combo.currentIndexChanged.connect(self._on_changed)

        self._preview_area = QWidget()
        self._preview_layout = QVBoxLayout(self._preview_area)
        self._preview_layout.setContentsMargins(0, 4, 0, 0)
        self._preview_area.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._combo)
        layout.addWidget(self._preview_area)

    def set_fetcher(self, fn: Fetcher) -> None:
        self._fetcher = fn

    def set_resources(self, resources: list[Resource], mime: MimeType | None = None) -> None:
        current = self.value()
        self._resources = resources
        self._mime = mime
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

    def _on_changed(self) -> None:
        self.changed.emit(self.value())
        self._load_preview()

    def _load_preview(self) -> None:
        self._stop_audio()
        self._clear_preview()
        rid = self.value()
        if rid is None or self._fetcher is None:
            self._preview_area.hide()
            return
        if rid == self._loading_rid:
            return
        self._loading_rid = rid
        loading = QLabel("Загрузка…")
        loading.setAlignment(Qt.AlignCenter)
        self._preview_layout.addWidget(loading)
        self._preview_area.show()
        self._fetch(rid)

    def _fetch(self, rid: int) -> None:
        fetcher = self._fetcher
        if fetcher is None:
            return
        thread = QThread(self)
        worker = _FetchWorker(fetcher, rid)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda data, ct, r=rid: self._on_fetched(data, ct, r))
        worker.failed.connect(lambda msg, r=rid: self._on_fetch_error(msg, r))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_thread(thread, worker))
        self._fetch_thread = thread
        thread.start()

    def _cleanup_thread(self, thread: QThread, worker: _FetchWorker) -> None:
        worker.deleteLater()
        thread.deleteLater()
        if self._fetch_thread is thread:
            self._fetch_thread = None

    def _on_fetched(self, data: bytes, content_type: str, rid: int) -> None:
        if self.value() != rid:
            return
        self._loading_rid = None
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

    def _on_fetch_error(self, msg: str, rid: int) -> None:
        if self.value() != rid:
            return
        self._loading_rid = None
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
                widget.stop()

    def _clear_preview(self) -> None:
        while self._preview_layout.count():
            item = self._preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
