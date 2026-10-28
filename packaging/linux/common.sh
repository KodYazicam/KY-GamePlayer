#!/bin/sh
# Shared helpers for packaging/linux/package-*.sh. Source after setting ROOT.
set -eu

APP="$ROOT/dist/KodYazar"
OUT="$ROOT/dist/release"
VERSION=$(
    cd "$ROOT"
    python3 - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PY
)
ARCH="x64"
TAG="KodYazar-Client-v$VERSION"
BASE_NAME="$TAG-linux-$ARCH"

require_app() {
    if [ ! -x "$APP/KodYazar" ]; then
        echo "error: $APP/KodYazar is missing; run packaging/linux/build.sh first" >&2
        exit 1
    fi
}

stage_tree() {
    dest="$1"
    rm -rf "$dest"
    install -d "$dest/opt/kodyazar"
    install -d "$dest/usr/bin"
    install -d "$dest/usr/share/applications"
    install -d "$dest/usr/share/icons/hicolor/256x256/apps"
    install -d "$dest/usr/share/licenses/kodyazar-client"
    cp -a "$APP/." "$dest/opt/kodyazar/"
    install -m 0755 "$ROOT/packaging/linux/kodyazar" "$dest/usr/bin/kodyazar"
    install -m 0644 "$ROOT/packaging/linux/kodyazar.desktop" "$dest/usr/share/applications/kodyazar.desktop"
    install -m 0644 "$ROOT/assets/icon.png" "$dest/usr/share/icons/hicolor/256x256/apps/kodyazar.png"
    install -m 0644 "$ROOT/LICENSE" "$dest/usr/share/licenses/kodyazar-client/LICENSE"
}

mkdir -p "$OUT"
