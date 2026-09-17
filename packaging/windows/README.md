# `packaging/windows/` — PyInstaller onedir

See the parent [`../README.md`](../README.md) for the full shipping story.

## `build.bat`

1. `cd` two levels up (repo root).
2. `python -m pip install -r requirements.txt pyinstaller`
3. `pyinstaller --noconfirm --clean packaging\windows\KodYazar.spec`
4. Prints `dist\KodYazar\KodYazar.exe`

Run it from Explorer or cmd. Do not run it from Git Bash with mixed path separators if PyInstaller then cannot find `games.json`.

## `KodYazar.spec`

Python, not INI. `Path.cwd()` must be the **repo root** because `build.bat` cds there before invoking PyInstaller.

Bundled:

- `games.json` (~12 MB) — required at runtime; the catalog is not downloaded on first paint.
- `assets/` — icons.

`ky_gameplayer.paths.resource()` resolves frozen paths. If you add a data file, add it to `datas` **and** load it via `resource()`.

## After the build

Copy the whole `dist\KodYazar\` folder. The exe alone is not enough (`_internal` holds PySide6 + `games.json`).

Shortcut target:

```
C:\path\to\KodYazar\KodYazar.exe
```

Start in that folder. Autostart in the running app writes a `.bat` + `.vbs` under the user’s Startup folder pointing at this exe when `sys.frozen` is true.
