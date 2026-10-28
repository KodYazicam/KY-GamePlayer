#!/bin/sh
# Create build/icon.icns from assets/icon.png for the macOS .app bundle.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SRC="$ROOT/assets/icon.png"
ICONSET="$ROOT/build/icon.iconset"
OUT="$ROOT/build/icon.icns"

if [ ! -f "$SRC" ]; then
    echo "error: $SRC missing" >&2
    exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$SRC" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$SRC" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done

iconutil -c icns "$ICONSET" -o "$OUT"
echo "$OUT"
