from __future__ import annotations

from .games import Game

STORE_PRIORITY = (
    "steam",
    "epic",
    "gog",
    "uplay",
    "xbox",
    "microsoft",
    "battlenet",
    "google_play",
)


def store_url(distributor: str, sku: str | None) -> str | None:
    dist = (distributor or "").strip().lower()
    ident = str(sku or "").strip()
    if not ident or ident.lower() == "none":
        return None
    if dist == "steam" and ident.isdigit():
        return f"https://store.steampowered.com/app/{ident}"
    if dist == "epic":
        return f"https://store.epicgames.com/p/{ident}"
    if dist == "gog":
        slug = ident.replace(" ", "_").lower()
        return f"https://www.gog.com/en/game/{slug}"
    if dist in {"xbox", "microsoft"}:
        return f"https://www.microsoft.com/store/productId/{ident}"
    if dist == "google_play":
        return f"https://play.google.com/store/apps/details?id={ident}"
    if dist == "uplay":
        return f"https://store.ubisoft.com/game?query={ident}"
    if dist == "battlenet":
        return "https://us.shop.battle.net/"
    return None


def game_store_links(game: Game) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for sku in game.third_party_skus:
        dist = str(sku.get("distributor") or "")
        ident = sku.get("id")
        url = store_url(dist, None if ident is None else str(ident))
        if not url or url in seen:
            continue
        seen.add(url)
        out.append((dist, str(ident or ""), url))
    out.sort(key=lambda item: STORE_PRIORITY.index(item[0]) if item[0] in STORE_PRIORITY else 99)
    return out


def primary_store_button(game: Game) -> dict[str, str] | None:
    links = game_store_links(game)
    if not links:
        return None
    dist, _ident, url = links[0]
    labels = {
        "steam": "Steam",
        "epic": "Epic",
        "gog": "GOG",
        "xbox": "Xbox",
        "microsoft": "Microsoft",
        "uplay": "Ubisoft",
        "battlenet": "Battle.net",
        "google_play": "Play Store",
    }
    return {"label": labels.get(dist, dist.title())[:32], "url": url[:512]}
