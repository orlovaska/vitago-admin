# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

ROOT = Path(SPECPATH)


def _collect(pkg: str, *, required: bool) -> tuple[list, list, list]:
    try:
        return collect_all(pkg)
    except Exception as exc:
        if required:
            raise SystemExit(
                f"Пакет {pkg} нужен в exe. Сначала: pip install -r requirements-align.txt\n{exc}"
            ) from exc
        return [], [], []


datas = [
    (str(ROOT / ".env.example"), "."),
    (str(ROOT / "scripts"), "scripts"),
]
binaries = []
hiddenimports = ["PyQt5.sip", "dotenv"]

for pkg, required in (
    ("faster_whisper", True),
    ("ctranslate2", True),
    ("av", True),
    ("numpy", True),
    ("tokenizers", True),
    ("huggingface_hub", True),
    ("imageio_ffmpeg", True),
    ("tqdm", False),
    ("onnxruntime", True),
    ("hf_xet", False),
):
    pkg_datas, pkg_binaries, pkg_hidden = _collect(pkg, required=required)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

binaries += collect_dynamic_libs("ctranslate2")
hiddenimports += ["faster_whisper", "ctranslate2", "av", "tokenizers"]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "pyi_rth_ffmpeg.py")],
    excludes=[
        "tkinter",
        "unittest",
        "pydoc",
        "pydoc_data",
        "setuptools",
        "pkg_resources",
        "pandas",
        "matplotlib",
        "PIL",
        "IPython",
        "pytest",
        "PySide2",
        "PySide6",
        "PyQt6",
        "torch",
        "torchaudio",
        "torchvision",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VitagoAdmin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VitagoAdmin",
)
