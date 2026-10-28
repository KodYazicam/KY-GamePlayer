# `tests/` — what CI actually runs

Operator docs: [`../README.md`](../README.md).  
Package map: [`../ky_gameplayer/README.md`](../ky_gameplayer/README.md).

Most tests stay **Qt-free**: they import dataclasses, JSON, and helpers, and never
construct `QApplication`, open Discord IPC, or harvest cookies. That keeps the
matrix cheap and sandbox-safe. `test_qt_ui.py`, `test_theme.py`,
`test_ipc.py` and `test_quest_science.py` are the Qt-facing group and run only
with `KODYAZAR_UI_TESTS=1` in the offscreen UI job. Window smoke tests point
`HOME`/`XDG_*` at an empty temporary directory and disable the membership and
process-scan timers, so they never read a developer's Discord install or start a
real token check.

## Commands

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests -v
```

GitHub Actions (`.github/workflows/ci.yml`) runs the Qt-free suite on Python
3.11, 3.12, 3.13 and 3.14, the offscreen suite on Linux, a Windows smoke job,
then asserts `games.json` is a non-empty JSON list. A separate Linux coverage job
runs both suites with a **60 %** line-coverage gate and uploads `coverage.xml`.

```bash
KODYAZAR_UI_TESTS=1 QT_QPA_PLATFORM=offscreen \
  python -m coverage run -m unittest discover -s tests
python -m coverage report --fail-under=60
```

## Files

| File | Covers | Does not cover |
| --- | --- | --- |
| `test_activity.py` | `ActivityConfig.build`, buttons vs secrets, clip empty strings, JSON round-trip, party size, streaming URL only on type 1 | IPC `SET_ACTIVITY` |
| `test_catalog.py` | `GameCatalog.load` of the real `games.json`, Overwatch id, token/theme/OS filters, Steam store URL priority | CDN downloads |
| `test_catalog_sync.py` | validation, diff, shrink guard, atomic install, `.bak`/restore, local HTTP download, CLI | Live Discord CDN |
| `test_client_auth.py` | token/cookie/fingerprint discovery, process classification, temp SQLite fixtures, empty-home browser roots | Real Discord install |
| `test_discord_rest.py` | route helpers, guild pagination, fallback routes and privacy/clan/claim flows with mocked `request` | Live Discord REST |
| `test_httputil.py` | 429/5xx retry policy, POST opt-in, `Retry-After` seconds/date, transport errors, stats (local server) | External network |
| `test_science.py` | `win_exe_from_entry`, `chunked`, `ScienceSession.new`, `science_game_from` | POST `/science` |
| `test_rest.py` | Quest JSON parse, house flags, guild membership helpers, badge decode, i18n `t()` | Live Discord REST |
| `test_profiles.py` | `ProfileStore` put/get/delete, favorites, recents, weight clamp, merge import, `atomic_write` | DPAPI |
| `test_detect.py` | `ProcessIndex` exe match, launcher skip, `process_names` | `/proc` or Toolhelp snapshots |
| `test_ipc.py` | frame encode/decode, transport helpers, IPC edge cases | Real Discord socket |
| `test_quest_science.py` | quest worker and science worker with fake REST/harvest | Live Discord |
| `test_theme.py` | design tokens, palette and theme application | Native platform rendering |
| `test_qt_ui.py` | `TaskRunner`, model markers, compact Games panel, filters, sub-tabs, TR/EN, catalog swap | Real desktop display |
| `test_diagnostics.py` | diagnostics report and redaction | Real log files |
| `test_packaging.py` | version single-source, Linux launcher/desktop files, macOS bundle version, release job/checksum wiring | Native package builds |

## Adding a test

1. Keep it in `unittest` so there is no extra dependency.
2. Do not import `window`, `panel`, `preview`, `images`, or `ipc` unless you isolate the non-Qt helper.
3. Never write tokens, cookies, or `science_state.json` into the repo.
4. If you touch `games.json` shape, extend `test_catalog.py`.
5. If you touch activity payload fields, extend `test_activity.py`.

## Local data

Tests read `games.json` from the repo root. The file is ~12 MB / ~24k games. First catalog test is the slowest (~1–2 s). Everything else is milliseconds.
