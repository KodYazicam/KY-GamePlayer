# Development plan / yol haritası

Mirrored in the root README. Status is the contract for contributors.

Version in `pyproject.toml` / `ky_gameplayer.__init__.__version__`: **1.1.0**.

## Now (1.1.0) — packaging and catalog hygiene (shipped)

- [x] `python -m ky_gameplayer.catalog_sync` CLI (`--check`, backup, refuses suspicious payloads, atomic write) so `games.json` can refresh without a git pull
- [x] Social preview image (`assets/banner.svg`, generated with svgforge)
- [x] Linux `.desktop` install script (`scripts/install-desktop.sh`) that does not rewrite the git copy
- [x] macOS `.app` via PyInstaller (`packaging/macos/`)
- [x] Optional one-file Windows EXE (`packaging/windows/KodYazar-onefile.spec`)
- [x] Settings block on the Help tab: log level, harvest on/off, lock timeout
- [x] Persist window size/splitter in `profiles.json` `settings`

## Next (1.2) — RPC quality

- [ ] `download_detectables` button in Help wrapping the sync CLI
- [ ] Asset browser UI over the `DiscordRest.application_assets` call (REST part landed in 1.1.0)
- [ ] Image upload helper (external URL only today)
- [x] Per-game default details/state templates (`game_templates` in `profiles.json`, identity tab)
- [x] Spotify-style Listening helper (type 2) with album art URL (identity tab)
- [ ] Better extra-slot UX when the host client cannot stack activities (detect official vs Vesktop)

## Later (1.3) — quests and science (shipped in 1.1.0)

- [ ] Quest type coverage if Discord adds tasks beyond video/play/stream
- [x] Science dry-run (checkbox: build events, log them, skip the POST)
- [x] Fingerprint capture button (“copy from Discord’s own disk state”)
- [x] Rate-limit dashboard (HTTP/429/retry counters on the Help tab)
- [x] Hard cap + confirm dialog before science source = all 24k games (cap 2000, engine-level)

## Later (2.0) — product

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

1. Bugs that block Connect or lock → patch 1.0.x
2. Docs mismatches → same
3. Catalog refresh tooling → 1.1
4. Anything that POSTs more Discord routes → discuss ToS risk in the PR
