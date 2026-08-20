from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.paths import project_root

LOGGER_NAME = "vitago.admin"
_LOG_DIR = "logs"
_LOG_FILE = "vitago-admin.log"
_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 5
_HANDLER_FLAG = "_vitago_admin_file"


def logs_dir() -> Path:
    path = project_root() / _LOG_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_file_path() -> Path:
    return logs_dir() / _LOG_FILE


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(name or LOGGER_NAME)


def setup_logging() -> Path:
    """Пишет WARNING+ в logs/vitago-admin.log рядом с приложением."""
    path = log_file_path()
    root = logging.getLogger()
    if any(getattr(handler, _HANDLER_FLAG, False) for handler in root.handlers):
        return path

    handler = RotatingFileHandler(
        path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    setattr(handler, _HANDLER_FLAG, True)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(logging.WARNING)
    logging.captureWarnings(True)

    sys.excepthook = _handle_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception
    return path


def log_error(message: str) -> None:
    get_logger().error("%s", message, exc_info=sys.exc_info()[1] is not None)


def log_warning(message: str) -> None:
    get_logger().warning("%s", message, exc_info=sys.exc_info()[1] is not None)


def _handle_exception(exc_type: type[BaseException], exc: BaseException, tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    get_logger().error("Необработанное исключение", exc_info=(exc_type, exc, tb))


def _handle_thread_exception(args) -> None:
    get_logger().error(
        "Необработанное исключение в потоке",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
