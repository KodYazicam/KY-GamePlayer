# Architecture

KodYazar Client is a single-process **PySide6** desktop app. One window, several worker threads, no local HTTP server.

```
run.py
  QT_LOGGING_RULES
  ky_gameplayer.__main__.main
    logging → cache/logs
    QApplication Fusion + ui.theme (palette + style sheet)
    instance.claim  → QLocalServer kodyazar-client-lock
    MainWindow(app_root)
      GameCatalog.load(games.json)
      ProfileStore(config/profiles.json)
      ScienceEngine(config/science_state.json)
      QuestEngine
      DiscordIpc
      ImageCache(cache/cdn)
      membership harvest thread
      detect scan thread
      science / quest QThreads when started
```

## Process and instance

`instance.claim` connects to `kodyazar-client-lock`. If another copy answers, it writes `raise` and the new process shows “already running” and exits 0. The living process `wire()`s `newConnection` to `_show_from_tray`.

Signals: SIGINT, SIGTERM, SIGHUP call `QApplication.quit`. A 200 ms timer keeps the Qt loop awake so Ctrl+C is processed on Unix.

Frozen (PyInstaller): `paths.app_root()` walks `sys.executable` parent, `_MEIPASS`, `_internal` until `games.json` or `assets/icon.png` exists.

## UI composition

`MainWindow` is a `QStackedWidget`:

0. **Lock page** — join invite, retry harvest, optional token/cookie paste
1. **App page** — brand row (member label, client combo, TR/EN, autostart) + `QTabWidget`

Tabs (order in code):

1. Rozet kontrol — HypeSquad cards (`panel.KodYazarPages.house_page`)
2. Tüm rozetler — catalog + owned flags
3. Oyun menüsü — splitter: compact catalog | RPC editor with five sub-tabs (Presence / Advanced / Automation / Science / Log)
4. Profil gizliliği
5. Görevler
6. Hesap
7. Yardım

`panel.Pages` is an alias of `KodYazarPages`. The games tab is assembled by `ui/layout.py` (`_build_left`, `_build_right`).

### UI modules

`MainWindow` is a composition root (`window.py`, <250 lines) that inherits mixins from `ky_gameplayer/ui/`:

| Module | Responsibility |
| --- | --- |
| `common.py` | `ExtraSlot`, `_line`, `MAX_EXTRA_SLOTS` |
| `lock.py` | lock page, token paste, membership enforcement |
| `tray.py` | tray icon, close-to-tray, shutdown |
| `language.py` | TR/EN string application |
| `layout.py` | header, tab shell, games splitter, action bars |
| `forms.py` | RPC editor groups, `collect()` / `apply_config()` |
| `games.py` | list model wiring, filters, favourites, random pool |
| `catalog.py` | opt-in catalog download, diff confirmation, in-place reload, restore |
| `presence.py` | IPC connect/frames, extra slots, assets, detection |
| `profiles.py` | profile CRUD, settings, import/export |
| `science_ui.py` | science farm, hooks, credential widgets |
| `account.py` | account REST, quests, badges/privacy actions |
| `theme.py` | design tokens, palette, style sheet |
| `tasks.py` | `TaskRunner` (blocking work → GUI thread) |

### Theme tokens

`ui/theme.py` owns two frozen `Tokens` sets (`DARK`, `LIGHT`) and derives both the Qt palette and one application-wide style sheet from them. `apply_theme(mode)` resolves `system` / `dark` / `light`, applies the palette before the style sheet, and follows `QStyleHints.colorSchemeChanged` while `system` is selected. The setting lives in `profiles.json` `settings["theme_mode"]` and is restored before the window is shown.

Custom-painted widgets (game delegate, presence preview) call `tokens()` instead of hardcoding colours; they repaint on a switch. `BrightText` follows `TEXT` as well as `WindowText`/`ButtonText`, because Qt styles may use it for tab labels. White is reserved for text on the accent colour.

### Logging and diagnostics

`__main__` calls `logging_setup.setup_logging()` before constructing the window:

- target `cache_dir()/logs/kodyazar.log`;
- `RotatingFileHandler` at 2 MB with three backups, so the directory stays bounded at roughly 8 MB;
- `RedactingFormatter` masks token-shaped strings, `Authorization:` headers and `token=`/`cookie=`/`secret=` pairs before formatting;
- a session-start line records app version, Python and platform;
- the Help-tab log level calls `apply_level()`, which updates the root logger **and** every handler.

`diagnostics.build_report()` adds version, OS, Python/Qt, catalog size, IPC availability, a whitelist of safe settings, the recent in-memory events and the last lines of the log. The whole report is passed through `redact()` again before it reaches the clipboard. **Copy diagnostics** and **Open log folder** live on the Help tab.

### Threading model

`TaskRunner` runs a callable on a daemon thread and emits `done` / `failed`; the signals are connected with `Qt.QueuedConnection`, so callbacks always execute on the GUI thread. Callback exceptions are logged, never propagated into the event loop. `cancel_all()` drops pending callbacks on shutdown.

Used by `_refresh_account`, `_apply_status`, `_apply_clan`, `_pull_science_from_client`, catalog download/install/restore, client refresh and PID scans. The science client-name lookup (`list_running_clients`, ~75 ms process scan) is cached for 5 s.

`DiscordIpc.connect()` also opens the transport and performs the handshake on a worker thread; `find_discord_ipc()` only stats candidate sockets, so a stale-but-listening pipe cannot freeze the GUI. `disconnect()` closes the socket first and joins with a short timeout. Membership uses a daemon thread + `membership_ready`, science/quests use `QThread` workers, and IPC has its own reader thread; all of them are stopped deterministically by `MainWindow.shutdown()`.

