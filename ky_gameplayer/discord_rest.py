from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .httputil import http_request, local_locale, local_timezone
from .science import USER_AGENT, ScienceSession

API = "https://discord.com/api/v9"
QUEST_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Discord/1.0.9253 Chrome/148.0.7778.280 "
    "Electron/42.7.1 Safari/537.36"
)

HOUSE_BRAVERY = 1
HOUSE_BRILLIANCE = 2
HOUSE_BALANCE = 3
HOUSE_FLAG = {
    HOUSE_BRAVERY: 1 << 6,
    HOUSE_BRILLIANCE: 1 << 7,
    HOUSE_BALANCE: 1 << 8,
}
HOUSES = (
    (1, "Bravery", "#9C84EF", "https://cdn.discordapp.com/badge-icons/8a88d63823d8a71cd5e390baa45efa02.png"),
    (2, "Brilliance", "#F47B67", "https://cdn.discordapp.com/badge-icons/011940fd013da3f7fb926e4a1cd2e618.png"),
    (3, "Balance", "#45DDC0", "https://cdn.discordapp.com/badge-icons/3aa41de486fa12454c3761e8e223442e.png"),
)


@dataclass
class QuestTask:
    quest_id: str
    name: str
    task_type: str
    target: int
    progress: int
    enrolled: bool
    completed: bool
    application_id: str = ""
    icon_hash: str = ""
    expires_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def remaining(self) -> int:
        return max(0, int(self.target) - int(self.progress))

    @property
    def percent(self) -> int:
        if self.target <= 0:
            return 100 if self.completed else 0
        return min(100, int(self.progress * 100 / self.target))

    def icon_url(self, size: int = 64) -> str | None:
        if self.application_id and self.icon_hash:
            return f"https://cdn.discordapp.com/app-icons/{self.application_id}/{self.icon_hash}.png?size={size}"
        return None


class DiscordRest:
    def __init__(self, token: str, cookie: str = "", super_props: str | None = None) -> None:
        self.token = token.strip()
        self.cookie = cookie.strip()
        self.super_props = super_props or ScienceSession.new().super_props

    def _headers(self) -> dict[str, str]:
        headers = {
            "accept": "*/*",
            "accept-language": local_locale(),
            "authorization": self.token,
            "content-type": "application/json",
            "origin": "https://discord.com",
            "referer": "https://discord.com/quest-home",
            "user-agent": QUEST_UA or USER_AGENT,
            "x-debug-options": "bugReporterEnabled",
            "x-discord-locale": local_locale(),
            "x-discord-timezone": local_timezone(),
            "x-super-properties": self.super_props,
        }
        if self.cookie:
            headers["cookie"] = self.cookie
        return headers

    def request(self, method: str, path: str, body: Any | None = None) -> tuple[int, Any]:
        url = path if path.startswith("http") else f"{API}{path}"
        status, payload, _hdrs = http_request(
            method,
            url,
            headers=self._headers(),
            body=body,
            timeout=20,
            retries=3,
        )
        return status, payload

    def me(self) -> tuple[int, Any]:
        return self.request("GET", "/users/@me")

    def user_guilds(self) -> tuple[int, Any]:
        out: list[dict] = []
        after = ""
        last_status = 0
        for _ in range(20):
            path = "/users/@me/guilds?limit=200"
            if after:
                path = f"{path}&after={after}"
            status, payload = self.request("GET", path)
            last_status = status
            if status != 200:
                if out:
                    return 200, out
                return status, payload
            rows = payload
            if isinstance(payload, dict):
                rows = payload.get("guilds") or payload.get("items") or []
            if not isinstance(rows, list):
                if out:
                    return 200, out
                return status, payload
            batch = [item for item in rows if isinstance(item, dict) and item.get("id")]
            if not batch:
                break
            out.extend(batch)
            if len(batch) < 200:
                break
            after = str(batch[-1]["id"])
        return last_status or 200, out

    def guild_member(self, guild_id: str) -> tuple[int, Any]:
        gid = str(guild_id)
        last = (0, None)
        for path in (
            f"/users/@me/guilds/{gid}/member",
            f"/guilds/{gid}/members/@me",
        ):
            status, payload = self.request("GET", path)
            last = (status, payload)
            if status in (200, 204):
                return status, payload
            if status not in (404, 405):
                return status, payload
        return last

    def quests_me(self) -> tuple[int, Any]:
        status, data = self.request("GET", "/quests/@me?include_preview=true")
        if status == 200:
            return status, data
        return self.request("GET", "/quests/@me")

    def enroll(self, quest_id: str) -> tuple[int, Any]:
        return self.request("POST", f"/quests/{quest_id}/enroll", {})

    def video_progress(self, quest_id: str, timestamp: float) -> tuple[int, Any]:
        return self.request(
            "POST",
            f"/quests/{quest_id}/video-progress",
            {"timestamp": float(timestamp)},
        )

    def heartbeat(self, quest_id: str, stream_key: str, terminal: bool = False) -> tuple[int, Any]:
        return self.request(
            "POST",
            f"/quests/{quest_id}/heartbeat",
            {"stream_key": stream_key, "terminal": bool(terminal)},
        )

    def dm_channels(self) -> tuple[int, Any]:
        return self.request("GET", "/users/@me/channels")

    def hypesquad_join(self, house_id: int) -> tuple[int, Any]:
        return self.request("POST", "/hypesquad/online", {"house_id": int(house_id)})

    def hypesquad_leave(self) -> tuple[int, Any]:
        return self.request("DELETE", "/hypesquad/online")

    def settings(self) -> tuple[int, Any]:
        return self.request("GET", "/users/@me/settings")

    def entitlements(self) -> tuple[int, Any]:
        return self.request("GET", "/users/@me/entitlements")

    def connections(self) -> tuple[int, Any]:
        return self.request("GET", "/users/@me/connections")

    def set_custom_status(self, text: str, emoji_name: str | None = None) -> tuple[int, Any]:
        body: dict[str, Any] = {
            "custom_status": {
                "text": text.strip() or None,
                "expires_at": None,
                "emoji_id": None,
                "emoji_name": emoji_name,
            }
        }
        return self.request("PATCH", "/users/@me/settings", body)

    def set_clan(self, guild_id: str | None, enabled: bool = True) -> tuple[int, Any]:
        if not guild_id:
            bodies = (
                ("PUT", "/users/@me/clan", {"identity_enabled": False}),
                ("PUT", "/users/@me/primary-guild", {"identity_enabled": False}),
                ("PATCH", "/users/@me", {"clan": None, "primary_guild": None}),
            )
        else:
            gid = str(guild_id)
            body = {"identity_guild_id": gid, "identity_enabled": bool(enabled)}
            bodies = (
                ("PUT", "/users/@me/clan", body),
                ("PUT", "/users/@me/primary-guild", body),
                ("PATCH", "/users/@me", {"clan": body, "primary_guild": body}),
            )
        last = (0, {"message": "clan yok"})
        for method, path, payload in bodies:
            status, data = self.request(method, path, payload)
            last = (status, data)
            if status in (200, 201, 204):
                return status, data
            if status not in (404, 405):
                return status, data
        return last

    def claim_quest(self, quest_id: str) -> tuple[int, Any]:
        for path, body in (
            (f"/quests/{quest_id}/claim-reward", {}),
            (f"/quests/{quest_id}/claim", {}),
            (f"/quests/{quest_id}/rewards/claim", {}),
        ):
            status, data = self.request("POST", path, body)
            if status in (200, 201, 204) or status != 404:
                return status, data
        return 404, {"message": "claim yok"}

    def set_privacy(self, level: int) -> tuple[int, Any]:
        if level == 1:
            flags = {"all": False, "mutual_friends": False, "mutual_guilds": False}
            restricted = True
        elif level == 2:
            flags = {"all": False, "mutual_friends": True, "mutual_guilds": True}
            restricted = True
        else:
            flags = {"all": True, "mutual_friends": True, "mutual_guilds": True}
            restricted = False
        status, data = self.request(
            "PATCH",
            "/users/@me/profile",
            {"profile_visibility": int(level)},
        )
        if status in (200, 204):
            return status, data
        return self.request(
            "PATCH",
            "/users/@me/settings",
            {
                "friend_source_flags": flags,
                "default_guilds_restricted": restricted,
            },
        )


