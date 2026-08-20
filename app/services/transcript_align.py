"""Выравнивание готового транскрипта на аудио (таймкоды без изменения текста).

Логика как у vitago-backend/scripts/align_transcript.py: Whisper (stable-ts)
только расставляет start/end, поле text — точные токены исходного файла.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from app.core.exceptions import AppError
from app.core.paths import project_root

TOKEN_RE = re.compile(r"\S+")
NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)

Cue = dict[str, Any]


@dataclass(frozen=True)
class TranscriptPair:
    stem: str
    audio: Path
    text: Path


@dataclass
class BatchAlignItem:
    stem: str
    cues: list[Cue] | None = None
    error: str | None = None


def tokenize(transcript: str) -> list[str]:
    return TOKEN_RE.findall(transcript)


def normalize(token: str) -> str:
    return NON_WORD_RE.sub("", token).casefold()


def round_time(value: float) -> float:
    return round(float(value), 3)


def parse_cues_json(raw: str | bytes | list[Any]) -> list[Cue]:
    data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
    if not isinstance(data, list):
        raise AppError("JSON таймкодов должен быть массивом")
    cues: list[Cue] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise AppError(f"Элемент [{index}] должен быть объектом")
        try:
            start = float(item["start"])
            end = float(item["end"])
            text = str(item["text"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError(f"Некорректный элемент transcriptCues[{index}]") from exc
        if not text:
            raise AppError(f"Пустой text в transcriptCues[{index}]")
        cues.append({"start": start, "end": end, "text": text})
    return cues


def cues_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def alignment_missing_hint() -> str:
    return (
        "Не найдены библиотеки распознавания. "
        "Пересоберите админку (Сборка exe) или выполните python run.py."
    )


def _quiet_huggingface() -> None:
    import logging
    import os
    import warnings

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    warnings.filterwarnings("ignore", message=".*huggingface_hub.*cache-system uses symlinks.*")
    for name in ("huggingface_hub", "huggingface_hub.utils._http", "huggingface_hub.file_download"):
        logging.getLogger(name).setLevel(logging.ERROR)


def ensure_ffmpeg() -> None:
    """Путь к ffmpeg для утилит. PATH не меняем — иначе PyAV/Whisper падают на Windows."""
    import os
    import shutil
    import sys

    current = os.environ.get("IMAGEIO_FFMPEG_EXE")
    if current and Path(current).is_file():
        return
    which = shutil.which("ffmpeg")
    if which:
        os.environ["IMAGEIO_FFMPEG_EXE"] = which
        return
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "ffmpeg.exe")
    try:
        import imageio_ffmpeg

        candidates.append(Path(imageio_ffmpeg.get_ffmpeg_exe()))
    except Exception:
        pass
    for exe in candidates:
        if exe.is_file():
            os.environ["IMAGEIO_FFMPEG_EXE"] = str(exe)
            return


def _prepare_native_runtime() -> None:
    import os

    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    _quiet_huggingface()
    # ffmpeg не кладём в PATH перед загрузкой модели.


def _proportional(tokens: list[str], start: float, end: float) -> list[Cue]:
    if not tokens:
        return []
    weights = [max(len(token), 1) for token in tokens]
    total = sum(weights)
    duration = max(end - start, 0.0)
    cursor = start
    cues: list[Cue] = []
    for index, token in enumerate(tokens):
        piece = duration * (weights[index] / total) if total else 0.0
        piece_end = end if index == len(tokens) - 1 else cursor + piece
        cues.append({"start": cursor, "end": max(piece_end, cursor), "text": token})
        cursor = cues[-1]["end"]
    return cues


def _map_times_to_original_tokens(tokens: list[str], aligned: list[Cue]) -> list[Cue]:
    if not tokens:
        return []
    if not aligned:
        raise AppError("Распознавание не вернуло слов — проверьте MP3 и что ffmpeg установлен")

    if len(tokens) == len(aligned):
        return [
            {"start": item["start"], "end": item["end"], "text": token}
            for token, item in zip(tokens, aligned)
        ]

    orig_norm = [normalize(token) for token in tokens]
    aligned_norm = [normalize(str(item["text"])) for item in aligned]
    matcher = SequenceMatcher(a=orig_norm, b=aligned_norm, autojunk=False)
    cues: list[Cue | None] = [None] * len(tokens)

    for _tag, i1, i2, j1, j2 in matcher.get_opcodes():
        orig_slice = tokens[i1:i2]
        aligned_slice = aligned[j1:j2]
        if not orig_slice or not aligned_slice:
            continue
        mapped = _proportional(orig_slice, float(aligned_slice[0]["start"]), float(aligned_slice[-1]["end"]))
        for offset, cue in enumerate(mapped):
            cues[i1 + offset] = cue

    filled: list[Cue] = []
    for index, token in enumerate(tokens):
        cue = cues[index]
        if cue is None:
            filled.append({"start": None, "end": None, "text": token})
        else:
            filled.append({"start": cue["start"], "end": cue["end"], "text": token})

    last_end = float(aligned[0]["start"])
    for index, cue in enumerate(filled):
        if cue["start"] is not None:
            last_end = float(cue["end"])
            continue
        next_start = next(
            (float(item["start"]) for item in filled[index + 1 :] if item["start"] is not None),
            float(aligned[-1]["end"]),
        )
        cue["start"] = last_end
        cue["end"] = max(next_start, last_end)
        last_end = float(cue["end"])
    return filled


def _finalize_cues(cues: list[Cue]) -> list[Cue]:
    result: list[Cue] = []
    previous_end = None
    for cue in cues:
        start = round_time(float(cue["start"]))
        if previous_end is not None:
            start = max(start, previous_end)
        end = max(round_time(float(cue["end"])), start)
        result.append({"start": start, "end": end, "text": str(cue["text"])})
        previous_end = end
    return result


def _load_align_model(model_name: str) -> Any:
    from faster_whisper import WhisperModel

    _prepare_native_runtime()
    try:
        return WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8",
            cpu_threads=1,
            num_workers=1,
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError(f"Не удалось загрузить модель распознавания: {exc}") from exc


def _words_from_faster_whisper(model: Any, audio_path: Path, *, language: str, transcript: str) -> list[Cue]:
    prompt = " ".join(tokenize(transcript)[:80])
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=False,
        beam_size=1,
        initial_prompt=prompt or None,
    )
    words: list[Cue] = []
    for segment in segments:
        for word in getattr(segment, "words", None) or []:
            start = getattr(word, "start", None)
            end = getattr(word, "end", None)
            text = getattr(word, "word", None) or ""
            if start is None:
                continue
            start_f = float(start)
            end_f = float(end) if end is not None else start_f
            words.append({"start": start_f, "end": max(end_f, start_f), "text": str(text)})
    return words


def align_transcript_to_cues(
    audio_path: Path,
    transcript: str,
    *,
    language: str = "ru",
    model_name: str = "base",
    model: Any | None = None,
) -> list[Cue]:
    if not cues_available():
        raise AppError(alignment_missing_hint())
    if not audio_path.is_file():
        raise AppError(f"Аудио не найдено: {audio_path}")
    tokens = tokenize(transcript)
    if not tokens:
        raise AppError("Транскрипт пустой")

    _quiet_huggingface()
    # Whisper нельзя грузить в GUI-процессе с PyQt — только в --align-worker.
    align_model = model if model is not None else _load_align_model(model_name)
    aligned = _words_from_faster_whisper(align_model, audio_path, language=language, transcript=transcript)
    if not aligned:
        raise AppError("Распознавание не вернуло слов — проверьте MP3")
    cues = _finalize_cues(_map_times_to_original_tokens(tokens, aligned))
    if [cue["text"] for cue in cues] != tokens:
        raise AppError("Внутренняя ошибка: токены транскрипта изменились")
    return cues


def _validate_pair_paths(audio_path: Path, text_path: Path) -> None:
    if audio_path.suffix.lower() != ".mp3":
        raise AppError("Аудио должно быть в формате MP3 (.mp3)")
    if text_path.suffix.lower() != ".txt":
        raise AppError("Транскрипт должен быть текстовым файлом (.txt)")
    if audio_path.stem != text_path.stem:
        raise AppError(
            f"Имена файлов должны совпадать: «{audio_path.stem}.mp3» и «{audio_path.stem}.txt»"
        )
    if not text_path.is_file():
        raise AppError(f"Транскрипт не найден: {text_path}")


def align_files(
    audio_path: Path,
    text_path: Path,
    *,
    language: str = "ru",
    model_name: str = "base",
    model: Any | None = None,
) -> list[Cue]:
    _validate_pair_paths(audio_path, text_path)
    transcript = text_path.read_text(encoding="utf-8-sig")
    return align_transcript_to_cues(
        audio_path,
        transcript,
        language=language,
        model_name=model_name,
        model=model,
    )


def _pick_unique(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]
    by_parent: dict[Path, list[Path]] = {}
    for path in paths:
        by_parent.setdefault(path.parent, []).append(path)
    singles = [items[0] for items in by_parent.values() if len(items) == 1]
    if len(singles) == 1:
        return singles[0]
    return None


def match_transcript_pairs(paths: Iterable[Path]) -> tuple[list[TranscriptPair], list[str]]:
    """Сопоставляет *.mp3 и *.txt по одинаковому имени (без расширения)."""
    mp3_by_stem: dict[str, list[Path]] = {}
    txt_by_stem: dict[str, list[Path]] = {}
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        stem = path.stem
        if suffix == ".mp3":
            mp3_by_stem.setdefault(stem, []).append(path.resolve())
        elif suffix == ".txt":
            txt_by_stem.setdefault(stem, []).append(path.resolve())

    pairs: list[TranscriptPair] = []
    warnings: list[str] = []
    for stem in sorted(set(mp3_by_stem) | set(txt_by_stem)):
        audio = _pick_unique(mp3_by_stem.get(stem, []))
        text = _pick_unique(txt_by_stem.get(stem, []))
        mp3_count = len(mp3_by_stem.get(stem, []))
        txt_count = len(txt_by_stem.get(stem, []))
        if audio is None and mp3_count:
            warnings.append(f"{stem}: несколько MP3 ({mp3_count}), пропущено")
            continue
        if text is None and txt_count:
            warnings.append(f"{stem}: несколько TXT ({txt_count}), пропущено")
            continue
        if audio is None:
            warnings.append(f"{stem}.txt без парного MP3")
            continue
        if text is None:
            warnings.append(f"{stem}.mp3 без парного TXT")
            continue
        pairs.append(TranscriptPair(stem=stem, audio=audio, text=text))
    return pairs, warnings


def match_pairs_in_directory(directory: Path) -> tuple[list[TranscriptPair], list[str]]:
    root = Path(directory)
    if not root.is_dir():
        raise AppError(f"Папка не найдена: {root}")
    return match_transcript_pairs(root.rglob("*"))


def write_pair_cues(pair: TranscriptPair, cues: list[Cue]) -> Path:
    path = pair.audio.with_name(f"{pair.stem}-cues.json")
    path.write_text(json.dumps(cues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def align_batch(
    pairs: list[TranscriptPair],
    *,
    language: str = "ru",
    model_name: str = "base",
    on_progress: Callable[..., Any] | None = None,
) -> list[BatchAlignItem]:
    if not pairs:
        raise AppError("Нет пар MP3+TXT для распознавания")
    if not cues_available():
        raise AppError(alignment_missing_hint())
    model = _load_align_model(model_name)
    results: list[BatchAlignItem] = []
    total = len(pairs)
    for index, pair in enumerate(pairs, start=1):
        if on_progress is not None:
            on_progress({"type": "start", "stem": pair.stem, "index": index, "total": total})
        try:
            cues = align_files(
                pair.audio,
                pair.text,
                language=language,
                model_name=model_name,
                model=model,
            )
            saved = write_pair_cues(pair, cues)
            item = BatchAlignItem(stem=pair.stem, cues=cues)
            results.append(item)
            if on_progress is not None:
                on_progress(
                    {
                        "type": "ok",
                        "stem": pair.stem,
                        "index": index,
                        "total": total,
                        "words": len(cues),
                        "file": saved.name,
                    }
                )
        except Exception as exc:  # noqa: BLE001 — собираем ошибки по файлам
            results.append(BatchAlignItem(stem=pair.stem, error=str(exc)))
            if on_progress is not None:
                on_progress(
                    {
                        "type": "err",
                        "stem": pair.stem,
                        "index": index,
                        "total": total,
                        "error": str(exc),
                    }
                )
    return results


def write_cues_zip(items: list[BatchAlignItem], zip_path: Path) -> int:
    ok = [item for item in items if item.cues is not None]
    if not ok:
        raise AppError("Нет успешных JSON для архива")
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in ok:
            payload = json.dumps(item.cues, ensure_ascii=False, indent=2) + "\n"
            archive.writestr(f"{item.stem}-cues.json", payload)
        failed = [item for item in items if item.error]
        if failed:
            report = "\n".join(f"{item.stem}: {item.error}" for item in failed) + "\n"
            archive.writestr("errors.txt", report)
    return len(ok)


def run_align_worker(work_dir: Path | str) -> int:
    """Точка входа дочернего процесса: падение здесь не роняет GUI-админку."""
    work = Path(work_dir)
    progress_path = work / "progress.ndjson"

    def emit(event: dict[str, Any]) -> None:
        with progress_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()

    try:
        job = json.loads((work / "job.json").read_text(encoding="utf-8-sig"))
        pairs = [
            TranscriptPair(stem=str(item["stem"]), audio=Path(item["audio"]), text=Path(item["text"]))
            for item in job.get("pairs") or []
        ]
        results = align_batch(
            pairs,
            language=str(job.get("language") or "ru"),
            model_name=str(job.get("model_name") or "base"),
            on_progress=emit,
        )
        (work / "result.json").write_text(
            json.dumps(
                {
                    "ok": True,
                    "items": [
                        {
                            "stem": item.stem,
                            "error": item.error,
                            "words": len(item.cues or []),
                        }
                        for item in results
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        emit({"type": "err", "stem": "*", "index": 0, "total": 0, "error": str(exc)})
        (work / "result.json").write_text(
            json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
            encoding="utf-8",
        )
        return 1


def _drain_progress(path: Path, done: int, on_progress: Callable[..., Any] | None) -> int:
    if not path.is_file():
        return done
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if text and not text.endswith(("\n", "\r")):
        lines = lines[:-1]
    for line in lines[done:]:
        raw = line.strip()
        if not raw or on_progress is None:
            continue
        try:
            on_progress(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return len(lines)


def align_batch_isolated(
    pairs: list[TranscriptPair],
    *,
    language: str = "ru",
    model_name: str = "base",
    on_progress: Callable[..., Any] | None = None,
) -> list[BatchAlignItem]:
    """Распознавание в отдельном процессе — нативный краш Whisper не убивает админку."""
    if not pairs:
        raise AppError("Нет пар MP3+TXT для распознавания")
    if not cues_available():
        raise AppError(alignment_missing_hint())

    work = Path(tempfile.mkdtemp(prefix="vitago-align-"))
    progress_path = work / "progress.ndjson"
    progress_path.write_text("", encoding="utf-8")
    (work / "job.json").write_text(
        json.dumps(
            {
                "language": language,
                "model_name": model_name,
                "pairs": [
                    {"stem": pair.stem, "audio": str(pair.audio), "text": str(pair.text)}
                    for pair in pairs
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    worker_log = work / "worker.log"
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--align-worker", str(work)]
        cwd = str(Path(sys.executable).resolve().parent)
    else:
        command = [sys.executable, str(project_root() / "main.py"), "--align-worker", str(work)]
        cwd = str(project_root())

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

    seen_ok: dict[str, dict[str, Any]] = {}
    seen_err: dict[str, dict[str, Any]] = {}

    def capture(event: dict[str, Any]) -> None:
        kind = event.get("type")
        stem = str(event.get("stem") or "")
        if kind == "ok" and stem:
            seen_ok[stem] = event
        elif kind == "err" and stem and stem != "*":
            seen_err[stem] = event
        if on_progress is not None:
            on_progress(event)

    proc: subprocess.Popen[str] | None = None
    code = 1
    crash_detail = ""
    log_handle = worker_log.open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        done = 0
        while proc.poll() is None:
            done = _drain_progress(progress_path, done, capture)
            time.sleep(0.2)
        done = _drain_progress(progress_path, done, capture)
        code = int(proc.returncode or 0)
    finally:
        log_handle.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
        if worker_log.is_file():
            try:
                crash_detail = worker_log.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                crash_detail = ""
        shutil.rmtree(work, ignore_errors=True)

    if code != 0 and on_progress is not None:
        message = "Процесс распознавания аварийно завершился. Уже сохранённые JSON рядом с MP3 остались."
        if crash_detail:
            message = f"{message}\n{crash_detail[-1000:]}"
        on_progress(
            {
                "type": "err",
                "stem": "*",
                "index": 0,
                "total": len(pairs),
                "error": message,
            }
        )

    results: list[BatchAlignItem] = []
    for pair in pairs:
        cues_path = pair.audio.with_name(f"{pair.stem}-cues.json")
        if pair.stem in seen_ok and cues_path.is_file():
            try:
                cues = parse_cues_json(cues_path.read_text(encoding="utf-8-sig"))
                results.append(BatchAlignItem(stem=pair.stem, cues=cues))
                continue
            except Exception as exc:  # noqa: BLE001
                results.append(BatchAlignItem(stem=pair.stem, error=str(exc)))
                continue
        if pair.stem in seen_err:
            results.append(BatchAlignItem(stem=pair.stem, error=str(seen_err[pair.stem].get("error") or "Ошибка")))
            continue
        if code != 0:
            results.append(
                BatchAlignItem(
                    stem=pair.stem,
                    error="Аварийное завершение процесса распознавания",
                )
            )
        else:
            results.append(BatchAlignItem(stem=pair.stem, error="Не обработано"))
    return results
