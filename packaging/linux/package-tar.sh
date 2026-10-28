#!/bin/sh
# Build a portable Linux .tar.gz fallback for distributions without a native
# package in this repository.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$ROOT/packaging/linux/common.sh"
require_app

STAGE="$ROOT/build/tar/$TAG-linux-$ARCH"
rm -rf "$ROOT/build/tar"
mkdir -p "$STAGE"
cp -a "$APP" "$STAGE/KodYazar"
cp "$ROOT/LICENSE" "$STAGE/LICENSE"
cp "$ROOT/packaging/linux/kodyazar.desktop" "$STAGE/kodyazar.desktop"
cp "$ROOT/assets/icon.png" "$STAGE/kodyazar.png"
cat > "$STAGE/README.txt" <<'EOF'
KodYazar Client - portable Linux build
======================================

Run:
    ./KodYazar/KodYazar

Keep the whole KodYazar directory together; the _internal directory contains
Qt, the Python runtime and games.json. Do not copy only the KodYazar binary.

Desktop integration is not automatic in this portable archive. The included
kodyazar.desktop and kodyazar.png are templates if you want to add a launcher
to your application menu.

License: KYAL-1.0 (see LICENSE). Attribution is mandatory.
EOF

TAR="$OUT/$BASE_NAME.tar.gz"
tar -C "$ROOT/build/tar" -czf "$TAR" "$TAG-linux-$ARCH"
echo "$TAR"
