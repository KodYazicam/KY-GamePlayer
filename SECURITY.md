# Security Policy

KY-GamePlayer (KodYazar Client) is a **local desktop app**. It talks to Discord over:

- Discord RPC named pipes / Unix sockets (`discord-ipc-N`)
- Discord HTTP API v9 (`/users/@me`, `/science`, `/quests`, `/hypesquad/online`, …)
- Discord CDN for game icons and badge art

It is **not** a bot, **not** a hosted service, and it does **not** send your token to KodYazicam.

## What it stores

| File | Where | Sensitivity |
| --- | --- | --- |
| `science_state.json` | config dir | **High** — user token, cookie, analytics token, executable fingerprint |
| `profiles.json` | config dir | Medium — RPC presets, favorites, science UI settings (not the token) |
| `logs/kodyazar-YYYYMMDD.log` | cache dir | Medium — IPC status, quest/science progress. Must not contain raw tokens |
| `cdn/` | cache dir | Low — downloaded PNG icons |

Windows encrypts `science_state.json` with DPAPI (`KY1\x00` + `CryptProtectData`). Linux and macOS write the JSON with mode `0600`.

Paths: [`docs/data.md`](docs/data.md).

## Token harvest

On first unlock the app reads the **already logged-in Discord / Vesktop / Chromium** Local Storage and Cookies database on **this machine** so you do not paste a token every launch. That is local process memory + local files. It does not upload the token anywhere except Discord’s own API, using the same `Authorization` header the official client uses.

Limitations:

- Chrome **App-Bound** cookie encryption (`v20` / `v21` / `APPB`) is **not** decrypted. Paste the cookie if harvest fails.
- Locked LevelDB / Cookies while Discord is open may need a shared-read copy (`winutil.read_shared` / `copy_shared`).
- Pasting a token into the lock screen is optional fallback. Treat that field like a password.

## Membership lock

The app refuses the main UI unless `/users/@me/guilds` (or guild member) shows guild `1549516395010854912` (KodYazar Client). Invite: `https://discord.gg/rS42FCPfKZ`. This is a product gate, not a security boundary. Anyone who clones the repo can change `brand.py`.

## Do not

- Commit `science_state.json`, exported identity JSON, or screenshots of the token field.
- File a public issue with a live token or cookie. Redact logs.
- Point this client at a Discord user account you do not own.
- Expect this to bypass Discord ToS. User-token REST (`/science`, quest heartbeat, hypesquad) is unofficial. Discord can rate-limit, lock, or terminate accounts. You run it at your own risk.

## Windows EXE / antivirus

Release zips are **unsigned PyInstaller** onedirs. Heuristic engines commonly flag high-entropy overlays and process-list APIs (`CreateToolhelp32Snapshot` is used on purpose — game detect). That is not a signed “0 detections” claim.

v1.0.0 (2026-09-17): zip [0/66](https://www.virustotal.com/gui/file-analysis/Y2ZmZjE3NmQ3NGI2ODAyYTM4MDVjOTE5YjVkY2I1ZTk6MTc4OTY3NjgwNw==/detection), exe [3/66](https://www.virustotal.com/gui/file-analysis/NGE2NmQ5ZjNhMWZiOWIyY2E5MjQ2YWQyNGZjMWI2MTI6MTc4OTY3Njc1OQ==/detection). The zip score is the container; SmartScreen looks at the PE. Hashes: [`docs/HASHES-v1.0.0.md`](docs/HASHES-v1.0.0.md). Prefer `python run.py` if you do not want a packed binary.

## Reporting

Open a private advisory on [KodYazicam/KY-GamePlayer](https://github.com/KodYazicam/KY-GamePlayer/security/advisories/new).
