# Troubleshooting

Logs: `cache_dir/logs/kodyazar-YYYYMMDD.log` ([`data.md`](data.md)). Never paste tokens.

## Lock: “Discord açık değil veya token okunamadı”

1. Start Discord / Vesktop and stay logged in.
2. Retry. Quick harvest only reads LevelDB; full harvest also reads Cookies.
3. Paste the user token into the lock field (DevTools → Application → Local Storage → `token`, or a plugin you already use). Cookie optional.
4. Windows: close Discord, retry, then reopen — Cookies db is often locked. The app copies with `FILE_SHARE_READ`.
5. Chrome v20 App-Bound cookies **cannot** be decrypted here. Paste `__dcfduid` + `__sdcfduid` from DevTools.

## Lock: not in KodYazar Client

Join <https://discord.gg/rS42FCPfKZ> on the **same account** the token belongs to. `GET /users/@me/guilds` must contain `1549516395010854912`. If you have 200+ servers, pagination walks `after=`. Wait a few seconds after joining.

## “IPC soketi yok” / Connect does nothing

Discord must expose `discord-ipc-0`.

- Linux Flatpak: leave Discord running; sockets live under `$XDG_RUNTIME_DIR/app/com.discordapp.Discord`.
- Snap: `$XDG_RUNTIME_DIR/snap.discord`.
- Windows: named pipe `\\.\pipe\discord-ipc-N`. Canary/PTB/Vesktop still use that pattern.
- WSL: Windows Discord pipes are **not** visible. Run the client on Windows.

READY timeout (8 s): handshake used a bad application id, or Discord is stuck. Restart Discord, pick a catalog game, Connect again.

## Rich Presence does not show

- Verified games ignore custom `name`; the title is the game.
- Buttons + secrets together: buttons win, secrets dropped.
- Streaming needs a twitch/youtube URL.
- Official Discord: **one** Playing. Extra pins need Vesktop/arRPC.
- PID must exist. Use detect or “Bu süreç”.

## Science 401 / 403

Token rejected or missing cookie. Pull from client again. Analytics token refreshes from `@me?with_analytics_token=true`. Cloudflare `cf_clearance` helps; v20 cookie harvest will not produce it.

## Science 204 but hours do not move

Need a real `executable_fingerprint` from Discord’s own detect. Launch an actual catalog game with Discord open, then **Açık client’tan al**. Without fingerprint some counters ignore the packets. Rate limits (429) are retried; huge batches look more bot-like — keep batch ≤ 20 and delay ≥ 0.8 s.

## Quests stay at 0

Accept the quest in Discord Quest Home first (`enrolledAt`). Video tasks need ~1 s ticks for `target` seconds. Play/stream tasks need a DM channel for `stream_key` and ~20 s heartbeats. `quest_enrollment_blocked_until` / `quest_access_suspended_until` mean Discord paused you — wait.

## Icons blank

CDN `cdn.discordapp.com`. Corporate TLS MITM or offline mode: list still works, art stays placeholder. Cache is `cache/cdn`.

## High CPU

Disable detect (5 s full process walk). Disable random + cycle. Icon pump is 80 ms while the queue is non-empty then idle.

## Autostart does not fire

- Linux: check `~/.config/autostart/kodyazar.desktop` Exec path still exists after you moved the clone.
- Windows: Startup `KodYazar.vbs` runs `pythonw` hidden. Frozen exe uses the exe path.
- macOS: `launchctl load ~/Library/LaunchAgents/dev.kodyazar.client.plist` if the checkbox wrote the file but launchd did not pick it up.

## “KodYazar zaten açık”

Another process holds `kodyazar-client-lock`. Use the tray Quit, or kill the leftover python. Crashes can leave a stale Qt local-server name; `QLocalServer.removeServer` runs on next claim.

## PySide6 / Qt plugin errors

Install the wheel from `requirements.txt` inside the venv. Mixing system Qt and pip PySide6 breaks `platforms` plugins. On Linux, `libxcb` / `libglib` must exist (`apt install libxcb-cursor0` on Debian if the window never appears).

## EXE missing games.json

Copy the **entire** `dist\KodYazar` folder. `paths.resource` looks in `_internal`. Rebuild with `packaging\windows\build.bat` after pulling a new `games.json`.

## SmartScreen / Defender on the release zip

Unsigned PyInstaller. Windows has never seen this publisher. That warning is expected.

v1.0.0 VirusTotal: zip 0/66, exe 3/65 (Microsoft `Wacatac.B!ml` + two nameless heuristics). Sandbox: no network, no dropped files. Full story: [README — Windows EXE and antivirus](../README.md#windows-exe-and-antivirus). Hashes: [`HASHES-v1.0.0.md`](HASHES-v1.0.0.md).

If you do not want the packed file, run `python run.py` from a clone.
