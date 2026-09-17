# Features (complete)

Every control that exists in 1.0.0. UI copy is listed in Turkish first (default language), then English.

Related: [`architecture.md`](architecture.md), [`discord.md`](discord.md), [`data.md`](data.md).

## Shell (all tabs)

| Control | What it does |
| --- | --- |
| Title **KodYazar Client** | `brand.APP_TITLE` |
| Member label | After unlock: `{username} · {client} · KodYazar Client`. While checking: “Üyelik kontrol ediliyor…” |
| **Client** combo | Running Discord-family processes (`list_running_clients`). **Otomatik** picks IPC-owning process first. Science and quests harvest from this preference. |
| **TR / EN** | `i18n.set_lang`. Relabels tabs, groups, placeholders, logs replay. |
| **Açılışta başlat / Start with system** | Linux XDG autostart + `.desktop`, Windows Startup `.bat`+`.vbs`, macOS LaunchAgent. |
| System tray | Show / Quit. Closing the window hides when tray works. Second instance raises this window. |
| Single instance | `kodyazar-client-lock` |

### Lock screen (before membership)

Shown until guild `1549516395010854912` is confirmed.

| Control | What it does |
| --- | --- |
| Invite text | Guild name + `https://discord.gg/rS42FCPfKZ` |
| **Sunucuya katıl / Join server** | Opens the invite in the browser |
| **Tekrar kontrol et / Check again** | Re-harvest + membership (20 s timeout) |
| Token field | Optional paste if Local Storage is locked |
| Cookie field | Optional `__dcfduid=…` |
| **Token ile gir / Enter with token** | `check_membership` with pasted values; fills missing cookie from disk |

Failure reasons: Discord not open, token unreadable, HTTP error on `/users/@me`, guilds list missing the id, timeout.

---

## Tab: Rozet kontrol / Badge control

HypeSquad house for the harvested account.

| Control | What it does |
| --- | --- |
| Account line | `global_name · current house` from public flags |
| Cards **Bravery / Brilliance / Balance** | Select house 1 / 2 / 3. Art from Discord badge CDN. Captions: Cesur maceracı / Keskin azimli / Dengeli uyumlu |
| **Seçili evi uygula / Apply selected house** | `POST /hypesquad/online` `{house_id}` |
| **Rozeti çıkar / Remove badge** | `DELETE /hypesquad/online` |

Current house is inferred from flag bits 6/7/8 and pre-selects the card.

---

## Tab: Tüm rozetler / All badges

Read-only catalog plus live owned state.

**Hediye / Gifting** cards (Nitro gift milestones): Patron 1, Champion 2, Luminary 3, Icon 6, Hero 10, Legend 20 — with official badge icons.

**Hesabında / On your account**: `decode_flags(public_flags, premium_type)` — Nitro line, three houses, Staff, Partner, HypeSquad Events, Bug Hunter 1/2, Early Supporter, Early Verified Bot Dev, Moderator Programs, Active Developer. Each row: owned/missing + how-to text (many are “not obtainable via this app”).

**Nitro / diğer**: Nitro 1/2/3/6/12/24/36/48 month labels + catalog badges (Quest, Original user, Staff, Partner, Bug Hunter 2, Active Dev, Early Supporter, Bug Hunter 1, HypeSquad Events, Commands, AutoMod, Orbs). This is a visual list, not an unlocker.

---

## Tab: Oyun menüsü / Games

Splitter. Left = catalog. Right = RPC + science.

### Left: catalog

| Control | What it does |
| --- | --- |
| Search | Tokens against name, id, alias, theme, exe, Steam/Epic/… sku |
| Theme | 22 Discord themes or all |
| Store | steam, epic, gog, uplay, xbox, microsoft, battlenet, google_play |
| OS | linux / win32 / darwin (from executables) |
| Icon / Cover / Overlay | has / missing / all |
| Scope | Tüm liste, Favoriler, Son kullanılan, Playlist, Hariç tutulanlar |
| ★ Favori | Toggle id in `profiles.json` `favorites` |
| + Playlist | Toggle `playlist` |
| Hariç tut | Toggle `excluded` (hidden from “all” unless you open that scope) |
| Weight 1–20 | Random-mode probability |
| List | 52 px rows, rounded icon, name + id · first theme |
| Meta box | Id, aliases, themes, OS, distributors, overlay/hook flags, SKUs |

