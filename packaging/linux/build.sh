#!/bin/sh
# Build the PyInstaller onedir tree used by every Linux package.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT"
python3 -m PyInstaller --noconfirm --clean packaging/linux/KodYazar-linux.spec
