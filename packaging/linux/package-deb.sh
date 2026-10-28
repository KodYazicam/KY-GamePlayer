#!/bin/sh
# Build a Debian/Ubuntu .deb from dist/KodYazar. Tested on Ubuntu 22.04.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$ROOT/packaging/linux/common.sh"
require_app

PKG="$ROOT/build/deb/kodyazar-client"
stage_tree "$PKG"
mkdir -p "$PKG/DEBIAN"

SIZE=$(du -sk "$PKG" | awk '{print $1}')
cat > "$PKG/DEBIAN/control" <<EOF
Package: kodyazar-client
Version: $VERSION
Section: games
Priority: optional
Architecture: amd64
Installed-Size: $SIZE
Maintainer: Batuhan (KodYazicam) <KodYazicam@users.noreply.github.com>
Homepage: https://github.com/KodYazicam/KY-GamePlayer
Depends: libc6 (>= 2.35), libgl1, libegl1, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libfreetype6, libglib2.0-0, libx11-6, libxext6, libxrender1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, libxcb-sync1, libxcb-xinerama0, libxcb-xinput0
Description: Discord Rich Presence and quest panel
 KodYazar Client is a local PySide6 desktop client for Discord Rich
 Presence, quests, HypeSquad and science counters.
EOF

cat > "$PKG/DEBIAN/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: KY-GamePlayer (KodYazar Client)
Source: https://github.com/KodYazicam/KY-GamePlayer

Files: *
Copyright: 2026 Batuhan (KodYazicam)
License: KYAL-1.0
 See /usr/share/licenses/kodyazar-client/LICENSE.
EOF

DEB="$OUT/$BASE_NAME.deb"
dpkg-deb --root-owner-group --build "$PKG" "$DEB"
echo "$DEB"