## Membership lock

`_enforce_membership` starts a daemon thread:

1. `client_auth.harvest(preferred, quick=True)` — running Discord/Vesktop process, then known user-data dirs, then browsers
2. `membership.check_membership(token, cookie)`
   - `GET /users/@me`
   - `GET /users/@me/guilds?limit=200` (paginated)
   - fallback `GET /users/@me/guilds/{id}/member` and `/guilds/{id}/members/@me`
3. Result queued to `membership_ready`

Timeout 20 s. Success switches the stack to the app page, applies auth to `ScienceEngine`, fills the account header. Failure stays on the lock page. Pasted tokens skip harvest.

Guild id and invite are constants in `brand.py`.

## Discord IPC

`ipc.DiscordIpc` is a `QObject` with a daemon reader thread.

Transport:

- Windows: `CreateFileW` on `\\.\pipe\discord-ipc-0` … `-9`, `WinPipeTransport` (`ReadFile`/`WriteFile`/`PeekNamedPipe`)
- Unix: `AF_UNIX` connect to candidates under `$XDG_RUNTIME_DIR` (including Flatpak/Snap/Vesktop subdirs), `$TMPDIR`, `/tmp`

Protocol (little-endian):

| Opcode | Name |
| --- | --- |
| 0 | HANDSHAKE `{v:1, client_id}` |
| 1 | FRAME JSON commands/events |
| 2 | CLOSE |
| 3 | PING |
| 4 | PONG |

`SET_ACTIVITY` args: `{pid, activity}`. `activity` is `ActivityConfig.build()` or `null` to clear. READY must arrive within 8 s or the loop emits `ipc_ready_timeout`. Ping every 45 s.

Official Discord shows **one** Playing activity. Extra slots (`ExtraSlot`, max 8) open **additional** IPC handshakes with other application ids. Vesktop/arRPC may stack them; stable Discord will not.

## REST

`discord_rest.DiscordRest` wraps `httputil.http_request` (`urllib`). Base `https://discord.com/api/v9`. Headers mimic Discord desktop (`USER_AGENT` / `QUEST_UA`, `x-super-properties`, locale, timezone, cookie).

Used by:

| Caller | Routes |
| --- | --- |
| Membership | `/users/@me`, `/users/@me/guilds`, guild member |
| QuestEngine | `/quests/@me`, enroll, video-progress, heartbeat, claim, hypesquad, profile privacy |
| Account tab | settings, entitlements, custom status, clan / primary-guild |
| ScienceEngine | `/users/@me?with_analytics_token=true`, `POST /science` |

`http_request` retries idempotent methods on 429 and transient 5xx (500/502/503/504) with capped exponential backoff + jitter, honouring `Retry-After` in seconds or HTTP-date form. POST/PATCH retry 429 automatically but only retry 5xx/transport failures when the caller sets `retry_non_idempotent=True`; this avoids duplicating a write that the server already applied. `retry_statuses` narrows or widens the status set.

## Science farm

Not Rich Presence. It POSTs analytics events Discord’s official client sends when it **detects a game**:

- `launch_game`
- `running_game_heartbeat` (initial + final, with `duration_tracked_ms`)

`ScienceClient.build_session` emits those three events per game. `farm()` batches games (UI default 20), posts, sleeps `delay + extra_delay`, honors cancel. 204 = success. 401/403 abort.

Modes:

- **playtime / Saat ekle** — `hours * 3600 * 1000` ms duration
- **played / Oynandı** — 60_000 ms, then ids appended to `profiles.json` `played` (for “Eksik oyunlar”)

Worker: `QThread` + `_FarmWorker`. Harvests token again at start. `ensure_analytics` refreshes analytics_token if older than 12 h.

## Quests

`QuestEngine` harvests auth and lists/enrolls on a `QThread`; results arrive through queued `log` / `failed` / `finished` signals. It then:

- `WATCH_VIDEO*` → `POST /quests/{id}/video-progress` ~1 s ticks until target
- `PLAY_ON_DESKTOP` / `STREAM_ON_DESKTOP` / `PLAY_ACTIVITY` → heartbeat every ~20 s with `stream_key` from a DM channel (`call:{channelId}:1`) or `call:{questId}:1`

On complete: terminal heartbeat / final timestamp, then claim-reward fallbacks.

## Detection

Every 5 s (if enabled) a thread calls `ProcessIndex.scan`:

- Linux: `/proc/*/comm,cmdline,exe`
- Windows: Toolhelp32 + `QueryFullProcessImageNameW` + `NtQueryInformationProcess` (command line)
- macOS: `ps -ax`

Exe names from `games.json` (launchers skipped). Proton/Wine command lines contribute `*.exe` tokens. Lowest pid wins per game id.

## Images

`ImageCache` uses `QNetworkAccessManager`. Memory map + disk files under `cache/cdn` named from the URL. List delegate requests icons lazily (`icon_needed` → 80 ms pump).

## i18n

`i18n.STRINGS` is a dict built from `(tr, en)` pairs in `_load()`. `t(key, **kwargs)` formats with `str.format`. Switching language in the combo calls `MainWindow._apply_language` which retitles every control and `pages.retranslate()`.

## Shutdown

`closeEvent`: if tray is usable, hide instead of quit. Quit path stops timers, `science.stop()`, `quest_engine.stop()`, unpins extra IPC slots, clears activity, disconnects, `QApplication.quit()`.
