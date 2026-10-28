from __future__ import annotations

import json
import math
from collections.abc import Collection
from pathlib import Path
from typing import Any

from .activity import ActivityConfig
from .paths import atomic_write

SCHEMA_VERSION = 1

# Settings written by the UI are plain JSON values. Files can be edited by hand
# and the import dialog accepts arbitrary JSON, so every read goes through
# these coercers instead of a bare int()/float() call.
_BOOL_SETTINGS: dict[str, bool] = {
    "auto_reconnect": True,
    "idle_clear": False,
    "schedule_enabled": False,
    "detect_enabled": False,
    "detect_apply": False,
    "detect_pid": True,
    "science_enabled": False,
    "science_on_random": True,
    "science_on_detect": False,
    "science_on_current": True,
    "science_dry_run": False,
    "use_game_templates": True,
    "harvest_enabled": True,
}

_INT_SETTINGS: dict[str, tuple[int, int, int]] = {
    "random_interval": (60, 5, 86400),
    "random_norepeat": (8, 0, 50),
    "cycle_interval": (20, 5, 3600),
    "idle_seconds": (1800, 30, 86400),
    "science_batch": (20, 1, 200),
    "lock_timeout": (20, 5, 120),
}

_FLOAT_SETTINGS: dict[str, tuple[float, float, float]] = {
    "science_hours": (2.0, 0.01, 24.0),
    "science_delay": (0.8, 0.0, 10.0),
    "science_jitter": (0.05, 0.0, 0.5),
    "science_target_hours": (0.0, 0.0, 500.0),
}