~24 314 games from `games.json`. Icons stream from CDN into `cache/cdn`.

### Right: connection bar

| Button | Action |
| --- | --- |
| Bağlan / Connect | Handshake IPC with current application id |
| RPC güncelle / Update RPC | `SET_ACTIVITY` with `ActivityConfig.build()` |
| Temizle / Clear | `SET_ACTIVITY` activity `null` |
| Kes / Disconnect | Close socket |
| JSON kopyala | Clipboard of the activity object |
| Dışa aktar / İçe aktar | `profiles.json` dump / merge |

Status dot green when READY. Socket path shown (`\\.\pipe\discord-ipc-0` or Unix path).

### Profiles

Editable combo + Save / Load / Delete. Stores `{game_id, activity}` under a name.

### Random mode

| Control | Default | Meaning |
| --- | --- | --- |
| Random mode checkbox | off | Timer picks a game from the source pool |
| Interval | 60 s (5–86400) | Period |
| Source | Filtrelenmiş liste | filter / all / favorites / playlist |
| No-repeat N | 8 | Skip last N ids |
| Şimdi değiştir / Ctrl+R | | Immediate pick |
| Countdown label | | `{name} · next {s}s` |

Weights multiply pick chance. Excluded ids never enter the pool. Optional science fire on switch (`science_on_random`).

### Extra activities (separate IPC)

Pin current game to a second (… eighth) `DiscordIpc` with a unique fake pid. Official Discord still shows one Playing; Vesktop/arRPC may stack.

| Button | |
| --- | --- |
| Mevcut oyunu pinle / Ctrl+P | New slot, max 8, no duplicate game id |
| Seçileni kapat | Stop selected slot |
| Ekleri kapat | Stop all |

List shows `name · connecting|live|dropped|error`.

### Running-game detect

| Control | |
| --- | --- |
| Çalışan oyunu algıla | 5 s process scan |
| Algılanınca RPC güncelle | Auto select + SET_ACTIVITY |
| Algılanan PID’yi kullan | Copy pid into the PID spinner |
| Tara / Ctrl+D | Scan now |
| Combo + Seçileni kullan | Manual apply |

Matches `games.json` executables (not launchers). Proton/Wine `.exe` tokens on Linux.

### Identity group

| Field | |
| --- | --- |
| Application ID | Catalog id or custom snowflake. Editing finished loads that game if present |
| Aktivite adı | Custom `name` (often ignored on verified games) |
| Tip | Playing 0 … Competing 5 |
| Status display | Name / State / Details |
| Stream URL | Only sent for Streaming |
| PID + combo | This process, detected games, up to 80 processes |
| PID yenile / Bu süreç | Refresh / `os.getpid()` |
| Auto assets | On game select, fill large/small from cover/icon hashes |

### Text group

Details, details URL, state, state URL (128/256). Emoji name, snowflake id, animated flag.

### Assets group

Large/small image, hover text, click URL. Combo of cover, icon, store URLs. Buttons: write to large, write to small, copy URL. Preview 72 px.

### Time group

Start timestamp (default now, **Şimdi** button). End timestamp. Duration seconds → writes end = start + duration.

### Party group

Party id, send size checkbox, current / max, privacy omit/private/public.

### Buttons group

Two label+URL pairs. **Mağaza butonu doldur / Ctrl+Shift+S** fills Steam (preferred) or Epic/GOG/Xbox/… from SKUs. Buttons suppress secrets.

### Secrets group

Join / spectate / match secrets (only if no buttons).

### Flags / instance

`instance` checkbox (default on). Bits: INSTANCE, JOIN, SPECTATE, JOIN_REQUEST, SYNC, PLAY, PARTY_PRIVACY_FRIENDS, PARTY_PRIVACY_VOICE_CHANNEL, EMBEDDED.

### Text cycle

Checkbox + interval (5–3600 s, default 20). One frame per line: `details|state|button label|https://url`. Rotates on the same game. Ctrl not bound; enabling with empty text warns.

### Scheduler

Keep RPC only between start→end (wraps midnight). Idle clear after N seconds (default 1800) of no UI activity. Auto-reconnect with exponential backoff (2 s … 30 s) when IPC drops.

