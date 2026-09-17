# Install

Python **3.11+**. Dependencies: `PySide6>=6.6,<7` and `cryptography>=42`. Not on PyPI as a published package you `pip install kodyazar-client` from the index — clone this repo.

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

## 2. Linux

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

## 3. Windows

### Source (recommended)

1. Install [Python 3.11+](https://www.python.org/downloads/). Tick **Add python.exe to PATH** and the py launcher.
2. Double-click `kurulum.bat` once.
   - Finds `py -3.14` … `py -3.11`, then `python`, then `python3`.
   - Requires 3.11+.
   - Creates `.venv`, upgrades pip, installs `requirements.txt`.
   - Verifies `run.py`, `requirements.txt`, `games.json` exist.
3. Double-click `windows.bat` every later launch.
   - If `.venv` is missing, it calls `kurulum.bat`.
   - Prefers `pythonw.exe` (no console). Falls back to `python.exe`.

### EXE (GitHub Release)

Tagged releases (`v*`) run [`.github/workflows/release.yml`](../.github/workflows/release.yml) on `windows-latest` and attach:

- `KodYazar-Client-vX.Y.Z-windows-x64.zip`
- matching `.sha256`
- `HASHES.txt` (exe + zip SHA-256 / SHA-1 / MD5 + VirusTotal permalinks)

Unzip the **whole** folder and run `KodYazar\KodYazar.exe`. The exe alone is not enough (`_internal` holds PySide6 + `games.json`). SmartScreen will likely warn: this is an unsigned PyInstaller build, not a Store app.

v1.0.0: hashes in [`HASHES-v1.0.0.md`](HASHES-v1.0.0.md). What VirusTotal actually said (zip 0/66, exe 3/65, sandbox quiet): [README — Windows EXE and antivirus](../README.md#windows-exe-and-antivirus). Scan the **exe** (2.1 MB) if you upload it yourself; the zip is over VirusTotal’s 32 MB anonymous cap.

Local rebuild:

```bat
packaging\windows\build.bat
```

See [`packaging/windows/README.md`](../packaging/windows/README.md).

Discord must be open for named pipe `\\.\pipe\discord-ipc-0` … `-9` (Stable / Canary / PTB / Vesktop). Cookie v10/v11 decrypts with DPAPI + AES-GCM. App-Bound **v20** cookies are skipped — paste cookie on the lock screen if harvest fails.

## 4. macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

Discord IPC is probed under `$TMPDIR`, `/tmp`, `/var/tmp`, and `~/Library/Application Support/discord`. Token harvest looks at `~/Library/Application Support/{discord,vesktop,…}`. Autostart writes `~/Library/LaunchAgents/dev.kodyazar.client.plist`.

There is no signed `.app` yet.

## 5. Optional: install as a local package

```bash
python -m pip install -e .
kodyazar
```

`pyproject.toml` exposes console script `kodyazar = ky_gameplayer.__main__:main`.

## 6. First launch checklist

1. Start Discord / Vesktop / Vencord and log in.
2. Join **KodYazar Client**: <https://discord.gg/rS42FCPfKZ>
3. Start KodYazar Client.
4. Lock screen harvests token (quick). If it fails, paste token (and cookie if asked).
5. Main UI unlocks only when `/users/@me/guilds` contains guild `1549516395010854912`.

Ctrl+C / SIGTERM / SIGHUP quit the Qt loop. Closing the window hides to tray when a tray icon is available; **Çıkış / Quit** in the tray exits.

## 7. Uninstall

Delete the clone. Then remove user data if you want a clean slate:

| OS | Config | Cache |
| --- | --- | --- |
| Windows | `%APPDATA%\kodyazar` | `%LOCALAPPDATA%\kodyazar` |
| Linux | `~/.config/kodyazar` | `~/.cache/kodyazar` |
| macOS | `~/Library/Application Support/kodyazar` | `~/Library/Caches/kodyazar` |

Autostart leftovers:

- Linux: `~/.config/autostart/kodyazar.desktop`, `~/.local/share/applications/kodyazar.desktop`
- Windows: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KodYazar.bat` (+ `.vbs`)
- macOS: `~/Library/LaunchAgents/dev.kodyazar.client.plist`
