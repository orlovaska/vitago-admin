"""Сборка Windows .exe через PyInstaller."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from run import ROOT, ensure_deps, ensure_venv, python_bin

SPEC = ROOT / "vitago-admin.spec"
BUILD_REQUIREMENTS = ROOT / "requirements-build.txt"
DIST_DIR = ROOT / "dist"
EXE_NAME = "VitagoAdmin.exe"


def ensure_build_deps() -> None:
    print("Проверяю зависимости сборки...")
    subprocess.check_call(
        [str(python_bin()), "-m", "pip", "install", "-r", str(BUILD_REQUIREMENTS)],
        cwd=ROOT,
    )


def build_exe() -> Path:
    print("Собираю exe...")
    subprocess.check_call(
        [
            str(python_bin()),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(SPEC),
        ],
        cwd=ROOT,
    )
    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        raise SystemExit(f"Сборка завершилась, но файл не найден: {exe_path}")
    example = ROOT / ".env.example"
    if example.exists():
        shutil.copy2(example, DIST_DIR / ".env.example")
        shutil.copy2(example, DIST_DIR / ".env")
    return exe_path


def main() -> int:
    if not SPEC.exists():
        raise SystemExit(f"Не найден spec: {SPEC}")
    ensure_venv()
    ensure_deps()
    ensure_build_deps()
    exe_path = build_exe()
    print(f"Готово: {exe_path}")
    print("Готово: рядом с exe уже есть .env с API_BASE_URL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
