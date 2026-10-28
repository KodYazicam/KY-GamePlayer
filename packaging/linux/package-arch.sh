#!/bin/sh
# Build an Arch Linux package from dist/KodYazar. Run as a normal user:
# makepkg refuses to build packages as root.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$ROOT/packaging/linux/common.sh"
require_app

BUILD="$ROOT/build/arch"
rm -rf "$BUILD"
mkdir -p "$BUILD"
sed "s/@VERSION@/$VERSION/g" "$ROOT/packaging/linux/PKGBUILD.in" > "$BUILD/PKGBUILD"
chmod 0644 "$BUILD/PKGBUILD"

(cd "$BUILD" && makepkg --nodeps --noconfirm)

PKG=$(find "$BUILD" -maxdepth 1 -type f -name 'kodyazar-client-*.pkg.tar.zst' | head -n 1)
if [ -z "$PKG" ]; then
    echo "error: makepkg produced no package" >&2
    exit 1
fi
OUT_PKG="$OUT/$TAG-arch-$ARCH.pkg.tar.zst"
cp "$PKG" "$OUT_PKG"
echo "$OUT_PKG"
