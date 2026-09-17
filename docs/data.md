# Data files and on-disk layout

Nothing in the config/cache dirs is committed. `.gitignore` already blocks `science_state.json`, `profiles.json`, `.venv/`, `dist/`.

## Directories

Resolved in `ky_gameplayer.paths`.

| | Config (`config_dir`) | Cache (`cache_dir`) |
| --- | --- | --- |
| Windows | `%APPDATA%\kodyazar` | `%LOCALAPPDATA%\kodyazar` |
| Linux | `$XDG_CONFIG_HOME/kodyazar` or `~/.config/kodyazar` | `$XDG_CACHE_HOME/kodyazar` or `~/.cache/kodyazar` |
| macOS | `~/Library/Application Support/kodyazar` | `~/Library/Caches/kodyazar` |

| Path | Writer | Contents |
| --- | --- | --- |
| `config/profiles.json` | `ProfileStore` | Last game, named RPC profiles, favorites, recents, playlist, excluded, played ids, random weights, UI settings |
| `config/science_state.json` | `ScienceState` / `secrets.save_mapping` | Token, cookie, fingerprint, analytics_token, fetched_at |
| `cache/logs/kodyazar-YYYYMMDD.log` | `__main__._setup_logging` | INFO logs, unhandled exceptions |
| `cache/cdn/` | `ImageCache` | PNG/JPEG downloaded from Discord CDN (game icons, badges, quest art) |

`atomic_write` writes a temp file in the same directory, `fsync`s, `os.replace`s, then `chmod 0600`.

## `science_state.json`

Plain JSON on Linux/macOS. On Windows, bytes are `b"KY1\x00" + CryptProtectData(utf-8 json)` so another Windows user on the same disk cannot read it.

```json
{
  "token": "<discord user token>",
  "cookie": "__dcfduid=…; __sdcfduid=…; locale=tr-TR",
  "fingerprint": "<optional executable_fingerprint>",
  "analytics_token": "<from GET /users/@me?with_analytics_token=true>",
  "fetched_at": 1710000000
}
```

`analytics_token` is treated stale after 12 hours (`AUTH_MAX_AGE`). Import via the Science panel **Kimlik dosyası al**. Treat exports as passwords.

## `profiles.json`

```json
{
  "last_game_id": "356875221078245376",
  "profiles": {
    "ranked": {
      "game_id": "356875221078245376",
      "activity": { "type": 0, "details": "Competitive", "state": "In game" }
    }
  },
  "favorites": ["356875221078245376"],
  "recents": ["356875221078245376"],
  "excluded": [],
  "playlist": [],
  "played": ["id-marked-by-science-played-mode"],
  "weights": { "356875221078245376": 3 },
  "settings": {
    "auto_reconnect": true,
    "random_interval": 60,
    "science_enabled": false
  }
}
```

`ActivityConfig.to_json()` dumps every dataclass field. Unknown keys are ignored on load. Weights clamp to 1–20. Recents keep 20 ids. Played list trims to 50_000.

Export/import in the Games tab copies this object (not `science_state.json`).

## Repo-root `games.json`

Discord detectable catalog. Loaded by `GameCatalog.load`.

- Count in this tree: **24 314** games
- Size: **~12 703 012** bytes, one JSON array
- Source of truth upstream: `https://cdn.discordapp.com/detectables/games.json` (`science.download_detectables`)

Each object:

| Field | Type | Use |
| --- | --- | --- |
| `id` | snowflake string | Discord application id = RPC client_id |
| `name` | string | List title, science `game` property |
| `aliases` | string[] | Search blob |
| `icon_hash` | hex or null | `cdn.discordapp.com/app-icons/{id}/{hash}.png` |
| `cover_image_hash` | hex or null | Same CDN path, used as large image |
| `themes` | string[] | Filter. 22 values (Action, Fantasy, Horror, …) |
| `executables` | `{name, os, is_launcher}` | Process detection. `os`: `win32`, `linux`, `darwin` |
| `third_party_skus` | `{distributor, id}` | Store buttons. Distributors: steam, epic, gog, uplay, xbox, microsoft, battlenet, google_play |
| `hook` | bool | Discord overlay hook flag (display only) |
| `overlay` | bool | Filter + meta |
| `overlay_compatibility_hook` | bool | Meta |
| `overlay_methods` | int | Meta |
| `overlay_warn` | bool | Meta |
| `content_classification` | object | ESRB/PEGI blobs, unused in UI |

Search matches **all** whitespace-separated tokens against `name + id + aliases + themes + sku ids + exe names` (casefold).

Do not pretty-print this file in git; keep it compact.

## Runtime-only (not files)

- Single-instance lock name: `kodyazar-client-lock` (`QLocalServer`)
- Discord IPC: `\\.\pipe\discord-ipc-N` or `$XDG_RUNTIME_DIR/discord-ipc-N`
- Preferred running client (Vesktop/Discord pid) lives in `MainWindow` memory

## Permissions

| File | Mode / ACL |
| --- | --- |
| `science_state.json` | `0600` + DPAPI on Windows |
| `profiles.json` | `0600` via `atomic_write` |
| logs | created `0600` best-effort |
| CDN cache | ordinary user files |

Backup: copy `profiles.json` if you care about presets. **Do not** put `science_state.json` in cloud sync folders that other people can read.
