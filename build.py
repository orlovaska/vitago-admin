"""Сборка Windows .exe через PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from run import ROOT, ensure_venv, python_bin

SPEC = ROOT / "vitago-admin.spec"
BUILD_REQUIREMENTS = ROOT / "requirements-build.txt"
DIST_DIR = ROOT / "dist"
EXE_NAME = "VitagoAdmin.exe"
EXE_PATH = DIST_DIR / "VitagoAdmin" / EXE_NAME


def ensure_build_deps() -> None:
    probe = subprocess.run(
        [str(python_bin()), "-c", "import PyQt5, requests, dotenv, PyInstaller"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode == 0:
        return
    print("Ставлю зависимости сборки...")
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    subprocess.check_call(
        [str(python_bin()), "-m", "pip", "install", "-q", "-r", str(BUILD_REQUIREMENTS)],
        cwd=ROOT,
        env=env,
    )


def pyinstaller_args(clean: bool) -> list[str]:
    args = [str(python_bin()), "-m", "PyInstaller", "--noconfirm", str(SPEC)]
    if clean:
        args.insert(-1, "--clean")
    return args


def build_exe(clean: bool) -> Path:
    print("Собираю exe...")
    subprocess.check_call(pyinstaller_args(clean), cwd=ROOT)
    if not EXE_PATH.exists():
        raise SystemExit(f"Сборка завершилась, но файл не найден: {EXE_PATH}")
    example = ROOT / ".env.example"
    if example.exists():
        shutil.copy2(example, EXE_PATH.parent / ".env.example")
        target_env = EXE_PATH.parent / ".env"
        if not target_env.exists():
            shutil.copy2(example, target_env)
    ssh_dir = ROOT / ".ssh"
    if ssh_dir.is_dir():
        shutil.copytree(ssh_dir, EXE_PATH.parent / ".ssh", dirs_exist_ok=True)
    return EXE_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Сборка Vitago Admin")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Полная пересборка без кэша PyInstaller (медленнее)",
    )
    args = parser.parse_args()
    if not SPEC.exists():
        raise SystemExit(f"Не найден spec: {SPEC}")
    ensure_venv()
    ensure_build_deps()
    exe_path = build_exe(clean=args.clean)
    print(f"Готово: {exe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
