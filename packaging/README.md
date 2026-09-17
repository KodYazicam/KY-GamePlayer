# `packaging/` — shipping KodYazar Client

The supported run mode is **source + venv**:

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

Windows first-run: `kurulum.bat` then `windows.bat` (see [`docs/install.md`](../docs/install.md)).

## Windows EXE (`packaging/windows/`)

| File | Role |
| --- | --- |
| `build.bat` | `cd` to repo root, install `requirements.txt` + PyInstaller, run the spec. |
| `KodYazar.spec` | Analysis of `run.py`, bundles `games.json` and `assets/`, windowed (`console=False`). |

Output: `dist/KodYazar/KodYazar.exe` (onedir COLLECT, not one-file). `ky_gameplayer.paths.app_root()` looks next to the exe, in `_MEIPASS`, and in `_internal` for `games.json`.

GitHub Actions [`.github/workflows/release.yml`](../.github/workflows/release.yml) builds this zip on every `v*` tag (`windows-latest`, Python 3.12) and uploads it to the GitHub Release.

Local rebuild:

```bat
packaging\windows\build.bat
```

Needs Python 3.11+ on PATH. First build downloads PySide6 wheels; expect several hundred MB in `dist/`.

### Spec details

- Entry: `run.py` (sets `QT_LOGGING_RULES` then calls `ky_gameplayer.__main__.main`).
- Datas: `games.json` → `.` and `assets/` → `assets`.
- Hidden imports: `cryptography`, `PySide6.QtNetwork` (single-instance `QLocalServer`).
- UPX off. Debug off. Icon: `assets/icon.ico` if present else `assets/icon.png`.

## Linux desktop

Not a `.deb`. Enabling **Açılışta başlat** writes:

- `~/.config/autostart/kodyazar.desktop`
- `~/.local/share/applications/kodyazar.desktop`
- regenerates repo-root `KY-GamePlayer.desktop` with absolute `Exec`/`Path`/`Icon`

Template: [`kodyazar.desktop.in`](../kodyazar.desktop.in). Runtime writer: `ky_gameplayer.autostart`.

## macOS

LaunchAgent `~/Library/LaunchAgents/dev.kodyazar.client.plist` when autostart is on. No `.app` bundle yet — run `python3 run.py` from Terminal or an Automator wrapper. Roadmap: [`docs/roadmap.md`](../docs/roadmap.md).

## What not to commit

`dist/`, `build/`, `*.egg-info/` are gitignored. Do not upload a built EXE that contains a harvested `science_state.json`.
