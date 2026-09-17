# Development plan / yol haritası

Mirrored in the root README. Status is the contract for contributors.

Version in `pyproject.toml` / `ky_gameplayer.__init__.__version__`: **1.0.0**.

## Now (1.0.x) — ship and document

- [x] PySide6 desktop shell, dark Fusion, tray, single instance
- [x] Membership lock on guild `1549516395010854912`
- [x] Discord IPC SET_ACTIVITY with full activity editor
- [x] 24k-game catalog + filters + favorites/playlist
- [x] Process detect (Linux/Windows/macOS)
- [x] HypeSquad, privacy, quests, custom status, clan
- [x] Science farm (hours / played)
- [x] Token harvest (LevelDB + DPAPI cookies v10/v11)
- [x] Windows `kurulum.bat` / `windows.bat` + PyInstaller spec
- [x] TR/EN i18n
- [x] This documentation set + GitHub repo
- [ ] GitHub Actions compile + unittest on 3.11–3.13 (workflow committed)
- [ ] Social preview image (`assets/banner.svg` or PNG) for the GitHub repo
- [ ] `icon.ico` for the Windows EXE

## Next (1.1) — packaging and catalog hygiene

- [ ] `download_detectables` button in Help or a `python -m ky_gameplayer.catalog_sync` CLI so `games.json` can refresh without a git pull
- [ ] Linux `.desktop` install script that does not rewrite the git copy
- [ ] macOS `.app` via PyInstaller or Briefcase
- [ ] Optional one-file Windows EXE (longer start, simpler copy)
- [ ] Settings page: log level, harvest on/off, lock timeout
- [ ] Persist window size/splitter in `profiles.json` `settings`

## Next (1.2) — RPC quality

- [ ] Asset browser from Discord application assets API when the id is a bot you own
- [ ] Image upload helper (external URL only today)
- [ ] Per-game default details/state templates
- [ ] Spotify-style Listening helper (type 2) with album art URL
- [ ] Better extra-slot UX when the host client cannot stack activities (detect official vs Vesktop)

## Later (1.3) — quests and science

- [ ] Quest type coverage if Discord adds tasks beyond video/play/stream
- [ ] Science dry-run (log payload, no POST)
- [ ] Fingerprint capture UI: “copy from last official detect”
- [ ] Rate-limit dashboard (429 counts)
- [ ] Hard cap / confirm dialog before science source = all 24k games

## Later (2.0) — product

- [ ] Plugin or script hooks (load a Python file that returns `ActivityConfig`)
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
