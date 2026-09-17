from __future__ import annotations

import base64
import json
import random
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

from .httputil import http_request, local_locale, local_timezone
from .paths import atomic_write
from .secrets import load_mapping, save_mapping

ME_URL = "https://discord.com/api/v9/users/@me?with_analytics_token=true"
SCIENCE_URL = "https://discord.com/api/v9/science"
GAMES_CDN_URL = "https://cdn.discordapp.com/detectables/games.json"

CLIENT_VERSION = "1.0.9253"
CLIENT_BUILD_NUMBER = 594031
NATIVE_BUILD_NUMBER = 88414
OS_VERSION = "10.0.26200"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)
AUTH_MAX_AGE = 12 * 3600


@dataclass
class ScienceState:
    token: str = ""
    cookie: str = ""
    fingerprint: str = ""
    analytics_token: str = ""
    fetched_at: int = 0

    @classmethod
    def load(cls, path: Path) -> "ScienceState":
        data = load_mapping(path)
        if not data:
            return cls()
        return cls(**{k: data.get(k, v) for k, v in cls().__dict__.items()})

    def save(self, path: Path) -> None:
        save_mapping(asdict(self), path)

    @property
    def is_stale(self) -> bool:
        return not self.analytics_token or (time.time() - self.fetched_at) > AUTH_MAX_AGE

    @property
    def has_cookie(self) -> bool:
        return bool(self.cookie.strip())

    @property
    def has_token(self) -> bool:
        return bool(self.token.strip())

    @property
    def ready(self) -> bool:
        return self.has_token and self.has_cookie


@dataclass(frozen=True)
class ScienceGame:
    id: str
    name: str
    exe: str


@dataclass(frozen=True)
class ScienceSession:
    heartbeat_session: str
    launch_signature: str
    super_props: str

    @classmethod
    def new(cls) -> "ScienceSession":
        hb = str(uuid.uuid4())
        sig = str(uuid.uuid4())
        return cls(hb, sig, build_super_props(sig, hb))


def _local_props() -> dict[str, Any]:
    from .httputil import local_locale, local_timezone

    return {
        "os": "Windows",
        "browser": "Discord Client",
        "release_channel": "stable",
        "client_version": CLIENT_VERSION,
        "os_version": OS_VERSION,
        "os_arch": "x64",
        "app_arch": "x64",
        "system_locale": local_locale(),
        "has_client_mods": False,
        "browser_user_agent": USER_AGENT,
        "browser_version": "42.7.1",
        "os_sdk_version": "26200",
        "client_build_number": CLIENT_BUILD_NUMBER,
        "native_build_number": NATIVE_BUILD_NUMBER,
        "client_event_source": None,
        "client_app_state": "focused",
        "client_heartbeat_session_id": None,
        "launch_signature": None,
    }


