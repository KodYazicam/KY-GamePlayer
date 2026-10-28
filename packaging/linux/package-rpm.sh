#!/bin/sh
# Build a Fedora/RHEL .rpm from dist/KodYazar. The payload is a relocatable
# PyInstaller tree, so it is not tied to the build machine's Python packages.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
. "$ROOT/packaging/linux/common.sh"
require_app

TOP="$ROOT/build/rpm"
EXTRAS="$TOP/extras"
rm -rf "$TOP"
mkdir -p "$TOP/BUILD" "$TOP/BUILDROOT" "$TOP/RPMS" "$TOP/SOURCES" "$TOP/SPECS" "$TOP/SRPMS" "$EXTRAS"

install -m 0755 "$ROOT/packaging/linux/kodyazar" "$EXTRAS/kodyazar"
install -m 0644 "$ROOT/packaging/linux/kodyazar.desktop" "$EXTRAS/kodyazar.desktop"
install -m 0644 "$ROOT/assets/icon.png" "$EXTRAS/kodyazar.png"
install -m 0644 "$ROOT/LICENSE" "$EXTRAS/LICENSE"

cat > "$TOP/SPECS/kodyazar-client.spec" <<'EOF'
%global debug_package %{nil}
%global __os_install_post %{nil}

Name:           kodyazar-client
Version:        %{_kodyazar_version}
Release:        1%{?dist}
Summary:        Discord Rich Presence and quest panel
License:        KYAL-1.0
URL:            https://github.com/KodYazicam/KY-GamePlayer
BuildArch:      x86_64
Requires:       glibc >= 2.35
Requires:       mesa-libGL
Requires:       mesa-libEGL
Requires:       libxkbcommon-x11
Requires:       dbus-libs
Requires:       fontconfig
Requires:       freetype
Requires:       glib2
Requires:       libX11
Requires:       libXext
Requires:       libXrender
Requires:       libxcb
Requires:       xcb-util-cursor

%description
KodYazar Client is a local PySide6 desktop client for Discord Rich Presence,
quests, HypeSquad and science counters.

%prep

%build

%install
rm -rf %{buildroot}
install -d %{buildroot}/opt/kodyazar
cp -a "%{_kodyazar_app}/." %{buildroot}/opt/kodyazar/
install -Dm755 "%{_kodyazar_extras}/kodyazar" %{buildroot}/usr/bin/kodyazar
install -Dm644 "%{_kodyazar_extras}/kodyazar.desktop" %{buildroot}/usr/share/applications/kodyazar.desktop
install -Dm644 "%{_kodyazar_extras}/kodyazar.png" %{buildroot}/usr/share/icons/hicolor/256x256/apps/kodyazar.png
install -Dm644 "%{_kodyazar_extras}/LICENSE" %{buildroot}/usr/share/licenses/kodyazar-client/LICENSE

%files
%defattr(-,root,root,-)
/opt/kodyazar
/usr/bin/kodyazar
/usr/share/applications/kodyazar.desktop
/usr/share/icons/hicolor/256x256/apps/kodyazar.png
%license %{_datadir}/licenses/kodyazar-client/LICENSE

%changelog
* Thu Oct 29 2026 KodYazicam <KodYazicam@users.noreply.github.com> - %{version}-1
- Native Linux packages for Fedora/RHEL, Debian/Ubuntu and Arch-based systems.
EOF

rpmbuild -bb \
    --define "_topdir $TOP" \
    --define "_kodyazar_version $VERSION" \
    --define "_kodyazar_app $APP" \
    --define "_kodyazar_extras $EXTRAS" \
    "$TOP/SPECS/kodyazar-client.spec"

RPM=$(find "$TOP/RPMS" -type f -name 'kodyazar-client-*.rpm' | head -n 1)
if [ -z "$RPM" ]; then
    echo "error: rpmbuild produced no package" >&2
    exit 1
fi
OUT_RPM="$OUT/$BASE_NAME.rpm"
cp "$RPM" "$OUT_RPM"
echo "$OUT_RPM"
