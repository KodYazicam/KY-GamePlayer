# Install

Python **3.11+**. Dependencies: `PySide6>=6.6,<7` and `cryptography>=42`. Not on PyPI as a published package you `pip install kodyazar-client` from the index — clone this repo or use a GitHub Release package.

```
Author : Batuhan (KodYazicam)
Project: KY-GamePlayer (KodYazar Client)
Source : https://github.com/KodYazicam/KY-GamePlayer
```

## 1. Clone

```bash
git clone https://github.com/KodYazicam/KY-GamePlayer.git
cd KY-GamePlayer
```

You need `games.json` (~12 MB) next to `run.py`. It is part of the repo.

## 2. Release packages

Tagged releases (`v*`) are built by [`.github/workflows/release.yml`](../.github/workflows/release.yml) and published together with a `.sha256` file for every asset and one combined `HASHES.txt`.

| Platform | Artifact |
| --- | --- |
| Windows x64 | `KodYazar-Client-vX.Y.Z-windows-x64.zip` |
| macOS Apple Silicon | `KodYazar-Client-vX.Y.Z-macos-arm64.zip` |
| macOS Intel | `KodYazar-Client-vX.Y.Z-macos-x64.zip` |
| Debian / Ubuntu x64 | `KodYazar-Client-vX.Y.Z-linux-x64.deb` |
| Fedora / RHEL x64 | `KodYazar-Client-vX.Y.Z-linux-x64.rpm` |
| Arch / Manjaro / EndeavourOS x64 | `KodYazar-Client-vX.Y.Z-arch-x64.pkg.tar.zst` |
| Other Linux x64 | `KodYazar-Client-vX.Y.Z-linux-x64.tar.gz` |

