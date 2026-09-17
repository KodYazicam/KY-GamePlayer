# `tests/` — what CI actually runs

Operator docs: [`../README.md`](../README.md).  
Package map: [`../ky_gameplayer/README.md`](../ky_gameplayer/README.md).

These tests stay **Qt-free**. They import dataclasses, JSON, and helpers. They do not construct `QApplication`, open Discord IPC, or harvest cookies. That keeps CI cheap and sandbox-safe.

## Commands

```bash
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests -v
```

GitHub Actions (`.github/workflows/ci.yml`) runs the same on Python 3.11, 3.12, and 3.13, then asserts `games.json` is a non-empty JSON list.

## Files

| File | Covers | Does not cover |
| --- | --- | --- |
| `test_activity.py` | `ActivityConfig.build`, buttons vs secrets, clip empty strings, JSON round-trip, party size, streaming URL only on type 1 | IPC `SET_ACTIVITY` |
| `test_catalog.py` | `GameCatalog.load` of the real `games.json`, Overwatch id, token/theme/OS filters, Steam store URL priority | CDN downloads |
| `test_science.py` | `win_exe_from_entry`, `chunked`, `ScienceSession.new`, `science_game_from` | POST `/science` |
| `test_rest.py` | Quest JSON parse, house flags, guild membership helpers, badge decode, i18n `t()` | Live Discord REST |
| `test_profiles.py` | `ProfileStore` put/get/delete, favorites, recents, weight clamp, merge import, `atomic_write` | DPAPI |
| `test_detect.py` | `ProcessIndex` exe match, launcher skip, `process_names` | `/proc` or Toolhelp snapshots |

## Adding a test

1. Keep it in `unittest` so there is no extra dependency.
2. Do not import `window`, `panel`, `preview`, `images`, or `ipc` unless you isolate the non-Qt helper.
3. Never write tokens, cookies, or `science_state.json` into the repo.
4. If you touch `games.json` shape, extend `test_catalog.py`.
5. If you touch activity payload fields, extend `test_activity.py`.

## Local data

Tests read `games.json` from the repo root. The file is ~12 MB / ~24k games. First catalog test is the slowest (~1–2 s). Everything else is milliseconds.
