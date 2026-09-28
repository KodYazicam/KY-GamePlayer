# -*- mode: python ; coding: utf-8 -*-
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
    [],
    exclude_binaries=True,
    name="KodYazar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(root / "assets" / "icon.png"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KodYazar",
)
app = BUNDLE(
    coll,
    name="KodYazar.app",
    icon=str(root / "assets" / "icon.png"),
    bundle_identifier="com.kodyazar.client",
    info_plist={
        "CFBundleName": "KodYazar Client",
        "CFBundleDisplayName": "KodYazar",
        "CFBundleShortVersionString": "1.1.0",
        "NSHighResolutionCapable": True,
    },
)
