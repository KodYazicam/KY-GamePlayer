## v1.2.0 — UI, security and CI

The window, the secrets file and the pipeline got the 1.2 treatment. No feature was removed.

### UI

- `window.py` went from 3,212 lines to a <250-line composition root; the UI lives in `ky_gameplayer/ui/` (`lock`, `tray`, `language`, `layout`, `forms`, `games`, `presence`, `profiles`, `science_ui`, `account`).
- Blocking work moved off the GUI thread (`ui/tasks.py::TaskRunner`): account refresh (4 REST calls), custom status, clan update, credential harvest and the science process scan no longer freeze the window on a slow response or a 429.
- New theme: design tokens, palette, one style sheet applied to the whole application (dialogs included), ghost/danger button variants, slimmer scrollbars, fixed header/favourites/random/detect overflow at the default width.

### Security

- Linux and macOS now keep `token`, `cookie` and `analytics_token` in the OS keyring (Secret Service / Keychain) instead of plain JSON.
- Legacy `science_state.json` files are migrated automatically on first read.
- Fallback to the old `0600` file when no backend is available; opt out with `KODYAZAR_NO_KEYRING=1`. Windows keeps DPAPI.

### Performance

- Catalog search text and distributor/OS lists are built once per game: `filter("counter")` ~32 ms → ~9 ms.

### CI

- Unit matrix 3.11–3.14, `ruff`, an offscreen PySide6 job and a Windows job.
- New tests: keyring storage, TR/EN parity, `TaskRunner`, window smoke build.

### Upgrade notes

- `pip install -r requirements.txt` again on Linux/macOS to pull `keyring`.
- First launch after upgrading moves your existing token into the keyring; nothing else changes.
- Windows users: no new dependency, DPAPI behaviour is unchanged.

## Build

Windows **onedir** build from `packaging/windows/KodYazar.spec`.

## Download

1. Get `KodYazar-Client-v*-windows-x64.zip` from this release.
2. Unzip the whole folder. Do **not** copy only `KodYazar.exe`.
3. Run `KodYazar\KodYazar.exe`.
4. Start Discord / Vesktop first, join [KodYazar Client](https://discord.gg/rS42FCPfKZ), then connect.

`games.json` (~12 MB catalog) and `assets/` are inside `_internal`.

## Also in this tree

- Source: clone and `python run.py` (Linux / macOS / Windows)
- Windows from source: `kurulum.bat` then `windows.bat`

## Antivirus / VirusTotal

This zip is **unsigned PyInstaller**. SmartScreen will likely warn. That is the same class of warning you get from any random GitHub EXE, not a special KodYazar finding.

We scanned the v1.0.0 binaries (17 Sep 2026); this release uses the same PyInstaller layout. Fresh hashes for this build are in `HASHES.txt`:

- **Zip — 0/66.** VirusTotal looked at the container. [analysis](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection)
- **`KodYazar.exe` — 3/65.** Microsoft `Trojan:Win32/Wacatac.B!ml` (machine learning, generic packed-PE bucket), Arctic Wolf `Unsafe`, SecureAge `Malicious`. Kaspersky, ESET, Bitdefender, Malwarebytes, CrowdStrike: clean. [detection](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection)

The sandboxes then ran the exe: **no dropped files, no network**, only `KodYazar.exe` itself. [behavior](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior)

**0/66 on the zip is not “the exe is clean.”** Windows looks at the PE. If you do not want a packed binary, clone the repo and run `python run.py`.

Hashes: [`docs/HASHES-v1.0.0.md`](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/HASHES-v1.0.0.md) and `HASHES.txt` on this release. Longer write-up: [README](https://github.com/KodYazicam/KY-GamePlayer#windows-exe-and-antivirus).

## Notes

- Unsigned PyInstaller binary. Windows SmartScreen / Defender may warn until you “Run anyway”.
- Chrome App-Bound cookies (`v20`) are not decrypted; paste cookie on the lock screen if harvest fails.
- Official Discord shows one Playing activity. Extra IPC pins need Vesktop/arRPC.

Docs: [README](https://github.com/KodYazicam/KY-GamePlayer#readme) · [Türkçe](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/README.tr.md) · [Install](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/install.md)
