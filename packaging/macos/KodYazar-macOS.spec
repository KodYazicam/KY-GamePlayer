# -*- mode: python ; coding: utf-8 -*-
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
bundle_icon = root / "build" / "icon.icns"
bundle_options = {
    "name": "KodYazar.app",
    "bundle_identifier": "com.kodyazar.client",
    "info_plist": {
        "CFBundleName": "KodYazar Client",
        "CFBundleDisplayName": "KodYazar",
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "LSMinimumSystemVersion": "14.0",
        "NSHighResolutionCapable": True,
    },
}
if bundle_icon.exists():
    bundle_options["icon"] = str(bundle_icon)
app = BUNDLE(coll, **bundle_options)
