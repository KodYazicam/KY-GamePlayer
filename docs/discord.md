# Discord surfaces

Unofficial user-token and RPC usage. Discord can change payloads without notice. This documents **what this repo sends**, not a promise from Discord.

## Clients we look for

Process name / cmdline tokens (`client_auth.PROCESS_NAMES`):

`vesktop`, `vencorddesktop`, `vencord`, `equibop`, `webcord`, `armcord`, `legcord`, `discordcanary`, `discordptb`, `discorddevelopment`, `update.exe`, `discord`

Skipped if cmdline contains `--type=`, `tokengen`, `local_proxy`, `ky_gameplayer`, `kodyazar`, `KY-GamePlayer`.

User-data directories: Windows `%APPDATA%` / `%LOCALAPPDATA%`, Linux `~/.config` plus Flatpak/Snap, macOS `~/Library/Application Support`. Browsers (Chrome, Brave, Edge, Chromium, Vivaldi, Opera, Firefox) are fallbacks for cookie/token if the desktop client is missing.

## IPC (Rich Presence)

Handshake `client_id` = catalog game id (Discord application id) or a custom Application ID you typed.

`SET_ACTIVITY` activity object fields we emit (`activity.ActivityConfig.build`):

| Field | Limit / notes |
| --- | --- |
| `type` | 0 Playing, 1 Streaming, 2 Listening, 3 Watching, 4 Custom, 5 Competing |
| `status_display_type` | 0 Name, 1 State, 2 Details |
| `name` | 128; ignored on most verified games |
| `url` | 512; only when type is Streaming |
| `details` / `state` | 128 |
| `details_url` / `state_url` | 256 |
| `timestamps.start` / `end` | unix seconds |
| `assets.large_image` etc. | hash, asset key, or URL |
| `party.id` / `size` `[current,max]` / `privacy` | |
| `buttons[]` | label 32, url 512; **cannot** be sent with secrets |
| `secrets.join/spectate/match` | 128; only if no buttons |
| `flags` | bitfield INSTANCE, JOIN, SPECTATE, … |
| `emoji` | custom status style |
| `instance` | bool |

PID in `SET_ACTIVITY.args.pid` should be a live process. Detected game pid is preferred; otherwise this client.

## REST (user token)

Base: `https://discord.com/api/v9`

| Method | Path | Feature |
| --- | --- | --- |
| GET | `/users/@me` | Lock, account, house flags |
| GET | `/users/@me?with_analytics_token=true` | Science analytics_token |
| GET | `/users/@me/guilds` | Membership, clan dropdown |
| GET | `/users/@me/guilds/{id}/member` | Membership fallback |
| GET | `/guilds/{id}/members/@me` | Membership fallback |
| GET | `/users/@me/settings` | Custom status read |
| PATCH | `/users/@me/settings` | Custom status write; privacy fallback |
| PATCH | `/users/@me/profile` | `profile_visibility` |
| GET | `/users/@me/entitlements` | Cosmetic / entitlement count |
| GET | `/users/@me/connections` | (available, unused in UI) |
| GET | `/users/@me/channels` | DM id for quest stream_key |
| PUT | `/users/@me/clan` | Clan tag |
| PUT | `/users/@me/primary-guild` | Clan fallback |
| PATCH | `/users/@me` | Clan fallback |
| POST | `/hypesquad/online` | `{house_id: 1\|2\|3}` |
| DELETE | `/hypesquad/online` | Leave house |
| GET | `/quests/@me?include_preview=true` | Quest list |
| POST | `/quests/{id}/enroll` | Accept |
| POST | `/quests/{id}/video-progress` | `{timestamp}` |
| POST | `/quests/{id}/heartbeat` | `{stream_key, terminal}` |
| POST | `/quests/{id}/claim-reward` (and `/claim`, `/rewards/claim`) | Claim |
| POST | `/science` | `{token: analytics_token, events: [...]}` |

HypeSquad house ids: 1 Bravery, 2 Brilliance, 3 Balance. Public flags bits 6/7/8.

Privacy levels in UI: 1 private (friends only flags), 2 limited (mutual friends+guilds), 3 public.

## Science events

Each game session:

1. `running_game_heartbeat` `initial_heartbeat=true`, `duration_tracked_ms=0`
2. `launch_game` with `game`, `game_id`, `executable_path`, optional `executable_fingerprint`
3. `running_game_heartbeat` `final_heartbeat=true`, `duration_tracked_ms` = requested hours

`x-super-properties` is base64 JSON pretending to be Discord desktop `1.0.9253` / build `594031` on Windows 10. Locale/timezone come from the OS (`httputil.local_locale`, `local_timezone`).

Fingerprint: Discord’s `executable_fingerprint` from Local Storage when a **real** game was detected by the official client. Without it, hours may not count toward some profile stats. The UI logs a hint when detect fires and fingerprint is empty.

## CDN

- App icons/covers: `https://cdn.discordapp.com/app-icons/{app_id}/{hash}.png?size=`
- Badge icons: `https://cdn.discordapp.com/badge-icons/{hash}.png`
- Detectables dump: `https://cdn.discordapp.com/detectables/games.json`

## Cookie names we keep

`__dcfduid`, `__sdcfduid`, `cf_clearance`, `locale`, `_cfuvid`, `__cfruid` for hosts ending in `discord.com`. Encrypted Chromium values `v10`/`v11` decrypt with the DPAPI-unwrapped `os_crypt.encrypted_key`. `v20`/`v21`/`APPB` are skipped.

## ToS / risk

This client automates things Discord’s desktop app does with a **user** token (not a bot token). That includes analytics spoofing and quest progress without playing. Discord’s policies can treat that as abuse. This repo does not bypass that. See [`SECURITY.md`](../SECURITY.md).
