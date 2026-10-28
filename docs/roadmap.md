# Development plan / yol haritası

Mirrored in the root README. Status is the contract for contributors.

Version in `pyproject.toml` / `ky_gameplayer.__init__.__version__`: **1.2.0**.

## Shipped — 1.2.0 (UI, security, CI)

- [x] `MainWindow` (3,212 lines) split into `ky_gameplayer/ui/` mixins; `window.py` is now a <250-line composition root
- [x] `ui/tasks.py::TaskRunner` — blocking Discord REST, credential harvest and process scans run off the GUI thread
- [x] Modern theme: design tokens, palette, app-wide style sheet, ghost/danger button variants, layout overflow fixes
- [x] Keyring (Secret Service / Keychain) for `token` / `cookie` / `analytics_token` on Linux and macOS, with migration and fallback
- [x] Per-game search text and distributor/OS caches (search ~32 ms → ~9 ms)
- [x] Offscreen Qt tests (`TaskRunner`, window smoke) and TR/EN parity tests
- [x] CI: Python 3.14, `ruff`, offscreen Qt job, Windows job
- [x] Documentation screenshots rendered from the real UI

## Shipped — 1.1.0 (packaging and catalog hygiene)

- [x] `python -m ky_gameplayer.catalog_sync` CLI (`--check`, backup, refuses suspicious payloads, atomic write)
- [x] Social preview image (`assets/banner.svg`, generated with svgforge)
- [x] Linux `.desktop` install script (`scripts/install-desktop.sh`) that does not rewrite the git copy
- [x] macOS `.app` via PyInstaller (`packaging/macos/`)
- [x] Optional one-file Windows EXE (`packaging/windows/KodYazar-onefile.spec`)
- [x] Settings block on the Help tab: log level, harvest on/off, lock timeout
- [x] Persist window size/splitter in `profiles.json` `settings`

## Next — 1.3 (RPC quality)

- [ ] `download_detectables` button in Help wrapping the sync CLI
- [ ] Asset browser UI over the `DiscordRest.application_assets` call (REST part landed in 1.1.0)
- [ ] Image upload helper (external URL only today)
- [ ] Better extra-slot UX when the host client cannot stack activities (detect official vs Vesktop)
- [x] Per-game default details/state templates (`game_templates` in `profiles.json`, identity tab)
- [x] Spotify-style Listening helper (type 2) with album art URL (identity tab)

## Later — quests and science

- [ ] Quest type coverage if Discord adds tasks beyond video/play/stream
- [x] Science dry-run (checkbox: build events, log them, skip the POST)
- [x] Fingerprint capture button (“copy from Discord’s own disk state”)
- [x] Rate-limit dashboard (HTTP/429/retry counters on the Help tab)
- [x] Hard cap + confirm dialog before science source = all 24k games (cap 2000, engine-level)

## Later — 2.0 (product)

- [x] Script hooks: load a Python file that returns `ActivityConfig` (`ky_gameplayer/hooks.py`, identity tab)
- [ ] Multi-account profiles with separate `science_state` files
- [ ] Wayland tray reliability pass
- [ ] Signed Windows Authenticode / macOS notarization (needs a certificate)
- [ ] Telemetry: **none**, keep it that way unless opt-in and documented

## Explicitly out of scope

- Decrypting Chrome App-Bound (v20) cookies
- Hosting a token on KodYazicam servers
- A public bot token mode (this is a **user** client)
- Shipping `science_state.json` examples
- Claiming Discord Staff / Partner / Bug Hunter badges

## How to pick work

1. Bugs that block Connect or lock → patch release
2. Docs mismatches → same
3. Catalog refresh tooling → 1.3
4. Anything that POSTs more Discord routes → discuss ToS risk in the PR

## Verification before a release

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests
ruff check .
KODYAZAR_UI_TESTS=1 QT_QPA_PLATFORM=offscreen python -m unittest tests.test_qt_ui
```
