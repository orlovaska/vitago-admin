"""Скрипт запуска админ-панели: venv, зависимости, .env и старт GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
ALIGN_REQUIREMENTS = ROOT / "requirements-align.txt"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def python_bin() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv() -> None:
    if python_bin().exists():
        return
    print("Создаю виртуальное окружение...")
    venv.create(VENV_DIR, with_pip=True)


def ensure_deps() -> None:
    print("Проверяю зависимости...")
    subprocess.check_call(
        [str(python_bin()), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        cwd=ROOT,
    )
    if ALIGN_REQUIREMENTS.exists():
        print("Проверяю зависимости распознавания (Whisper, не озвучка)...")
        subprocess.check_call(
            [str(python_bin()), "-m", "pip", "install", "-r", str(ALIGN_REQUIREMENTS)],
            cwd=ROOT,
        )


def ensure_env() -> None:
    if ENV_FILE.exists():
        return
    if not ENV_EXAMPLE.exists():
        raise SystemExit("Отсутствует .env.example")
    ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    print("Создан .env из .env.example. Задайте API_BASE_URL перед работой.")


def main() -> int:
    os.chdir(ROOT)
    ensure_venv()
    ensure_deps()
    ensure_env()
    return subprocess.call([str(python_bin()), str(ROOT / "main.py")], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
