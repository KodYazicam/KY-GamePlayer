from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .activity import ActivityConfig
from .paths import atomic_write


class ProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {
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
            for key in ("favorites", "recents", "excluded", "playlist", "played"):
                if not isinstance(self.data.get(key), list):
                    self.data[key] = []
            if not isinstance(self.data.get("weights"), dict):
                self.data["weights"] = {}
            if not isinstance(self.data.get("settings"), dict):
                self.data["settings"] = {}

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
        config = ActivityConfig.from_json(raw.get("activity") or {})
        return (str(game_id) if game_id else None, config)

    def put(self, name: str, game_id: str | None, config: ActivityConfig) -> None:
        profiles = self.data.setdefault("profiles", {})
        profiles[name] = {"game_id": game_id, "activity": config.to_json()}
        self.save()

    def delete(self, name: str) -> None:
        self.data.get("profiles", {}).pop(name, None)
        self.save()

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
            self.data.setdefault("settings", {}).update(settings)
        if payload.get("last_game_id"):
            self.data["last_game_id"] = payload["last_game_id"]
        self.save()
