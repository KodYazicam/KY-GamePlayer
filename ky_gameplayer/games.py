from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CDN_APP_ICONS = "https://cdn.discordapp.com/app-icons/{app_id}/{hash}.png"


@dataclass(slots=True)
class Game:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    icon_hash: str | None = None
    cover_image_hash: str | None = None
    themes: list[str] = field(default_factory=list)
    executables: list[dict[str, Any]] = field(default_factory=list)
    third_party_skus: list[dict[str, Any]] = field(default_factory=list)
    hook: bool = False
    overlay: bool = False
    overlay_compatibility_hook: bool = False
    overlay_methods: int = 0
    overlay_warn: bool = False
    content_classification: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def search_blob(self) -> str:
        parts = [self.name, self.id, *self.aliases, *self.themes]
        for sku in self.third_party_skus:
            dist = sku.get("distributor")
            sid = sku.get("id")
            if dist:
                parts.append(str(dist))
            if sid:
                parts.append(str(sid))
        for exe in self.executables:
            name = exe.get("name")
            if name:
                parts.append(str(name))
        return " ".join(parts).casefold()

    def icon_url(self, size: int = 128) -> str | None:
        if not self.icon_hash:
            return None
        return f"{CDN_APP_ICONS.format(app_id=self.id, hash=self.icon_hash)}?size={size}"

    def cover_url(self, size: int = 256) -> str | None:
        if not self.cover_image_hash:
            return None
        return f"{CDN_APP_ICONS.format(app_id=self.id, hash=self.cover_image_hash)}?size={size}"

    def distributors(self) -> list[str]:
        seen: list[str] = []
        for sku in self.third_party_skus:
            dist = sku.get("distributor")
            if dist and dist not in seen:
                seen.append(str(dist))
        return seen

    def os_list(self) -> list[str]:
        seen: list[str] = []
        for exe in self.executables:
            os_name = exe.get("os")
            if os_name and os_name not in seen:
                seen.append(str(os_name))
        return seen


def _as_game(item: dict[str, Any]) -> Game | None:
    game_id = str(item.get("id") or "").strip()
    name = str(item.get("name") or "").strip()
    if not game_id or not name:
        return None
    aliases = [str(a) for a in (item.get("aliases") or []) if a]
    themes = [str(t) for t in (item.get("themes") or []) if t]
    return Game(
        id=game_id,
        name=name,
        aliases=aliases,
        icon_hash=item.get("icon_hash") or None,
        cover_image_hash=item.get("cover_image_hash") or None,
        themes=themes,
        executables=list(item.get("executables") or []),
        third_party_skus=list(item.get("third_party_skus") or []),
        hook=bool(item.get("hook")),
        overlay=bool(item.get("overlay")),
        overlay_compatibility_hook=bool(item.get("overlay_compatibility_hook")),
        overlay_methods=int(item.get("overlay_methods") or 0),
        overlay_warn=bool(item.get("overlay_warn")),
        content_classification=dict(item.get("content_classification") or {}),
        raw=item,
    )


class GameCatalog:
    def __init__(self, games: list[Game]) -> None:
        self.games = games
        self.by_id = {game.id: game for game in games}
        self.themes = sorted({theme for game in games for theme in game.themes})
        self.distributors = sorted(
            {dist for game in games for dist in game.distributors()}
        )

    @classmethod
    def load(cls, path: Path) -> GameCatalog:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("games.json liste olmalı")
        games: list[Game] = []
        for item in payload:
            if isinstance(item, dict):
                game = _as_game(item)
                if game is not None:
                    games.append(game)
        games.sort(key=lambda g: g.name.casefold())
        return cls(games)

    def get(self, game_id: str) -> Game | None:
        return self.by_id.get(game_id)

    def filter(
        self,
        query: str = "",
        theme: str | None = None,
        distributor: str | None = None,
        os_name: str | None = None,
        has_icon: bool | None = None,
        has_cover: bool | None = None,
        overlay: bool | None = None,
        limit: int | None = None,
    ) -> list[Game]:
        needle = " ".join(query.casefold().split())
        tokens = needle.split() if needle else []
        out: list[Game] = []
        for game in self.games:
            if tokens and not all(token in game.search_blob for token in tokens):
                continue
            if theme and theme not in game.themes:
                continue
            if distributor and distributor not in game.distributors():
                continue
            if os_name and os_name not in game.os_list():
                continue
            if has_icon is True and not game.icon_hash:
                continue
            if has_icon is False and game.icon_hash:
                continue
            if has_cover is True and not game.cover_image_hash:
                continue
            if has_cover is False and game.cover_image_hash:
                continue
            if overlay is True and not game.overlay:
                continue
            if overlay is False and game.overlay:
                continue
            out.append(game)
            if limit is not None and len(out) >= limit:
                break
        return out
