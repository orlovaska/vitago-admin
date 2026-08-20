import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_EXPERIMENTAL_WARNING", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")

if getattr(sys, "frozen", False):
    root = Path(sys.executable).resolve().parent
    ffmpeg = root / "ffmpeg.exe"
    if ffmpeg.is_file():
        # Не добавляем папку exe в PATH: ffmpeg.exe там ломает PyAV/Whisper.
        os.environ.setdefault("IMAGEIO_FFMPEG_EXE", str(ffmpeg))
    # В режиме воркера не трогаем DLL search path — там же лежат Qt*.dll.
    if os.environ.get("_VITAGO_ALIGN_WORKER") != "1":
        try:
            os.add_dll_directory(str(root))
        except (AttributeError, OSError):
            pass
