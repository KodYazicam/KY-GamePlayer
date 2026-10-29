## v1.3.2 — P0 reliability hotfix

This is a focused hotfix for 1.3.1. No new features; detection, fingerprint
capture and malformed settings are fixed.

### Fixes

- Process detection now delivers its result on the GUI thread through
  `TaskRunner`. The 5 s scan no longer stays stuck after the first attempt, and
  the detected list / auto-apply path works again
  ([#34](https://github.com/KodYazicam/KY-GamePlayer/issues/34),
  [#35](https://github.com/KodYazicam/KY-GamePlayer/pull/35)).
- Fingerprint capture re-enables `btn_science_fp_capture` and reports success,
  empty result or error instead of staying on “Fingerprint aranıyor...”.
- `profiles.json` settings are coerced and clamped on load and import. A
  malformed value falls back to its default instead of aborting startup;
  unknown keys are preserved.
- `schema_version` (currently `1`) is written to the profile store, and
  `merge_import` sanitizes settings before saving.

### Downloads

| Platform | Artifact |
| --- | --- |
| Windows x64 | `KodYazar-Client-v1.3.2-windows-x64.zip` |
| macOS Apple Silicon | `KodYazar-Client-v1.3.2-macos-arm64.zip` |
| macOS Intel | `KodYazar-Client-v1.3.2-macos-x64.zip` |
| Debian / Ubuntu x64 | `KodYazar-Client-v1.3.2-linux-x64.deb` |
| Fedora / RHEL x64 | `KodYazar-Client-v1.3.2-linux-x64.rpm` |
| Arch / Manjaro / EndeavourOS x64 | `KodYazar-Client-v1.3.2-arch-x64.pkg.tar.zst` |
| Other Linux x64 | `KodYazar-Client-v1.3.2-linux-x64.tar.gz` |

Every asset has a matching `.sha256` file and the release includes a combined
`HASHES.txt`.

### Upgrade notes

- No manual migration. Existing `profiles.json` files are loaded and sanitized
  in place.
- Use this build instead of 1.3.1; the detection and fingerprint regressions
  are fixed here.
- macOS `.app` bundles are **unsigned and not notarized**. First launch:
  right-click → Open, or remove the quarantine attribute after copying the app
  out of the zip.

### Tests

- 193 tests, including event-loop regressions for `_scan_running` and
  `_capture_fingerprint`, malformed settings/import tests and an offscreen
  window-startup test.
- `ruff` clean; coverage **64 %** (gate 60 %).

## v1.3.1 — native Linux and macOS packages

This is a packaging release: the application code is unchanged from 1.3.0, but
tagged builds now produce native artifacts for every supported desktop instead
of a Windows-only zip.

### Downloads

| Platform | Artifact |
| --- | --- |
| Windows x64 | `KodYazar-Client-v1.3.1-windows-x64.zip` |
| macOS Apple Silicon | `KodYazar-Client-v1.3.1-macos-arm64.zip` |
| macOS Intel | `KodYazar-Client-v1.3.1-macos-x64.zip` |
| Debian / Ubuntu x64 | `KodYazar-Client-v1.3.1-linux-x64.deb` |
| Fedora / RHEL x64 | `KodYazar-Client-v1.3.1-linux-x64.rpm` |
| Arch / Manjaro / EndeavourOS x64 | `KodYazar-Client-v1.3.1-arch-x64.pkg.tar.zst` |
| Other Linux x64 | `KodYazar-Client-v1.3.1-linux-x64.tar.gz` |

Every asset has a matching `.sha256` file and the release includes a combined
`HASHES.txt`. Linux packages install the app under `/opt/kodyazar`, add
`/usr/bin/kodyazar`, a desktop entry and a 256 px icon. The generic tarball is
portable: unpack it and run `KodYazar/KodYazar`.

### Notes

- PyInstaller cannot cross-compile. Windows, macOS arm64, macOS Intel and the
  Ubuntu 22.04 Linux build run on native runners; the RPM is assembled by
  `rpmbuild` in a Fedora container and the Arch package in an Arch container.
- macOS `.app` bundles are **unsigned and not notarized**. First launch:
  right-click → Open, or remove the quarantine attribute after copying the app
  out of the zip. PySide6 6.12 requires macOS 14 (Sonoma) or newer.
- Linux packages bundle Qt and the Python runtime. They still need the normal
  X11/Wayland, OpenGL and font libraries listed in the package metadata.
- Debian/Ubuntu packages are built on Ubuntu 22.04 (glibc 2.35) for a wider
  compatibility floor. Arch packages are built in an Arch container so they
  match the rolling release.

## v1.3.0 — responsive UI, resilience and diagnostics

1.3 is about the seconds you used to lose: connecting, searching, opening quests
and waiting for a blocked window. The Games tab is shorter, the editor is split
into sub-tabs, appearance is selectable and the log can no longer grow forever.

### UI and Games

- Non-blocking Discord IPC connect: socket candidates are only stat'ed, open +
  handshake run on a worker thread, and `disconnect()` no longer joins the reader
  on the GUI thread ([#13](https://github.com/KodYazicam/KY-GamePlayer/issues/13)).
- Quest harvest/REST, client lists and PID scans moved off the GUI thread;
  `last_auth` and live-client cache bugs fixed; deterministic shutdown
  ([#14](https://github.com/KodYazicam/KY-GamePlayer/issues/14)).
- Compact catalog: scope chips, filters folded away, selected-game card and
  technical details on demand. The right side now uses **Presence / Advanced /
  Automation / Science / Log** sub-tabs instead of one long form
  ([#27](https://github.com/KodYazicam/KY-GamePlayer/issues/27)).
- Ranked search (exact → prefix → word → substring → alias/SKU/exe), elided rows,
  `Ctrl+F` focus search, `Escape` clear, `Ctrl+Shift+F` favourite, `F1` cheat-sheet
  and an empty state ([#15](https://github.com/KodYazicam/KY-GamePlayer/issues/15)).

### Appearance

- Light, dark and **system** themes selected on the Help tab and persisted in
  `profiles.json`; the game list and presence preview now use the same tokens as
  the rest of the window, and switches apply without a restart
  ([#16](https://github.com/KodYazicam/KY-GamePlayer/issues/16)).
- Fixed tab labels that could inherit white `BrightText` on the light surface.

### Catalog

- **Games → Update catalog** downloads the official `games.json` only on request,
  validates it, shows added/removed/changed counts and writes
  `config_dir()/games.json`. The bundled catalog stays read-only and the previous
  file is kept as `games.json.bak` for **Restore**
  ([#26](https://github.com/KodYazicam/KY-GamePlayer/issues/26)).

### Reliability

- HTTP retries for idempotent requests on 429 and transient 500/502/503/504,
  capped exponential backoff + jitter and `Retry-After` in seconds or HTTP-date
  form. POST/PATCH retry 429 automatically; 5xx/transport retries are opt-in via
  `retry_non_idempotent=True` ([#18](https://github.com/KodYazicam/KY-GamePlayer/issues/18)).
- Rotating log at `logs/kodyazar.log` (2 MB × 3), redaction for token/cookie/
  authorization-shaped strings in both file and in-memory views, and a Help-tab
  **Copy diagnostics** report with version, OS, Qt, catalog size, safe settings
  and a redacted tail ([#17](https://github.com/KodYazicam/KY-GamePlayer/issues/17)).

### Tests and CI

- 180 tests: HTTP retry against a local `ThreadingHTTPServer`, IPC framing,
  quest/science worker paths, auth helpers, model/search ranking, theme tokens,
  diagnostics and offscreen UI smoke tests.
- New Linux coverage job with a **60 %** line gate (`coverage.xml` artifact);
  current CI total is 63 % (64 % locally with the offscreen suite).
- No test requires external network access, a Discord client or real credentials.

### Upgrade notes

- No data migration. Default appearance stays **dark**; switch on Help → Appearance.
- Old `kodyazar-YYYYMMDD.log` files are no longer written. New logs live in
  `kodyazar.log` with `.1`–`.3` rotations.
- `pip install -r requirements.txt` again only if your environment is missing
  `keyring` from 1.2.

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

- Windows: **onedir** build from `packaging/windows/KodYazar.spec`.
- macOS: `.app` from `packaging/macos/KodYazar-macOS.spec`.
- Linux: onedir tree from `packaging/linux/KodYazar-linux.spec`, then
  `packaging/linux/package-deb.sh`, `package-rpm.sh`, `package-arch.sh` or
  `package-tar.sh`.

## Download

Pick the artifact for your platform:

| Platform | Install |
| --- | --- |
| Windows x64 | Unzip the **whole** folder and run `KodYazar\KodYazar.exe`. Do not copy only the exe. |
| macOS arm64 / x64 | Unzip, drag `KodYazar.app` to Applications, then right-click → Open on first launch. |
| Debian / Ubuntu | `sudo apt install ./KodYazar-Client-v*-linux-x64.deb` |
| Fedora / RHEL | `sudo dnf install ./KodYazar-Client-v*-linux-x64.rpm` |
| Arch-based | `sudo pacman -U KodYazar-Client-v*-arch-x64.pkg.tar.zst` |
| Other Linux | Unpack the tarball and run `KodYazar/KodYazar`; keep the whole folder together. |

After launching, start Discord / Vesktop first, join
[KodYazar Client](https://discord.gg/rS42FCPfKZ), then connect.

`games.json` (~12 MB catalog) and `assets/` are inside `_internal` (Windows and
Linux) or `KodYazar.app/Contents/Resources` (macOS).

## Also in this tree

- Source: clone and `python run.py` (Linux / macOS / Windows)
- Windows from source: `kurulum.bat` then `windows.bat`
- Linux packages: [`docs/install.md`](install.md#linux-packages)
- macOS app: [`docs/install.md`](install.md#macos-package)

## Antivirus / VirusTotal

The Windows zip is **unsigned PyInstaller**. SmartScreen will likely warn. That is the same class of warning you get from any random GitHub EXE, not a special KodYazar finding. The macOS `.app` is also unsigned/notarized; Linux packages are unsigned archives.

We scanned the v1.0.0 binaries (17 Sep 2026); this release uses the same PyInstaller layout. Fresh hashes for this build are in `HASHES.txt`:

- **Zip — 0/66.** VirusTotal looked at the container. [analysis](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection)
- **`KodYazar.exe` — 3/65.** Microsoft `Trojan:Win32/Wacatac.B!ml` (machine learning, generic packed-PE bucket), Arctic Wolf `Unsafe`, SecureAge `Malicious`. Kaspersky, ESET, Bitdefender, Malwarebytes, CrowdStrike: clean. [detection](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/detection)

The sandboxes then ran the exe: **no dropped files, no network**, only `KodYazar.exe` itself. [behavior](https://www.virustotal.com/gui/file/aa7cd98bba263e8ac8948b66137352f88310f8eebac1ad512d00e12b21f62595/behavior)

**0/66 on the zip is not “the exe is clean.”** Windows looks at the PE. If you do not want a packed binary, clone the repo and run `python run.py`.

Hashes: [`docs/HASHES-v1.0.0.md`](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/HASHES-v1.0.0.md) and `HASHES.txt` on this release. Longer write-up: [README](https://github.com/KodYazicam/KY-GamePlayer#windows-exe-and-antivirus).

## Notes

- Unsigned PyInstaller binaries. Windows SmartScreen / Defender and macOS Gatekeeper may warn until you explicitly allow them.
- Chrome App-Bound cookies (`v20`) are not decrypted; paste cookie on the lock screen if harvest fails.
- Official Discord shows one Playing activity. Extra IPC pins need Vesktop/arRPC.

Docs: [README](https://github.com/KodYazicam/KY-GamePlayer#readme) · [Türkçe](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/README.tr.md) · [Install](https://github.com/KodYazicam/KY-GamePlayer/blob/main/docs/install.md)
