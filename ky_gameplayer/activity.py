from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ACTIVITY_TYPES = (
    (0, "Playing"),
    (1, "Streaming"),
    (2, "Listening"),
    (3, "Watching"),
    (4, "Custom"),
    (5, "Competing"),
)

STATUS_DISPLAY_TYPES = (
    (0, "Name"),
    (1, "State"),
    (2, "Details"),
)

ACTIVITY_FLAGS = (
    (1 << 0, "INSTANCE"),
    (1 << 1, "JOIN"),
    (1 << 2, "SPECTATE"),
    (1 << 3, "JOIN_REQUEST"),
    (1 << 4, "SYNC"),
    (1 << 5, "PLAY"),
    (1 << 6, "PARTY_PRIVACY_FRIENDS"),
    (1 << 7, "PARTY_PRIVACY_VOICE_CHANNEL"),
    (1 << 8, "EMBEDDED"),
)

PARTY_PRIVACY = (
    (0, "Private"),
    (1, "Public"),
)


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


def _clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            cleaned = _clean(value)
            if cleaned is None or cleaned == {} or cleaned == []:
                continue
            out[key] = cleaned
        return out
    if isinstance(obj, list):
        return [item for item in (_clean(x) for x in obj) if item is not None]
    return obj


@dataclass
class ActivityConfig:
    type: int = 0
    status_display_type: int = 0
    name: str | None = None
    url: str | None = None
    details: str | None = None
    details_url: str | None = None
    state: str | None = None
    state_url: str | None = None
    start: int | None = None
    end: int | None = None
    large_image: str | None = None
    large_text: str | None = None
    large_url: str | None = None
    small_image: str | None = None
    small_text: str | None = None
    small_url: str | None = None
    party_id: str | None = None
    party_size: int | None = None
    party_max: int | None = None
    party_privacy: int | None = None
    join_secret: str | None = None
    spectate_secret: str | None = None
    match_secret: str | None = None
    button1_label: str | None = None
    button1_url: str | None = None
    button2_label: str | None = None
    button2_url: str | None = None
    instance: bool = True
    flags: int | None = None
    emoji_name: str | None = None
    emoji_id: str | None = None
    emoji_animated: bool = False
    application_id: str | None = None
    pid: int | None = None
    use_elapsed: bool = True
    use_end: bool = False

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ActivityConfig:
        allowed = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in allowed})

    def buttons(self) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        label = _clip(self.button1_label, 32)
        url = _clip(self.button1_url, 512)
        if label and url:
            items.append({"label": label, "url": url})
        label = _clip(self.button2_label, 32)
        url = _clip(self.button2_url, 512)
        if label and url:
            items.append({"label": label, "url": url})
        return items

    def has_secrets(self) -> bool:
        return any(
            _clip(value, 128)
            for value in (self.join_secret, self.spectate_secret, self.match_secret)
        )

    def build(self) -> dict[str, Any] | None:
        activity: dict[str, Any] = {
            "type": int(self.type),
            "status_display_type": int(self.status_display_type),
            "instance": bool(self.instance),
        }
        name = _clip(self.name, 128)
        if name:
            activity["name"] = name
        details = _clip(self.details, 128)
        if details:
            activity["details"] = details
        details_url = _clip(self.details_url, 256)
        if details_url:
            activity["details_url"] = details_url
        state = _clip(self.state, 128)
        if state:
            activity["state"] = state
        state_url = _clip(self.state_url, 256)
        if state_url:
            activity["state_url"] = state_url
        if self.type == 1:
            url = _clip(self.url, 512)
            if url:
                activity["url"] = url

        timestamps: dict[str, int] = {}
        if self.start:
            timestamps["start"] = int(self.start)
        if self.end:
            timestamps["end"] = int(self.end)
        if timestamps:
            activity["timestamps"] = timestamps

        assets: dict[str, str] = {}
        large_image = _clip(self.large_image, 256)
        if large_image:
            assets["large_image"] = large_image
        large_text = _clip(self.large_text, 128)
        if large_text:
            assets["large_text"] = large_text
        large_url = _clip(self.large_url, 256)
        if large_url:
            assets["large_url"] = large_url
        small_image = _clip(self.small_image, 256)
        if small_image:
            assets["small_image"] = small_image
        small_text = _clip(self.small_text, 128)
        if small_text:
            assets["small_text"] = small_text
        small_url = _clip(self.small_url, 256)
        if small_url:
            assets["small_url"] = small_url
        if assets:
            activity["assets"] = assets

        party: dict[str, Any] = {}
        party_id = _clip(self.party_id, 128)
        if party_id:
            party["id"] = party_id
        if self.party_size is not None and self.party_max is not None:
            current = max(1, int(self.party_size))
            maximum = max(current, int(self.party_max))
            party["size"] = [current, maximum]
        if self.party_privacy is not None:
            party["privacy"] = int(self.party_privacy)
        if party:
            activity["party"] = party

        buttons = self.buttons()
        if buttons:
            activity["buttons"] = buttons
        elif self.has_secrets():
            secrets: dict[str, str] = {}
            join = _clip(self.join_secret, 128)
            spectate = _clip(self.spectate_secret, 128)
            match = _clip(self.match_secret, 128)
            if join:
                secrets["join"] = join
            if spectate:
                secrets["spectate"] = spectate
            if match:
                secrets["match"] = match
            if secrets:
                activity["secrets"] = secrets

        if self.flags:
            activity["flags"] = int(self.flags)

        emoji_name = _clip(self.emoji_name, 32)
        if emoji_name:
            emoji: dict[str, Any] = {"name": emoji_name}
            emoji_id = _clip(self.emoji_id, 32)
            if emoji_id:
                emoji["id"] = emoji_id
            emoji["animated"] = bool(self.emoji_animated)
            activity["emoji"] = emoji

        return _clean(activity)
