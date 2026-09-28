#!/bin/sh
# Build the macOS .app (roadmap 1.1). Requires: python3, pip deps, pyinstaller.
set -e
cd "$(dirname -- "$0")/../.."
python3 -m PyInstaller packaging/macos/KodYazar-macOS.spec --noconfirm --clean
echo
echo "built: dist/KodYazar.app"