### Science farm group

See also [`discord.md`](discord.md) science events.

| Control | Default | |
| --- | --- | --- |
| Otonom: RPC değişince science bas | off | Fire farm when RPC updates |
| Random geçişte bas | on | |
| Algılanan oyunda bas | off | |
| Sadece seçili oyunu bas | on | Ignore pool, use current game |
| Mod | Saat ekle | or Oynandı (1 dk) |
| Saat | 2.00 | 0.01–24 |
| Kaynak | Seçili oyun | filter / favorites / playlist / all / missing (not in `played`) |
| Hedef saat | 0 = off | If >0 and one game, use as hours then stop |
| Batch | 20 | Games per HTTP POST (1–200) |
| Gecikme | 0.80 s | Between batches |
| Jitter | 0.05 | ± on duration_ms |
| Token / cookie / fingerprint | password fields | Saved to `science_state.json` |
| Açık client’tan al | | `harvest()` |
| Kimlik kaydet | | Write fields to disk |
| Token yenile | | `GET @me?with_analytics_token` |
| Kimlik dosyası al | | Import JSON |
| Şimdi bas / Durdur | | Start/cancel QThread |

Status line: live client, token/cookie/fp ok, idle/running.

**Played** mode marks successful ids so **Eksik oyunlar** shrinks.

### IPC log

Append-only view of translated events (connect, READY user, SET_ACTIVITY, science packets, quest lines). **Logu temizle** drops the buffer. Language switch replays the buffer.

### Preview widget

Paints a Discord-like card: type prefix, large art, small badge, details/state, elapsed/remaining, up to two grey buttons.

### Keyboard

| Shortcut | Action |
| --- | --- |
| Ctrl+R | Random switch now |
| Ctrl+U | Update RPC |
| Ctrl+L | Clear RPC |
| Ctrl+P | Pin extra slot |
| Ctrl+D | Scan processes |
| Ctrl+F | Toggle favorite |
| Ctrl+Shift+S | Fill store button |

---

## Tab: Profil gizliliği / Profile privacy

Three cards:

1. **Özel / Private** — friends only (`friend_source_flags` all false, restricted guilds)
2. **Kısıtlı / Limited** — mutual friends + mutual guilds
3. **Herkese açık / Public** — badges visible, `profile_visibility` 3

**Gizliliği uygula** → `PATCH /users/@me/profile` then settings fallback.

---

## Tab: Görevler / Quests

Lists accepted (and preview) Discord Quests.

| Control | |
| --- | --- |
| Tara | `GET /quests/@me` |
| Kabul et + başlat | Enroll pending + run engine |
| Otomatik başlat | Same start path |
| Durdur | Cancel worker |

Cards: icon, name, task type, progress bar, badge (bitti / kayıtlı / bekliyor / devam).

Supported task types: `WATCH_VIDEO`, `WATCH_VIDEO_ON_MOBILE`, `PLAY_ON_DESKTOP`, `STREAM_ON_DESKTOP`, `PLAY_ACTIVITY`. Unknown types are listed but not completed.

Video: ~1 s timestamp ticks. Play/stream: ~20 s heartbeats with `stream_key` from a DM. Claim attempts `claim-reward` / `claim` / `rewards/claim`.

Enrollment blocked / access suspended flags from the list payload are logged.

---

## Tab: Hesap / Account

| Control | |
| --- | --- |
| Meta | username, Nitro premium_type, clan tag |
| Özel durum + Durumu yaz | `PATCH /users/@me/settings` custom_status |
| Clan combo + Clan uygula | Searchable guild list; tagged guilds first. Empty = off |
| Entitlement count | `GET /users/@me/entitlements` length (Orbs balance is **not** here; Discord wallet) |
| Hesabı yenile | me + settings + entitlements + guilds |

---

## Tab: Yardım / Help

HTML how-to (8 steps), invite button, guild id. Text comes from `i18n.help_body`.

---

## Non-UI features

- Daily log file in cache
- Unhandled exception hook (KeyboardInterrupt quits cleanly)
- High-DPI PassThrough
- Dark Fusion palette (`#1e1f22` / `#5865f2`)
- Segoe UI 10 on Windows
- `QT_LOGGING_RULES` hides qpa window/font spam
