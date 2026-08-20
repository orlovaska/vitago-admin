from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QWidget,
)

from app.core.container import Container
from app.presentation.navigation import NavigationMediator
from app.presentation.pages.base import ScrollPage
from app.presentation.widgets.common import Card, GhostButton, PageHeader, PrimaryButton, notify_error, notify_info
from app.services.transcript_align import (
    BatchAlignItem,
    TranscriptPair,
    alignment_missing_hint,
    align_batch_isolated,
    cues_available,
    match_pairs_in_directory,
    match_transcript_pairs,
    write_cues_zip,
)

INSTRUCTIONS = (
    "Здесь только распознавание таймкодов: TXT накладывается на MP3, текст не меняется.\n"
    "1. «Выбрать папку» или «Выбрать файлы» — пары name.mp3 + name.txt сопоставятся сами.\n"
    "2. В списке отметьте нужные пары (по умолчанию все).\n"
    "3. Модель распознавания (base — обычный выбор).\n"
    "4. «Распознать»: лог идёт по файлам. Каждый успешный JSON сразу пишется рядом с MP3.\n"
    "5. ZIP можно скачать отдельно, если нужен архив всех готовых JSON."
)


class TranscriptAlignPage(ScrollPage):
    """Пакетное выравнивание: папка/файлы MP3+TXT → JSON таймкодов."""

    def __init__(self, container: Container, navigator: NavigationMediator, parent: QWidget | None = None) -> None:
        super().__init__(container, navigator, parent)
        self._pairs: list[TranscriptPair] = []
        self._results: list[BatchAlignItem] = []
        self._source_dir: Path | None = None
        self._running = False
        self._settings = QSettings("Vitago", "AdminPanel")

        self.content_layout.addWidget(
            PageHeader(
                "Распознавание транскрипции",
                "MP3+TXT с одинаковыми именами → JSON таймкодов. Озвучки нет.",
            )
        )

        card = Card()
        self.howto = QLabel(INSTRUCTIONS)
        self.howto.setObjectName("muted")
        self.howto.setWordWrap(True)

        self.model = QComboBox()
        for value, title in (
            ("tiny", "tiny — быстрее, грубее"),
            ("base", "base — баланс (по умолчанию)"),
            ("small", "small — точнее, медленнее"),
            ("medium", "medium — ещё точнее, дольше"),
        ):
            self.model.addItem(title, value)
        self.model.setCurrentIndex(1)
        model_hint = (
            "Модель распознавания Whisper: чем больше, тем точнее таймкоды, "
            "но дольше считается."
        )
        self.model.setToolTip(model_hint)
        model_label = QLabel("Модель распознавания")
        model_label.setToolTip(model_hint)

        pick_dir = PrimaryButton("Выбрать папку")
        pick_files = GhostButton("Выбрать файлы")
        pick_dir.clicked.connect(self._pick_directory)
        pick_files.clicked.connect(self._pick_files)
        self._pick_dir = pick_dir
        self._pick_files = pick_files

        check_all = GhostButton("Все")
        check_none = GhostButton("Снять все")
        check_all.clicked.connect(lambda: self._set_all_checked(True))
        check_none.clicked.connect(lambda: self._set_all_checked(False))

        self.pair_list = QListWidget()
        self.pair_list.setMinimumHeight(180)
        self.pair_list.setSelectionMode(QListWidget.NoSelection)

        self.run_btn = PrimaryButton("Распознать")
        self.run_btn.clicked.connect(self._run_batch)
        save = GhostButton("Скачать ZIP")
        save.clicked.connect(self._save_zip)

        self.status = QLabel("Пары не выбраны")
        self.status.setWordWrap(True)

        self.hint = QLabel()
        self.hint.setObjectName("muted")
        self.hint.setWordWrap(True)
        self._refresh_hint()

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(200)
        self.log.setPlaceholderText("Лог обработки появится здесь")

        model_row = QHBoxLayout()
        model_row.addWidget(model_label)
        model_row.addWidget(self.model)
        model_row.addStretch()

        actions = QHBoxLayout()
        actions.addWidget(pick_dir)
        actions.addWidget(pick_files)
        actions.addStretch()

        list_actions = QHBoxLayout()
        list_actions.addWidget(QLabel("Пары"))
        list_actions.addWidget(check_all)
        list_actions.addWidget(check_none)
        list_actions.addStretch()

        run_row = QHBoxLayout()
        run_row.addWidget(self.run_btn)
        run_row.addWidget(save)
        run_row.addStretch()

        card.body.addWidget(self.howto)
        card.body.addLayout(model_row)
        card.body.addLayout(actions)
        card.body.addLayout(list_actions)
        card.body.addWidget(self.pair_list)
        card.body.addWidget(self.status)
        card.body.addWidget(self.hint)
        card.body.addLayout(run_row)
        card.body.addWidget(self.log)
        self.content_layout.addWidget(card)

    def _on_busy(self, busy: bool, text: str) -> None:
        if busy and text:
            self.status.setText(text)

    def on_enter(self, payload: dict[str, Any]) -> None:
        self._refresh_hint()
        if self._pairs or self._running:
            return
        last = str(self._settings.value("transcriptAlign/lastDir", "") or "")
        if not last:
            return
        root = Path(last)
        if not root.is_dir():
            return
        try:
            pairs, warnings = match_pairs_in_directory(root)
        except Exception:
            return
        if pairs:
            self._set_pairs(pairs, warnings, source=str(root))

    def _refresh_hint(self) -> None:
        if cues_available():
            self.hint.setText(
                "Распознавание идёт в фоне в отдельном процессе — можно переключаться "
                "по разделам админки. Успешный JSON сразу пишется рядом с MP3."
            )
        else:
            self.hint.setText(alignment_missing_hint())

    def _log(self, line: str) -> None:
        self.log.appendPlainText(line)
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.Checked if checked else Qt.Unchecked
        for index in range(self.pair_list.count()):
            self.pair_list.item(index).setCheckState(state)

    def _checked_pairs(self) -> list[TranscriptPair]:
        selected: list[TranscriptPair] = []
        for index in range(self.pair_list.count()):
            item = self.pair_list.item(index)
            if item.checkState() != Qt.Checked:
                continue
            pair = item.data(Qt.UserRole)
            if isinstance(pair, TranscriptPair):
                selected.append(pair)
        return selected

    def _set_running(self, running: bool) -> None:
        self._running = running
        self.run_btn.setEnabled(not running)
        self.run_btn.setText("Идёт распознавание…" if running else "Распознать")
        # Папку не меняем посреди прогона, остальное приложение свободно.
        self._pick_dir.setEnabled(not running)
        self._pick_files.setEnabled(not running)

    def _set_pairs(self, pairs: list[TranscriptPair], warnings: list[str], *, source: str) -> None:
        self._pairs = pairs
        self._results = []
        self._source_dir = Path(source) if source else None
        if self._source_dir is not None:
            self._settings.setValue("transcriptAlign/lastDir", str(self._source_dir))
        self.pair_list.clear()
        for pair in pairs:
            item = QListWidgetItem(f"{pair.stem}.mp3  ↔  {pair.stem}.txt")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, pair)
            self.pair_list.addItem(item)
        self.log.clear()
        self._log(f"Источник: {source}")
        self._log(f"Найдено пар: {len(pairs)} (все отмечены)")
        if warnings:
            self._log("Без пары / пропущено:")
            for item in warnings:
                self._log(f"  • {item}")
        self.status.setText(f"Пар: {len(pairs)}" + (f", предупреждений: {len(warnings)}" if warnings else ""))
        if not pairs:
            notify_error(self, "Не найдено ни одной пары name.mp3 + name.txt")
        else:
            notify_info(self, f"Сопоставлено пар: {len(pairs)}")

    def _pick_directory(self) -> None:
        if self._running:
            return
        path = QFileDialog.getExistingDirectory(self, "Папка с MP3 и TXT")
        if not path:
            return
        root = Path(path)
        try:
            pairs, warnings = match_pairs_in_directory(root)
        except Exception as exc:  # noqa: BLE001
            notify_error(self, str(exc))
            return
        self._set_pairs(pairs, warnings, source=str(root))

    def _pick_files(self) -> None:
        if self._running:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "MP3 и TXT",
            "",
            "MP3 и TXT (*.mp3 *.txt)",
        )
        if not paths:
            return
        pairs, warnings = match_transcript_pairs(Path(item) for item in paths)
        parent = str(Path(paths[0]).parent)
        self._set_pairs(pairs, warnings, source=parent)

    def _run_batch(self) -> None:
        if self._running:
            return
        pairs = self._checked_pairs()
        if not pairs:
            notify_error(self, "Отметьте хотя бы одну пару")
            return
        model = str(self.model.currentData() or "base")
        self._results = []
        self._log("")
        self._log(f"Старт: {len(pairs)} из {self.pair_list.count()} (можно пользоваться другими разделами)")
        self._set_running(True)
        self.status.setText(f"Обработка 0/{len(pairs)}")

        self.tasks.submit(
            align_batch_isolated,
            self._on_batch_done,
            self._on_batch_failed,
            pairs,
            model_name=model,
            on_progress=self._on_progress,
            busy_text=None,
        )

    def _on_progress(self, event: object) -> None:
        if not isinstance(event, dict):
            return
        kind = event.get("type")
        index = event.get("index")
        total = event.get("total")
        stem = event.get("stem")
        prefix = f"[{index}/{total}]"
        if kind == "start":
            self.status.setText(f"Обрабатывается {stem}.mp3 ({index}/{total})")
            self._log(f"{prefix} Обрабатывается {stem}.mp3 …")
        elif kind == "ok":
            self.status.setText(f"Готово {stem}.mp3 ({index}/{total})")
            self._log(f"{prefix} Корректно — {event.get('file')} ({event.get('words')} слов)")
        elif kind == "err":
            if stem == "*":
                self._log(f"{event.get('error')}")
                return
            self.status.setText(f"Ошибка {stem}.mp3 ({index}/{total})")
            self._log(f"{prefix} Ошибка {stem}: {event.get('error')}")

    def _on_batch_failed(self, message: str) -> None:
        self._set_running(False)
        self._log(f"Остановлено: {message}")
        if any(item.cues is not None for item in self._results):
            self._log("Уже сохранённые JSON рядом с MP3 не трогались.")
        notify_error(self, message)

    def _on_batch_done(self, results: list[BatchAlignItem]) -> None:
        self._results = results
        self._set_running(False)
        ok = [item for item in results if item.cues is not None]
        failed = [item for item in results if item.error]
        self.status.setText(f"Готово: {len(ok)} успешно, ошибок: {len(failed)}")
        self._log(f"Итого: успешно {len(ok)}, ошибок {len(failed)}. JSON лежит рядом с MP3.")
        if not ok:
            notify_error(self, "Ни одна пара не обработана успешно")
            return
        notify_info(self, f"Сохранено {len(ok)} JSON рядом с аудио")

    def _save_zip(self) -> None:
        if not any(item.cues is not None for item in self._results):
            notify_error(self, "Нет успешных JSON для архива")
            return
        suggested = "transcript-cues.zip"
        if self._source_dir is not None:
            suggested = str(self._source_dir / "transcript-cues.zip")
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить ZIP с JSON", suggested, "ZIP (*.zip)")
        if not path:
            return
        try:
            count = write_cues_zip(self._results, Path(path))
        except Exception as extra:  # noqa: BLE001
            notify_error(self, str(extra))
            return
        notify_info(self, f"Архив сохранён ({count} JSON): {path}")
