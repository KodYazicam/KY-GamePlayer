# Architecture

KodYazar Client is a single-process **PySide6** desktop app. One window, several worker threads, no local HTTP server.

```
run.py
  QT_LOGGING_RULES
  ky_gameplayer.__main__.main
    logging → cache/logs
    QApplication Fusion + dark palette
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
3. Oyun menüsü — splitter: catalog list | RPC editor
4. Profil gizliliği
5. Görevler
6. Hesap
7. Yardım

`panel.Pages` is an alias of `KodYazarPages`. Games tab widgets live in `window.py` (`_build_left`, `_build_right`).

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

429 retries with `Retry-After` (capped). Transient errors retry 3 times with jitter.

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

`QuestEngine` harvests auth, lists quests, optionally enrolls, then:

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