_STR_SETTINGS: dict[str, tuple[str, Collection[str] | None]] = {
    "random_source": ("filter", {"filter", "all", "favorites", "playlist"}),
    "schedule_start": ("09:00", None),
    "schedule_end": ("23:00", None),
    "science_mode": ("playtime", {"playtime", "played"}),
    "science_source": ("current", {"current", "filter", "favorites", "playlist", "all", "missing"}),
    "lang": ("tr", {"tr", "en"}),
    "log_level": ("INFO", {"DEBUG", "INFO", "WARNING", "ERROR"}),
    "theme_mode": ("dark", {"system", "dark", "light"}),
}


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().casefold()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        result = default
    elif isinstance(value, int):
        result = value
    elif isinstance(value, float):
        result = int(value) if math.isfinite(value) else default
    elif isinstance(value, str):
        text = value.strip()
        try:
            result = int(text)
        except ValueError:
            try:
                number = float(text)
            except ValueError:
                result = default
            else:
                result = int(number) if math.isfinite(number) else default
    else:
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _as_float(value: Any, default: float, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool):
        result = default
    elif isinstance(value, (int, float)):
        try:
            result = float(value)
        except (OverflowError, ValueError):
            result = default
    elif isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            result = default
    else:
        result = default
    if not math.isfinite(result):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _as_str(value: Any, default: str, allowed: Collection[str] | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    if allowed is not None and value not in allowed:
        return default
    return value


def settings_bool(settings: dict[str, Any], key: str, default: bool) -> bool:
    return _as_bool(settings.get(key), default)


def settings_int(
    settings: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    return _as_int(settings.get(key), default, minimum, maximum)


def settings_float(
    settings: dict[str, Any],
    key: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    return _as_float(settings.get(key), default, minimum, maximum)


def settings_str(
    settings: dict[str, Any],
    key: str,
    default: str,
    *,
    allowed: Collection[str] | None = None,
) -> str:
    return _as_str(settings.get(key), default, allowed)


def sanitize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with known keys coerced, clamped and unknown keys kept."""
    clean = dict(settings)
    for key, default in _BOOL_SETTINGS.items():
        if key in clean:
            clean[key] = _as_bool(clean[key], default)
    for key, (default, minimum, maximum) in _INT_SETTINGS.items():
        if key in clean:
            clean[key] = _as_int(clean[key], default, minimum, maximum)
    for key, (default, minimum, maximum) in _FLOAT_SETTINGS.items():
        if key in clean:
            clean[key] = _as_float(clean[key], default, minimum, maximum)
    for key, (default, allowed) in _STR_SETTINGS.items():
        if key in clean:
            clean[key] = _as_str(clean[key], default, allowed)
    return clean


class ProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "last_game_id": None,
            "profiles": {},
            "favorites": [],
            "recents": [],
            "excluded": [],
            "playlist": [],
            "played": [],
            "weights": {},
            "settings": {"auto_reconnect": True},
        }
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(payload, dict):
            self.data.update(payload)
            if not isinstance(self.data.get("profiles"), dict):
                self.data["profiles"] = {}
            if not isinstance(self.data.get("game_templates"), dict):
                self.data["game_templates"] = {}
            for key in ("favorites", "recents", "excluded", "playlist", "played"):
                if not isinstance(self.data.get(key), list):
                    self.data[key] = []
            if not isinstance(self.data.get("weights"), dict):
                self.data["weights"] = {}
            if not isinstance(self.data.get("settings"), dict):
                self.data["settings"] = {}
            else:
                self.data["settings"] = sanitize_settings(self.data["settings"])
            version = self.data.get("schema_version")
            if not isinstance(version, int) or isinstance(version, bool):
                version = SCHEMA_VERSION
            self.data["schema_version"] = version

    def save(self) -> None:
        atomic_write(self.path, json.dumps(self.data, indent=2, ensure_ascii=False))

    def settings(self) -> dict[str, Any]:
        return self.data.setdefault("settings", {})

    @property
    def last_game_id(self) -> str | None:
        value = self.data.get("last_game_id")
        return str(value) if value else None

    @last_game_id.setter
    def last_game_id(self, game_id: str | None) -> None:
        self.data["last_game_id"] = game_id
        self.save()

    def names(self) -> list[str]:
        return sorted(self.data.get("profiles", {}).keys())

    def get(self, name: str) -> tuple[str | None, ActivityConfig] | None:
        raw = self.data.get("profiles", {}).get(name)
        if not isinstance(raw, dict):
            return None
        game_id = raw.get("game_id")
        activity = raw.get("activity")
        config = ActivityConfig.from_json(activity if isinstance(activity, dict) else {})
        return (str(game_id) if game_id else None, config)

    def put(self, name: str, game_id: str | None, config: ActivityConfig) -> None:
        profiles = self.data.setdefault("profiles", {})
        profiles[name] = {"game_id": game_id, "activity": config.to_json()}
        self.save()

    def delete(self, name: str) -> None:
        self.data.get("profiles", {}).pop(name, None)
        self.save()

    def game_template(self, game_id: str) -> ActivityConfig | None:
        raw = self.data.setdefault("game_templates", {}).get(game_id)
        if not isinstance(raw, dict):
            return None
        return ActivityConfig.from_json(raw)

    def put_game_template(self, game_id: str, config: ActivityConfig) -> None:
        templates = self.data.setdefault("game_templates", {})
        templates[game_id] = config.to_json()
        self.save()

    def delete_game_template(self, game_id: str) -> bool:
        templates = self.data.setdefault("game_templates", {})
        if game_id in templates:
            templates.pop(game_id)
            self.save()
            return True
        return False

    def _id_list(self, key: str) -> list[str]:
        values = self.data.setdefault(key, [])
        if not isinstance(values, list):
            values = []
            self.data[key] = values
        return [str(item) for item in values]

    def favorites(self) -> list[str]:
        return self._id_list("favorites")

    def recents(self) -> list[str]:
        return self._id_list("recents")

    def excluded(self) -> list[str]:
        return self._id_list("excluded")

    def playlist(self) -> list[str]:
        return self._id_list("playlist")

    def played(self) -> list[str]:
        return self._id_list("played")

    def mark_played(self, game_ids: list[str], limit: int = 50000) -> None:
        items = self.data.setdefault("played", [])
        have = set(str(x) for x in items)
        for game_id in game_ids:
            if game_id not in have:
                items.append(game_id)
                have.add(game_id)
        self.data["played"] = items[-limit:]
        self.save()

    def is_favorite(self, game_id: str) -> bool:
        return game_id in self.favorites()

    def toggle_favorite(self, game_id: str) -> bool:
        items = self.data.setdefault("favorites", [])
        if game_id in items:
            items.remove(game_id)
            self.save()
            return False
        items.append(game_id)
        self.save()
        return True

    def add_recent(self, game_id: str, limit: int = 20) -> None:
        items = [item for item in self._id_list("recents") if item != game_id]
        items.insert(0, game_id)
        self.data["recents"] = items[:limit]
        self.save()

    def toggle_excluded(self, game_id: str) -> bool:
        items = self.data.setdefault("excluded", [])
        if game_id in items:
            items.remove(game_id)
            self.save()
            return False
        items.append(game_id)
        self.save()
        return True

    def toggle_playlist(self, game_id: str) -> bool:
        items = self.data.setdefault("playlist", [])
        if game_id in items:
            items.remove(game_id)
            self.save()
            return False
        items.append(game_id)
        self.save()
        return True

    def weight(self, game_id: str) -> int:
        raw = self.data.get("weights") or {}
        try:
            return max(1, int(raw.get(game_id, 1)))
        except (TypeError, ValueError):
            return 1

    def set_weight(self, game_id: str, value: int) -> None:
        weights = self.data.setdefault("weights", {})
        weights[game_id] = max(1, min(20, int(value)))
        self.save()

    def dump(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.data))

    def merge_import(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return
        incoming = payload.get("profiles")
        if isinstance(incoming, dict):
            self.data.setdefault("profiles", {}).update(incoming)
        templates = payload.get("game_templates")
        if isinstance(templates, dict):
            self.data.setdefault("game_templates", {}).update(templates)
        for key in ("favorites", "recents", "excluded", "playlist"):
            extra = payload.get(key)
            if isinstance(extra, list):
                current = self.data.setdefault(key, [])
                for item in extra:
                    text = str(item)
                    if text not in current:
                        current.append(text)
        weights = payload.get("weights")
        if isinstance(weights, dict):
            self.data.setdefault("weights", {}).update(weights)
        settings = payload.get("settings")
        if isinstance(settings, dict):
            merged = dict(self.data.get("settings") or {})
            merged.update(settings)
            self.data["settings"] = sanitize_settings(merged)
        self.data["schema_version"] = SCHEMA_VERSION
        if payload.get("last_game_id"):
            self.data["last_game_id"] = payload["last_game_id"]
        self.save()
