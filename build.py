"""Сборка Windows .exe через PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from run import ROOT, ensure_venv, python_bin

SPEC = ROOT / "vitago-admin.spec"
BUILD_REQUIREMENTS = ROOT / "requirements-build.txt"
ALIGN_REQUIREMENTS = ROOT / "requirements-align.txt"
DIST_DIR = ROOT / "dist"
EXE_NAME = "VitagoAdmin.exe"
EXE_PATH = DIST_DIR / "VitagoAdmin" / EXE_NAME


def stop_running_exe() -> None:
    """Закрывает запущенный VitagoAdmin, иначе PyInstaller не сможет очистить dist/."""
    if sys.platform != "win32":
        return
    probe = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {EXE_NAME}", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    if EXE_NAME.lower() not in (probe.stdout or "").lower():
        return
    print(f"Закрываю запущенный {EXE_NAME}...")
    subprocess.run(
        ["taskkill", "/F", "/IM", EXE_NAME],
        capture_output=True,
        check=False,
    )


def _pip_install(requirement_file: Path) -> None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    subprocess.check_call(
        [str(python_bin()), "-m", "pip", "install", "-q", "-r", str(requirement_file)],
        cwd=ROOT,
        env=env,
    )


def ensure_build_deps() -> None:
    probe = subprocess.run(
        [str(python_bin()), "-c", "import PyQt5, requests, dotenv, PyInstaller"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode != 0:
        print("Ставлю зависимости сборки...")
        _pip_install(BUILD_REQUIREMENTS)
    align = subprocess.run(
        [str(python_bin()), "-c", "import faster_whisper, imageio_ffmpeg"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if align.returncode != 0 and ALIGN_REQUIREMENTS.exists():
        print("Ставлю зависимости распознавания для сборки...")
        _pip_install(ALIGN_REQUIREMENTS)
        align = subprocess.run(
            [str(python_bin()), "-c", "import faster_whisper, imageio_ffmpeg, ctranslate2, av, numpy"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if align.returncode != 0:
        raise SystemExit(
            "Не удалось импортировать пакеты распознавания. "
            "Проверьте pip install -r requirements-align.txt"
        )


def copy_ffmpeg(dist_dir: Path) -> None:
    probe = subprocess.run(
        [str(python_bin()), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    src = Path((probe.stdout or "").strip())
    if probe.returncode != 0 or not src.is_file():
        print("ffmpeg не найден — распознавание MP3 может не заработать")
        return
    shutil.copy2(src, dist_dir / "ffmpeg.exe")
    print(f"Скопирован ffmpeg: {dist_dir / 'ffmpeg.exe'}")


def pyinstaller_args(clean: bool) -> list[str]:
    args = [str(python_bin()), "-m", "PyInstaller", "--noconfirm", str(SPEC)]
    if clean:
        args.insert(-1, "--clean")
    return args


def build_exe(clean: bool) -> Path:
    stop_running_exe()
    print("Собираю exe...")
    try:
        subprocess.check_call(pyinstaller_args(clean), cwd=ROOT)
    except subprocess.CalledProcessError as exc:
        dist_locked = (DIST_DIR / "VitagoAdmin").exists()
        if dist_locked:
            raise SystemExit(
                "Сборка не удалась: папка dist\\VitagoAdmin занята "
                f"(закройте {EXE_NAME} и повторите)."
            ) from exc
        raise
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
    copy_ffmpeg(EXE_PATH.parent)
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
