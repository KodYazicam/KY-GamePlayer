#!/bin/sh
# Install (or refresh) the Linux .desktop launcher without touching the git
# checkout. Writes to ~/.local/share/applications/kodyazar.desktop and points
# it at the python + run.py of THIS clone.
#
# Usage:
#   ./scripts/install-desktop.sh          install for the current user
#   ./scripts/install-desktop.sh --uninstall
set -e

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
local_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
target="$local_dir/kodyazar.desktop"

if [ "$1" = "--uninstall" ]; then
    rm -f "$target"
    echo "removed $target"
    exit 0
fi

python=${PYTHON:-python3}
command -v "$python" >/dev/null 2>&1 || python=python
command -v "$python" >/dev/null 2>&1 || { echo "no python3 found" >&2; exit 1; }

"$python" - << EOF
from pathlib import Path
import os
import sys

sys.path.insert(0, r"$repo")
from ky_gameplayer.autostart import install_desktop

install_desktop(Path(r"$repo") / "run.py")
print("wrote ${XDG_DATA_HOME:-\$HOME/.local/share}/applications/kodyazar.desktop")
EOF

update-desktop-database "$local_dir" 2>/dev/null || true
echo "KodYazar Client is in your application launcher (Game;Utility)."
