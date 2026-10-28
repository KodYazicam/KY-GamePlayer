# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for Linux.

Run from the repository root:

    pyinstaller --noconfirm --clean packaging/linux/KodYazar-linux.spec
"""

from pathlib import Path
import tomllib

root = Path.cwd()
version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

datas = [
    (str(root / "games.json"), "."),
    (str(root / "assets"), "assets"),
    (str(root / "LICENSE"), "."),
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
    [],
    exclude_binaries=True,
    name="KodYazar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KodYazar",
)

# Keep the version available to local packaging scripts without hard-coding it
# in a second place.
print(f"KodYazar Client {version} Linux onedir build")
