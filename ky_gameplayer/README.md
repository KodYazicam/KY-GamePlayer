# `ky_gameplayer/` — runtime package

Operator docs: [`../README.md`](../README.md).  
Architecture: [`../docs/architecture.md`](../docs/architecture.md).  
Feature catalog: [`../docs/features.md`](../docs/features.md).  
Discord payloads: [`../docs/discord.md`](../docs/discord.md).

This folder is the **Python package**. Entry: `__main__.main` (also `python run.py` from the repo root). Console script: `kodyazar` (`pyproject.toml`).

Version: `__init__.__version__` = `1.0.0`.

## Boot

```
__main__.py
  logging → cache/logs/kodyazar-YYYYMMDD.log
  QApplication (Fusion, dark palette, icon)
  instance.claim → QLocalServer "kodyazar-client-lock"
  window.MainWindow(app_root)
    games.GameCatalog.load(resource("games.json"))
    profiles.ProfileStore(config/profiles.json)
    science_worker.ScienceEngine(config/science_state.json)
    quest_engine.QuestEngine
    ipc.DiscordIpc
    images.ImageCache(cache/cdn)
```

`run.py` only sets `QT_LOGGING_RULES` and calls `main()`.

## Modules (edit here)

| File | Owns | Do not put here |
| --- | --- | --- |
| `__main__.py` | Qt app, palette, signals, logging, exception hook | Widgets |
| `window.py` | MainWindow: lock, tabs, games splitter, RPC form, timers, shortcuts | REST URL strings |
| `panel.py` | House / badges / privacy / quests / account / help pages | IPC |
| `brand.py` | `APP_TITLE`, guild id `1549516395010854912`, invite | Logic |
| `i18n.py` | `STRINGS` tr/en, `t()` | New English-only UI copy |
| `paths.py` | `app_root`, `resource`, config/cache/log dirs, `atomic_write` | Qt |
| `instance.py` | Single-instance `QLocalServer` | Persistence |
| `autostart.py` | Linux `.desktop`, Windows Startup bat/vbs, macOS LaunchAgent | RPC |
| `games.py` | `Game`, `GameCatalog.load` / `filter` | UI delegates |
| `model.py` | `GameListModel`, `GameDelegate` (52 px rows) | Catalog JSON |
| `store.py` | SKU → Steam/Epic/GOG/Xbox/… URLs, primary store button | HTTP |
| `activity.py` | `ActivityConfig` dataclass + `build()` SET_ACTIVITY payload | Socket IO |
| `ipc.py` | Unix socket + Windows named pipe, handshake, SET_ACTIVITY, ping | REST |
| `preview.py` | `PresencePreview` paint of a Discord-like card | Network |
| `images.py` | `QNetworkAccessManager` CDN cache | Token harvest |
| `detect.py` | `ProcessIndex` maps exe basename → games | `/proc` walking |
| `processes.py` | Linux `/proc`, Windows Toolhelp, macOS `ps` | Catalog |
| `client_auth.py` | Find Discord/Vesktop, harvest token/cookie/fp from LevelDB + Cookies | UI |
| `winutil.py` | Shared-read files, DPAPI protect/unprotect | HTTP |
| `secrets.py` | Load/save `science_state.json` (DPAPI `KY1\x00` on Windows) | Qt |
| `membership.py` | `check_membership` against `REQUIRED_GUILD_ID` | Widgets |
| `discord_rest.py` | User-token REST: me, guilds, quests, hypesquad, privacy, clan | Science event JSON |
| `quest_engine.py` | QThread worker: enroll, video ticks, heartbeats, claim | Catalog |
| `science.py` | Super properties, launch/heartbeat events, `farm()` POST `/science` | Qt |
| `science_worker.py` | `ScienceEngine` + `_FarmWorker` QThread | Window layout |
| `badges.py` | Flag bits, gift milestones, CDN badge hashes | REST |
| `profiles.py` | `profiles.json` favorites/recents/playlist/weights/settings | Tokens |
| `httputil.py` | `urllib` JSON, 429 retry, locale, timezone | Discord routes |

## Data flow for one “RPC güncelle”

1. `MainWindow._collect_config()` (in `window.py`) reads widgets into `ActivityConfig`.
2. `ActivityConfig.build()` drops empty keys, clips lengths, prefers buttons over secrets.
3. If not connected, `_connect` → `DiscordIpc.connect(application_id)`.
4. On READY, `_update_rpc` → `SET_ACTIVITY` `{pid, activity}`.
5. Optional: science autonomous checkbox → `ScienceEngine.start_farm`.

## Data flow for lock

1. Timer 50 ms after show → `_enforce_membership` thread.
2. `harvest(preferred, quick=True)` reads LevelDB token.
3. `check_membership` GET `@me` then guilds then member.
4. `membership_ready` queued to UI thread; stack index 1 on success.

## Adding a UI string

Both languages in `i18n.py` `pairs`. Call `t("key")`. `_apply_language` must retitle the widget if it is created once.

## Adding a REST route

Put the path on `DiscordRest`. Call it from `QuestEngine` / `ScienceEngine` / `MainWindow` helpers. Do not `urllib` from `panel.py`.

## Frozen exe

`paths.resource("games.json")` and `resource("assets/icon.png")` search `_MEIPASS` / `_internal`. Spec: [`../packaging/windows/README.md`](../packaging/windows/README.md).