def house_from_flags(flags: int) -> int | None:
    for house_id, bit in HOUSE_FLAG.items():
        if flags & bit:
            return house_id
    return None


def _task_config(quest: dict[str, Any]) -> dict[str, Any]:
    config = quest.get("config") or {}
    return config.get("taskConfigV2") or config.get("taskConfig") or {}


SUPPORTED_TASKS = (
    "WATCH_VIDEO",
    "WATCH_VIDEO_ON_MOBILE",
    "PLAY_ON_DESKTOP",
    "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY",
)


def parse_quest(quest: dict[str, Any]) -> QuestTask | None:
    quest_id = str(quest.get("id") or "")
    if not quest_id:
        return None
    config = quest.get("config") or {}
    messages = config.get("messages") or {}
    name = str(messages.get("questName") or config.get("id") or quest_id)
    tasks = (_task_config(quest).get("tasks") or {})
    task_type = ""
    target = 0
    for key in SUPPORTED_TASKS:
        entry = tasks.get(key)
        if isinstance(entry, dict):
            task_type = key
            target = int(entry.get("target") or 0)
            break
        if entry:
            task_type = key
    status = quest.get("userStatus") or {}
    progress_map = status.get("progress") or {}
    progress = 0
    if task_type and isinstance(progress_map.get(task_type), dict):
        progress = int(progress_map[task_type].get("value") or 0)
    elif status.get("streamProgressSeconds"):
        progress = int(status.get("streamProgressSeconds") or 0)
    application = config.get("application") or {}
    assets = config.get("assets") or {}
    icon = str(application.get("icon") or assets.get("icon") or "")
    return QuestTask(
        quest_id=quest_id,
        name=name,
        task_type=task_type or "UNKNOWN",
        target=target,
        progress=progress,
        enrolled=bool(status.get("enrolledAt")),
        completed=bool(status.get("completedAt")) or (target > 0 and progress >= target),
        application_id=str(application.get("id") or ""),
        icon_hash=icon,
        expires_at=str(config.get("expiresAt") or ""),
        raw=quest,
    )


def parse_quest_list(payload: Any) -> list[QuestTask]:
    if not isinstance(payload, dict):
        return []
    items = list(payload.get("quests") or []) + list(payload.get("excluded_quests") or [])
    out: list[QuestTask] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = parse_quest(item)
        if parsed is None or parsed.quest_id in seen:
            continue
        seen.add(parsed.quest_id)
        out.append(parsed)
    return out
