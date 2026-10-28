# Linux packaging

Builds the PyInstaller onedir tree once, then produces native packages from it.

## Prerequisites

- Python 3.11+ with `requirements.txt`
- PyInstaller 6.x
- `dpkg-deb` for `.deb`
- `rpmbuild` for `.rpm`
- `base-devel` / `makepkg` for the Arch package
- X11/Wayland, OpenGL, fontconfig and xcb runtime libraries for the build host

On Ubuntu 22.04:

```bash
sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 \
  libxcb-cursor0 rpm zstd
python3 -m pip install -r requirements.txt "pyinstaller>=6,<7"
```

On Arch:

```bash
sudo pacman -S --needed python python-pip libxcb libxkbcommon libxkbcommon-x11 \
  libglvnd dbus fontconfig freetype2 glib2 libx11 libxext libxrender \
  xcb-util-cursor base-devel
python3 -m pip install -r requirements.txt "pyinstaller>=6,<7"
```

## Build

```bash
./packaging/linux/build.sh
# -> dist/KodYazar/KodYazar
```

Then one or more package formats:

```bash
./packaging/linux/package-deb.sh    # Debian / Ubuntu
./packaging/linux/package-rpm.sh    # Fedora / RHEL
./packaging/linux/package-arch.sh   # Arch / Manjaro / EndeavourOS (non-root)
./packaging/linux/package-tar.sh    # portable fallback
```

All outputs land in `dist/release/`.

`package-arch.sh` must run as a normal user: `makepkg` refuses to build as
root. In CI it runs as a dedicated `builder` user inside an
`archlinux:base-devel` container.

## Installed layout

| Path | Content |
| --- | --- |
| `/opt/kodyazar/` | PyInstaller app tree, including `_internal/` |
| `/usr/bin/kodyazar` | wrapper: `exec /opt/kodyazar/KodYazar "$@"` |
| `/usr/share/applications/kodyazar.desktop` | menu entry |
| `/usr/share/icons/hicolor/256x256/apps/kodyazar.png` | icon |
| `/usr/share/licenses/kodyazar-client/LICENSE` | KYAL-1.0 |

The `.deb` targets `amd64` and glibc 2.35+ (Ubuntu 22.04 build). The `.rpm`
uses the same payload and is assembled by `rpmbuild` in a Fedora container; it
requires Fedora/RHEL libraries and is not a package for older RHEL 9 systems
whose glibc is older than the payload. The Arch package is built against current
Arch and is intended for rolling Arch-based systems.

## Verify

```bash
dpkg-deb -I dist/release/*.deb
dpkg-deb -c dist/release/*.deb | head
rpm -qip dist/release/*.rpm
rpm -qlp dist/release/*.rpm | head
tar -tzf dist/release/*.tar.gz | head
tar --zstd -tf dist/release/*.pkg.tar.zst | head
```

For a smoke test on a machine with Qt installed:

```bash
QT_QPA_PLATFORM=offscreen ./dist/KodYazar/KodYazar
```

The app opens a window; use the normal test suite for headless verification.
