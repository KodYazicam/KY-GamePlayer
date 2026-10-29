# Development plan / yol haritası

Mirrored in the root README. Status is the contract for contributors.

Version in `pyproject.toml` / `ky_gameplayer.__init__.__version__`: **1.3.2**.

## Shipped — 1.3.2 (P0 reliability hotfix)

- [x] Process scans and fingerprint capture deliver results through `TaskRunner` on the GUI thread
- [x] Scan busy state resets on failure; the fingerprint button re-enables on success, empty result and error
- [x] `profiles.json` settings are coerced and clamped on load and import; malformed values fall back to defaults
- [x] `schema_version` added to the profile store and the import path is sanitized
- [x] Event-loop regression tests for scan/fingerprint plus malformed settings/import and window startup

## Shipped — 1.3.1 (cross-platform packages)

- [x] Native Windows, macOS arm64/Intel, Debian/Ubuntu, Fedora/RHEL, Arch and generic Linux release artifacts
- [x] One `publish` job with per-file SHA-256 and a combined `HASHES.txt`
- [x] Linux install tree under `/opt/kodyazar`, `/usr/bin/kodyazar`, desktop entry and icon
- [x] macOS `.app` version sourced from `pyproject.toml`; unsigned Gatekeeper note documented
- [x] Packaging docs and install docs updated for every artifact

## Shipped — 1.3.0 (responsive UI, resilience, diagnostics)

- [x] Non-blocking IPC connect; cheap socket availability check; disconnect no longer joins the reader on the GUI thread
- [x] Quest harvest/REST, client refresh and PID scans off the GUI thread; fixed science `last_auth`; deterministic shutdown
- [x] Ranked search (exact → prefix → word → substring), elided rows, `Ctrl+F` / `Escape` / `Ctrl+Shift+F` / `F1`
- [x] Light / dark / system appearance, tokenised list + preview painting, persisted `theme_mode`
- [x] Compact catalog with scope chips and five editor sub-tabs (Presence / Advanced / Automation / Science / Log)
- [x] Opt-in official `games.json` update with diff preview, validation and rollback (Games tab + CLI)
- [x] HTTP retries for idempotent 5xx/429 with capped backoff, `Retry-After` seconds/date and POST opt-in
- [x] Rotating redacted log (2 MB × 3) and Help-tab diagnostics report
- [x] Coverage job in CI with a 60 % gate and `coverage.xml` artifact
- [x] 180 tests, including local HTTP retry, IPC framing, quest/science workers and offscreen UI
- [x] Dark + light README screenshots rendered from the real UI with synthetic demo data

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

## Also shipped — quests and science

- [x] Science dry-run (checkbox: build events, log them, skip the POST)
- [x] Fingerprint capture button (“copy from Discord’s own disk state”)
- [x] Rate-limit dashboard (HTTP/429/retry counters on the Help tab)
- [x] Hard cap + confirm dialog before science source = all 24k games (cap 2000, engine-level)

## Next — 1.4 (RPC quality)

- [ ] Asset browser UI over the `DiscordRest.application_assets` call (REST part landed in 1.1.0)
- [ ] Image upload helper (external URL only today)
- [ ] Better extra-slot UX when the host client cannot stack activities (detect official vs Vesktop)
- [ ] Quest type coverage if Discord adds tasks beyond video/play/stream

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
3. Asset browser / extra-slot UX → 1.4
4. Anything that POSTs more Discord routes → discuss ToS risk in the PR

## Verification before a release

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests
ruff check .
KODYAZAR_UI_TESTS=1 QT_QPA_PLATFORM=offscreen python -m unittest tests.test_qt_ui
```

## Coverage and a pip-less local run

The Qt-free suite runs straight from a checkout; no `pip install -e .` is
required:

```bash
python -m unittest discover -s tests
```

The UI tests need PySide6 and an offscreen platform:

```bash
KODYAZAR_UI_TESTS=1 QT_QPA_PLATFORM=offscreen \
  python -m unittest tests.test_ipc tests.test_quest_science tests.test_theme tests.test_qt_ui
```

If the `coverage` module is already available, the same checkout can be measured
without installing the project:

```bash
KODYAZAR_UI_TESTS=1 QT_QPA_PLATFORM=offscreen \
  python -m coverage run -m unittest discover -s tests
python -m coverage report --fail-under=60
python -m coverage xml
```

CI has a dedicated Linux `coverage` job with the same commands and a **60 %**
line-coverage gate; `coverage.xml` is uploaded as an artifact. The current total
is 63 % on CI and 64 % locally with the offscreen suite. The Qt-free matrix
still runs on Python 3.11–3.14. HTTP retry tests use a local
`ThreadingHTTPServer` and never contact Discord.

Tests must not require network access, a Discord client, or a real token.
