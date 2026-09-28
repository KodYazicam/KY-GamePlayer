# -*- mode: python ; coding: utf-8 -*-
# Optional one-file Windows EXE (roadmap 1.1): single KodYazar.exe, no
# _internal folder to keep next to it. Slower to start than the onedir
# build; prefer packaging/windows/build.bat for normal use.
from pathlib import Path

root = Path.cwd()
datas = [
    (str(root / "games.json"), "."),
    (str(root / "assets"), "assets"),
]

a = Analysis(
    [str(root / "run.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=["cryptography", "PySide6.QtNetwork"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="KodYazar-onefile",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "assets" / "icon.ico") if (root / "assets" / "icon.ico").exists() else str(root / "assets" / "icon.png"),
)
