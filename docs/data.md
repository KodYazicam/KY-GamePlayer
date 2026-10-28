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
| `config/games.json` | `catalog_sync` / `MainWindow` | Optional user-updated catalog. Takes precedence over the bundled copy when it loads; absent by default. |
| `config/games.json.bak` | `catalog_sync` | Previous user catalog (or the bundled catalog after the first update). Used by **Restore**. |
| `cache/logs/kodyazar.log` | `__main__._setup_logging` | Redacted IPC/quest/science status and unhandled exceptions. Rotates at 2 MB; `.1`–`.3` are kept. |
| `cache/cdn/` | `ImageCache` | PNG/JPEG downloaded from Discord CDN (game icons, badges, quest art) |

`atomic_write` writes a temp file in the same directory, `fsync`s, `os.replace`s, then `chmod 0600`.

## Logs and diagnostics

- `logging_setup.setup_logging()` installs a `RotatingFileHandler` (`maxBytes=2_000_000`, `backupCount=3`) on `logs/kodyazar.log`.
- A `RedactingFormatter` masks Discord token shapes, `Authorization:` headers and `token=` / `cookie=` / `secret=` pairs before writing. The in-memory event view used by diagnostics goes through the same `redact()` function.
- The Help-tab **Log level** setting updates the root logger **and** every handler.
- **Copy diagnostics** builds a report from app version, OS, Python/Qt, catalog size, IPC availability, a whitelist of safe settings, recent events and the log tail. User paths, tokens and cookies are not included.
- **Open log folder** opens `cache_dir()/logs`.

The log directory stays bounded at about 8 MB (four 2 MB files).

## `science_state.json`

On Windows, bytes are `b"KY1\x00" + CryptProtectData(utf-8 json)` so another Windows user on the same disk cannot read it. On Linux/macOS the JSON stores only non-sensitive values; `token`, `cookie` and `analytics_token` live in the OS keyring (see [Secret storage](#secret-storage)).

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

## `games.json` (bundled and user catalog)

Discord detectable catalog. `MainWindow` prefers `config_dir()/games.json` when it exists and falls back to the read-only bundled file (`app_root()/games.json`). Both are parsed by `GameCatalog.load`.

- Count in this tree: **24 314** games
- Size: **~12 703 012** bytes, one JSON array
- Source of truth upstream: `https://cdn.discordapp.com/detectables/games.json`

### Opt-in refresh

**Games → Kataloğu güncelle** (or `python -m ky_gameplayer.catalog_sync`) downloads the upstream file on explicit request, validates it, shows a diff preview and only then writes `config/games.json` atomically. The download is capped at 40 MB, IDs must be unique numeric snowflakes, and a catalog that loses more than half of its rows is refused. There is no startup fetch and no polling.

`--check` compares counts without writing. `--restore` copies `games.json.bak` back. The GUI reloads the catalog, filters and process index in place; a restart is not required.

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
| `science_state.json` | `0600`; Windows DPAPI (`KY1\0`); Linux/macOS secrets in the OS keyring |
| `profiles.json` | `0600` via `atomic_write` |
| `logs/kodyazar.log`, `.1`–`.3` | created `0600` best-effort; redacted before formatting |
| CDN cache | ordinary user files |

### Secret storage

`token`, `cookie`, `analytics_token` (and the same class of keys) are written to the
OS keyring on Linux and macOS — Secret Service or Keychain, service
`kodyazar-client`, account `science_state`. The JSON file keeps non-sensitive
values (`fingerprint`, `fetched_at`).

- Existing plain-text files are migrated on first read.
- If no backend answers (headless box, no DBus), the app falls back to the
  previous `0600` file and logs a warning.
- `KODYAZAR_NO_KEYRING=1` forces the file path.
- Windows keeps DPAPI and never touches the keyring.
- Explicit paths (`ScienceState.load(path)` / portable import) bypass the keyring.

Backup: copy `profiles.json` if you care about presets. **Do not** put `science_state.json` in cloud sync folders that other people can read.
