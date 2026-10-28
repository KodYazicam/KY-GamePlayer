# `packaging/` — shipping KodYazar Client

The supported run mode is still **source + venv**:

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

Tagged releases also ship native packages built with PyInstaller. PyInstaller is
not a cross-compiler: each artifact is built on the OS/architecture it targets.
The release workflow is [`.github/workflows/release.yml`](../.github/workflows/release.yml).

| Artifact | Built on | Install |
| --- | --- | --- |
| `KodYazar-Client-vX-windows-x64.zip` | `windows-latest` | Unzip; run `KodYazar\KodYazar.exe` |
| `KodYazar-Client-vX-macos-arm64.zip` | `macos-15` (Apple Silicon) | Unzip; open `KodYazar.app` |
| `KodYazar-Client-vX-macos-x64.zip` | `macos-15-intel` | Unzip; open `KodYazar.app` |
| `KodYazar-Client-vX-linux-x64.deb` | Ubuntu 22.04 | `sudo apt install ./…deb` |
| `KodYazar-Client-vX-linux-x64.rpm` | Ubuntu 22.04 payload, Fedora `rpmbuild` | `sudo dnf install ./…rpm` |
| `KodYazar-Client-vX-arch-x64.pkg.tar.zst` | Arch container | `sudo pacman -U …pkg.tar.zst` |
| `KodYazar-Client-vX-linux-x64.tar.gz` | Ubuntu 22.04 | Unpack; run `KodYazar/KodYazar` |

`vX` means the release tag, for example `v1.3.1`. Packaging scripts read the
version from `pyproject.toml`. The `publish` job in the release workflow writes
a `.sha256` file for every asset and one combined `HASHES.txt`.

## Windows EXE (`packaging/windows/`)

| File | Role |
| --- | --- |
| `build.bat` | `cd` to repo root, install `requirements.txt` + PyInstaller, run the spec. |
| `KodYazar.spec` | Analysis of `run.py`, bundles `games.json`, `assets/` and `LICENSE`, windowed (`console=False`). |
| `KodYazar-onefile.spec` | Optional single-file EXE; slower start, no `_internal` folder. |

Output: `dist/KodYazar/KodYazar.exe` (onedir COLLECT, not one-file). `ky_gameplayer.paths.app_root()` looks next to the exe, in `_MEIPASS`, and in `_internal` for `games.json`.

Local rebuild:

```bat
packaging\windows\build.bat
```

Needs Python 3.11+ on PATH. First build downloads PySide6 wheels; expect several hundred MB in `dist/`.

### Spec details

- Entry: `run.py` (sets `QT_LOGGING_RULES` then calls `ky_gameplayer.__main__.main`).
- Datas: `games.json` → `.`, `assets/` → `assets`, `LICENSE` → `.`.
- Hidden imports: `cryptography`, `PySide6.QtNetwork` (single-instance `QLocalServer`).
- UPX off. Debug off. Icon: `assets/icon.ico` if present else `assets/icon.png`.

## macOS (`packaging/macos/`)

```bash
python3 -m pip install -r requirements.txt pyinstaller
./packaging/macos/build.sh
# -> dist/KodYazar.app
```

The spec reads the version from `pyproject.toml`, so the bundle version cannot
drift from the release. `make-icns.sh` converts `assets/icon.png` into
`build/icon.icns` before PyInstaller runs. Build on the machine/architecture you
ship for: `macos-15` produces arm64, `macos-15-intel` produces x64.

The app is **not signed or notarized**. First launch on another Mac:
right-click → Open, or run `xattr -dr com.apple.quarantine KodYazar.app`.
Token/IPC paths live under `~/Library/Application Support/kodyazar`,
`~/Library/Caches/kodyazar` and the usual macOS temp directories.

## Linux (`packaging/linux/`)

```bash
python3 -m pip install -r requirements.txt pyinstaller
./packaging/linux/build.sh                 # dist/KodYazar/
./packaging/linux/package-deb.sh           # dist/release/*.deb
./packaging/linux/package-rpm.sh           # dist/release/*.rpm
./packaging/linux/package-tar.sh           # dist/release/*.tar.gz
./packaging/linux/package-arch.sh          # Arch package, non-root user
```

`package-deb.sh` needs `dpkg-deb`; `package-rpm.sh` needs `rpmbuild`; the Arch
script needs `base-devel` (`makepkg`). The CI uses Ubuntu 22.04 for the
Debian/RPM payload so the glibc floor stays at 2.35, and an Arch container for
the `.pkg.tar.zst`.

Installed layout:

| Path | Content |
| --- | --- |
| `/opt/kodyazar/KodYazar` | PyInstaller launcher and `_internal/` |
| `/usr/bin/kodyazar` | wrapper that execs `/opt/kodyazar/KodYazar` |
| `/usr/share/applications/kodyazar.desktop` | application-menu entry |
| `/usr/share/icons/hicolor/256x256/apps/kodyazar.png` | icon |
| `/usr/share/licenses/kodyazar-client/LICENSE` | KYAL-1.0 attribution |

The generic tarball keeps the same app directory but does not install system
files; users run `KodYazar/KodYazar` from the unpacked folder.

Runtime packages still need X11/Wayland, OpenGL, fontconfig and xcb libraries.
Package dependency lists are intentionally explicit in
[`package-deb.sh`](linux/package-deb.sh), [`package-rpm.sh`](linux/package-rpm.sh)
and [`PKGBUILD.in`](linux/PKGBUILD.in).

## Tests before packaging

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests
ruff check .
```

Tests never need network access, a Discord client or real credentials.

## What not to commit

`dist/`, `build/`, `*.egg-info/` are gitignored. Do not upload a built package
that contains a harvested `science_state.json`.