def build_super_props(launch_signature: str, heartbeat_session: str) -> str:
    props = _local_props()
    props["client_launch_id"] = str(uuid.uuid4())
    props["launch_signature"] = launch_signature
    props["client_heartbeat_session_id"] = heartbeat_session
    raw = json.dumps(props, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def read_analytics_token(auth_token: str) -> str:
    from .i18n import t

    status, data, _hdrs = http_request(
        "GET",
        ME_URL,
        headers={"authorization": auth_token, "user-agent": USER_AGENT},
        timeout=15,
        retries=2,
    )
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError(t("sci_token_rej", code=status))
    token = data.get("analytics_token")
    if not token:
        raise RuntimeError(t("sci_no_analytics"))
    return token


def ensure_analytics(state: ScienceState, path: Path | None = None) -> ScienceState:
    if not state.is_stale:
        return state
    state.analytics_token = read_analytics_token(state.token)
    state.fetched_at = int(time.time())
    if path is not None:
        state.save(path)
    return state


def win_exe_from_entry(game: dict[str, Any] | Any) -> str:
    executables = getattr(game, "executables", None)
    if executables is None and isinstance(game, dict):
        executables = game.get("executables") or []
    for entry in executables or []:
        if entry.get("os") == "win32" and entry.get("name"):
            return str(entry["name"])
    for entry in executables or []:
        if entry.get("name"):
            return str(entry["name"])
    return "game.exe"


def science_game_from(game: Any) -> ScienceGame:
    if isinstance(game, ScienceGame):
        return game
    return ScienceGame(
        id=str(getattr(game, "id")),
        name=str(getattr(game, "name")),
        exe=win_exe_from_entry(game),
    )


def download_detectables(dest: Path) -> str:
    status, payload, _hdrs = http_request(
        "GET",
        GAMES_CDN_URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
        retries=2,
    )
    if status != 200:
        raise RuntimeError(f"games.json [{status}]")
    raw = json.dumps(payload) if not isinstance(payload, str) else payload
    if isinstance(payload, list):
        raw = json.dumps(payload)
    atomic_write(dest, raw if isinstance(raw, str) else json.dumps(payload))
    return dest.read_text(encoding="utf-8")


class ScienceClient:
    def __init__(self, state: ScienceState, session: ScienceSession) -> None:
        self.state = state
        self.session = session
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def build_launch(self, game: ScienceGame) -> dict[str, Any]:
        now = int(time.time() * 1000)
        props: dict[str, Any] = {
            "client_track_timestamp": now,
            "client_heartbeat_session_id": self.session.heartbeat_session,
            "event_sequence_number": self._next_seq(),
            "game": game.name,
            "game_id": game.id,
            "verified": True,
            "elevated": False,
            "is_launcher": False,
            "game_platform": "desktop",
            "detection_method": "verified_game",
            "is_overlay_enabled": False,
            "is_overlay_game_enabled": True,
            "is_overlay_game_source": "OOP_DEFAULT_DATABASE",
            "fullscreen_type": "UNKNOWN",
            "hardware_display_count": 1,
            "overlay_method": "Disabled",
            "activity_status_enabled": True,
            "activity_status_shared_guilds": [],
            "current_user_status": "online",
            "game_detection_enabled": True,
            "executable_path": game.exe,
            "voice_channel_id": None,
            "voice_channel_type": None,
            "voice_channel_bitrate": None,
            "voice_channel_guild_id": None,
            "hidden_by_distributor": False,
            "game_metadata": None,
            "executable_fingerprint": self.state.fingerprint,
            "client_performance_cpu": None,
            "client_performance_memory": None,
            "cpu_core_count": None,
            "accessibility_features": 0,
            "rendered_locale": "tr-TR",
            "launch_signature": self.session.launch_signature,
            "client_rtc_state": None,
            "client_app_state": "focused",
            "client_send_timestamp": now,
        }
        if not self.state.fingerprint:
            del props["executable_fingerprint"]
        return {"type": "launch_game", "properties": props}

    def build_heartbeat(
        self,
        game: ScienceGame,
        duration_ms: int,
        session_id: str,
        initial: bool,
        final: bool,
        ts: int | None = None,
    ) -> dict[str, Any]:
        ts = int(time.time() * 1000) if ts is None else ts
        return {
            "type": "running_game_heartbeat",
            "properties": {
                "client_track_timestamp": ts,
                "client_heartbeat_session_id": self.session.heartbeat_session,
                "event_sequence_number": self._next_seq(),
                "game_id": game.id,
                "game_name": game.name,
                "game_metadata": None,
                "game_executable": game.exe,
                "game_detection_enabled": True,
                "initial_heartbeat": initial,
                "final_heartbeat": final,
                "game_session_id": session_id,
                "duration_tracked_ms": duration_ms,
                "rtc_connection_id": None,
                "media_session_id": None,
                "launch_signature": self.session.launch_signature,
                "client_app_state": "focused",
                "client_send_timestamp": ts,
            },
        }

    def build_session(self, game: ScienceGame, duration_ms: int) -> list[dict[str, Any]]:
        sid = str(uuid.uuid4())
        now = int(time.time() * 1000)
        start = now - duration_ms
        if start < 0:
            start = now
        return [
            self.build_heartbeat(game, 0, sid, initial=True, final=False, ts=start),
            self.build_launch(game),
            self.build_heartbeat(game, duration_ms, sid, initial=False, final=True, ts=now),
        ]

    def post(self, events: Sequence[dict[str, Any]]) -> int:
        payload = {"token": self.state.analytics_token, "events": list(events)}
        headers = {
            "accept": "*/*",
            "accept-language": local_locale(),
            "authorization": self.state.token,
            "content-type": "application/json",
            **({"cookie": self.state.cookie} if self.state.cookie else {}),
            "origin": "https://discord.com",
            "referer": "https://discord.com/channels/@me",
            "user-agent": USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": local_locale(),
            "x-discord-timezone": local_timezone(),
            "x-super-properties": self.session.super_props,
        }
        status, _payload, _hdrs = http_request(
            "POST",
            SCIENCE_URL,
            headers=headers,
            body=payload,
            timeout=15,
            retries=3,
        )
        return int(status)


def chunked(items: Sequence[ScienceGame], size: int) -> Iterator[Sequence[ScienceGame]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def farm(
    client: ScienceClient,
    games: Sequence[ScienceGame],
    duration_ms: int,
    *,
    batch_size: int = 100,
    delay: float = 0.3,
    jitter: float = 0.05,
    extra_delay: tuple[float, float] = (0.5, 1.5),
    cancel: Callable[[], bool] | None = None,
    on_batch: Callable[[int, int, int], None] | None = None,
) -> int:
    total = len(games)
    sent_ok = 0
    for request_no, chunk in enumerate(chunked(games, max(1, batch_size)), start=1):
        if cancel and cancel():
            break
        events: list[dict[str, Any]] = []
        for game in chunk:
            drift = 0
            if duration_ms > 0 and jitter > 0:
                span = int(duration_ms * jitter)
                drift = random.randint(-span, span)
            events.extend(client.build_session(game, max(0, duration_ms + drift)))
        status = 0
        for _attempt in range(4):
            status = client.post(events)
            if status != 429:
                break
            time.sleep(2.0 + random.uniform(0.2, 1.2))
        if status == 204:
            sent_ok += len(chunk)
        if on_batch:
            on_batch(request_no, sent_ok, status)
        if status in (401, 403):
            break
        lo, hi = extra_delay
        time.sleep(max(0.0, delay) + random.uniform(min(lo, hi), max(lo, hi)))
        if cancel and cancel():
            break
    return sent_ok