Get them from [Releases](https://github.com/KodYazicam/KY-GamePlayer/releases). Verify before running:

```bash
sha256sum -c KodYazar-Client-vX.Y.Z-linux-x64.deb.sha256
# or
grep 'linux-x64.deb' HASHES.txt
```

### Windows x64

1. Download the zip and unzip the **whole** folder. Do not copy only `KodYazar.exe`; `_internal` holds PySide6 and `games.json`.
2. Run `KodYazar\KodYazar.exe`.
3. SmartScreen will likely warn: this is an unsigned PyInstaller build, not a Store app. See [Windows EXE and antivirus](../README.md#windows-exe-and-antivirus).

### Linux packages

The `.deb`, `.rpm` and Arch packages install:

| Path | Content |
| --- | --- |
| `/opt/kodyazar/` | PyInstaller app tree and `_internal/` |
| `/usr/bin/kodyazar` | launcher |
| `/usr/share/applications/kodyazar.desktop` | application-menu entry |
| `/usr/share/icons/hicolor/256x256/apps/kodyazar.png` | icon |
| `/usr/share/licenses/kodyazar-client/LICENSE` | KYAL-1.0 |

Debian / Ubuntu:

```bash
sudo apt install ./KodYazar-Client-vX.Y.Z-linux-x64.deb
kodyazar
```

Fedora / RHEL:

```bash
sudo dnf install ./KodYazar-Client-vX.Y.Z-linux-x64.rpm
kodyazar
```

Arch-based distributions:

```bash
sudo pacman -U KodYazar-Client-vX.Y.Z-arch-x64.pkg.tar.zst
kodyazar
```

Generic tarball for any other x86_64 Linux:

```bash
tar -xzf KodYazar-Client-vX.Y.Z-linux-x64.tar.gz
./KodYazar-Client-vX.Y.Z-linux-x64/KodYazar/KodYazar
```

Keep the whole `KodYazar` directory together. The tarball does not install system files.

The Linux packages bundle Qt and the Python runtime. They still need X11/Wayland, OpenGL, fontconfig and xcb libraries; the `.deb`/`.rpm`/PKGBUILD declare their dependencies. The Debian/RPM payload is built on Ubuntu 22.04 (glibc 2.35+). The Arch package is built against current Arch. If your distribution is older than those baselines, use the source install or the tarball on a newer base.

### macOS package

1. Download the zip matching your Mac:
   - Apple Silicon (M1/M2/M3/M4): `…-macos-arm64.zip`
   - Intel: `…-macos-x64.zip`
2. Unzip and move `KodYazar.app` to `/Applications`. The PySide6 6.12 wheels require **macOS 14 (Sonoma) or newer**.
3. First launch: right-click → **Open**. Alternatively remove the quarantine attribute:

```bash
xattr -dr com.apple.quarantine /Applications/KodYazar.app
```

The app is **unsigned and not notarized**. Gatekeeper will warn until signed with an Apple Developer ID. Token/IPC paths live under `~/Library/Application Support/kodyazar`, `~/Library/Caches/kodyazar` and the macOS temp directories.

## 3. Linux from source

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python run.py
```

Or without a venv:

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

### Desktop launcher

Inside the app, check **Açılışta başlat / Start with system**. That writes:

- `~/.config/autostart/kodyazar.desktop`
- `~/.local/share/applications/kodyazar.desktop`

`KY-GamePlayer.desktop` in the repo is a portable sample. After autostart is enabled, `install_desktop()` rewrites it with absolute `python` + `run.py` paths.

Wayland/X11: Fusion style, dark palette. Qt high-DPI rounding is `PassThrough`.

Flatpak/Snap Discord: IPC sockets are searched under `$XDG_RUNTIME_DIR/app/com.discordapp.Discord` and `dev.vencord.Vesktop`. Keep Discord running before Connect.

## 4. Windows from source

1. Install [Python 3.11+](https://www.python.org/downloads/). Tick **Add python.exe to PATH** and the py launcher.
2. Double-click `kurulum.bat` once.
   - Finds `py -3.14` … `py -3.11`, then `python`, then `python3`.
   - Requires 3.11+.
   - Creates `.venv`, upgrades pip, installs `requirements.txt`.
   - Verifies `run.py`, `requirements.txt`, `games.json` exist.
3. Double-click `windows.bat` every later launch.
   - If `.venv` is missing, it calls `kurulum.bat`.
   - Prefers `pythonw.exe` (no console). Falls back to `python.exe`.

Local EXE rebuild:

```bat
packaging\windows\build.bat
```

See [`packaging/windows/README.md`](../packaging/windows/README.md).

Discord must be open for named pipe `\\.\pipe\discord-ipc-0` … `-9` (Stable / Canary / PTB / Vesktop). Cookie v10/v11 decrypts with DPAPI + AES-GCM. App-Bound **v20** cookies are skipped — paste cookie on the lock screen if harvest fails.

v1.0.0 hashes: [`HASHES-v1.0.0.md`](HASHES-v1.0.0.md). VirusTotal history: [README — Windows EXE and antivirus](../README.md#windows-exe-and-antivirus).

## 5. macOS from source

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Discord IPC is probed under `$TMPDIR`, `/tmp`, `/var/tmp`, and `~/Library/Application Support/discord`. Token harvest looks at `~/Library/Application Support/{discord,vesktop,…}`. Autostart writes `~/Library/LaunchAgents/dev.kodyazar.client.plist`.

To build the `.app` locally:

```bash
python3 -m pip install pyinstaller
./packaging/macos/build.sh
open dist/KodYazar.app
```

See [`packaging/macos/README.md`](../packaging/macos/README.md).

## 6. Optional: install as a local package

```bash
python -m pip install -e .
kodyazar
```

`pyproject.toml` exposes console script `kodyazar = ky_gameplayer.__main__:main`.

## 7. First launch checklist

1. Start Discord / Vesktop / Vencord and log in.
2. Join **KodYazar Client**: <https://discord.gg/rS42FCPfKZ>
3. Start KodYazar Client.
4. Lock screen harvests token (quick). If it fails, paste token (and cookie if asked).
5. Main UI unlocks only when `/users/@me/guilds` contains guild `1549516395010854912`.

Ctrl+C / SIGTERM / SIGHUP quit the Qt loop. Closing the window hides to tray when a tray icon is available; **Çıkış / Quit** in the tray exits.

## 8. Uninstall

For a source checkout, delete the clone. For a package, use your package manager:

```bash
sudo apt remove kodyazar-client
sudo dnf remove kodyazar-client
sudo pacman -R kodyazar-client
```

Then remove user data if you want a clean slate:

| OS | Config | Cache |
| --- | --- | --- |
| Windows | `%APPDATA%\kodyazar` | `%LOCALAPPDATA%\kodyazar` |
| Linux | `~/.config/kodyazar` | `~/.cache/kodyazar` |
| macOS | `~/Library/Application Support/kodyazar` | `~/Library/Caches/kodyazar` |

Autostart leftovers:

- Linux: `~/.config/autostart/kodyazar.desktop`, `~/.local/share/applications/kodyazar.desktop`
- Windows: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KodYazar.bat` (+ `.vbs`)
- macOS: `~/Library/LaunchAgents/dev.kodyazar.client.plist`
