# Contributing to KY-GamePlayer

```
Author : Batuhan (KodYazicam)
Project: KY-GamePlayer (KodYazar Client)
Source : https://github.com/KodYazicam/KY-GamePlayer
```

Attribution stays with [KodYazicam](https://github.com/KodYazicam) under **KYAL-1.0**. Keep the credit in `LICENSE`, this file, and the root README.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m compileall -q ky_gameplayer run.py tests
python -m unittest discover -s tests -v
python run.py
```

Windows: `kurulum.bat` then `windows.bat`. Details in [`docs/install.md`](docs/install.md).

Read these before changing code:

- [`ky_gameplayer/README.md`](ky_gameplayer/README.md) — module map
- [`docs/architecture.md`](docs/architecture.md) — boot, lock, IPC, REST
- [`docs/features.md`](docs/features.md) — every UI surface
- [`tests/README.md`](tests/README.md) — what CI runs
- [`docs/data.md`](docs/data.md) — on-disk files

## Rules

- Python **3.11+**. Use `from __future__ import annotations`.
- Do not add runtime dependencies beyond `PySide6` and `cryptography` without a README + `pyproject.toml` change.
- UI strings go through `ky_gameplayer.i18n.t`. Add both `tr` and `en` in `i18n.py`.
- Do not log tokens, cookies, or authorization headers. Logs already live in the cache dir; keep them boring.
- Discord IPC stays in `ipc.py`. REST stays in `discord_rest.py`. Do not scatter `urllib` calls into widgets.
- Membership lock (`REQUIRED_GUILD_ID`) is product policy, not optional. If you change the guild, change `brand.py` and the docs together.
- `games.json` is Discord’s detectable catalog. Prefer `ScienceClient` / `download_detectables` over hand-editing 24k rows.
- Windows DPAPI wrapping of `science_state.json` must remain (`KY1\x00` prefix). Linux/macOS keep mode `0600`.
- Keep KYAL-1.0 attribution.

## Pull requests

1. Fork and branch from `main`.
2. Add or update tests for helpers you touch.
3. Update the folder README if you add a module.
4. Update `docs/features.md` if the UI gained a control.
5. Do not commit `.venv/`, `dist/`, `science_state.json`, or `profiles.json`.
