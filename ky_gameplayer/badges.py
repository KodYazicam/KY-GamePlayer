from __future__ import annotations

from dataclasses import dataclass

from .i18n import t

BADGE_CDN = "https://cdn.discordapp.com/badge-icons/{hash}.png"

NITRO = {
    0: "nitro_none",
    1: "Nitro Classic",
    2: "Nitro",
    3: "Nitro Basic",
}

HOUSE_BADGES = (
    (1 << 6, "HypeSquad Bravery", "8a88d63823d8a71cd5e390baa45efa02"),
    (1 << 7, "HypeSquad Brilliance", "011940fd013da3f7fb926e4a1cd2e618"),
    (1 << 8, "HypeSquad Balance", "3aa41de486fa12454c3761e8e223442e"),
)

FLAG_BADGES = (
    (1 << 0, "Staff", "5e74e9b61934fc1f67c65515d1f7e60d", "badge_staff"),
    (1 << 1, "Partner", "3f9748e53446a137a052f3454e2de41e", "badge_partner"),
    (1 << 2, "HypeSquad Events", None, "badge_events"),
    (1 << 3, "Bug Hunter 1", None, "badge_bh1"),
    (1 << 9, "Early Supporter", None, "badge_early"),
    (1 << 14, "Bug Hunter 2", "848f79194d4be5ff5f81505cbd0ce1e6", "badge_bh2"),
    (1 << 17, "Early Verified Bot Dev", None, "badge_botdev"),
    (1 << 18, "Moderator Programs", None, "badge_mod"),
    (1 << 22, "Active Developer", None, "badge_active"),
)

GIFT_BADGES = (
    ("Patron", 1, "ac305d1b9481f312ce4419e7f8296558"),
    ("Champion", 2, "8b7792c4f65953d3ff564f23429cb79e"),
    ("Luminary", 3, "3119f5504b2cd09576a323908c7c3517"),
    ("Icon", 6, "64f2413c9b9803661322aaad25826b62"),
    ("Hero", 10, "77d65b1f210014a11eb1582ee06ab684"),
    ("Legend", 20, "7fe346cfc5da1340087d8759a9e7a395"),
)

CATALOG_BADGES = (
    ("Quest", "7d9ae358c8c5e118768335dbe68b4fb8"),
    ("Original user", "6de6d34650760ba5551a79732e98ed60"),
    ("Staff", "5e74e9b61934fc1f67c65515d1f7e60d"),
    ("Partner", "3f9748e53446a137a052f3454e2de41e"),
    ("Bug Hunter 2", "848f79194d4be5ff5f81505cbd0ce1e6"),
    ("Active Dev", None),
    ("Early Supporter", None),
    ("Bug Hunter 1", None),
    ("HypeSquad Events", None),
    ("Commands", None),
    ("AutoMod", None),
    ("Orbs", None),
)

NITRO_MONTHS = (
    ("nitro_1", 1),
    ("nitro_2", 2),
    ("nitro_3", 3),
    ("nitro_6", 6),
    ("nitro_12", 12),
    ("nitro_24", 24),
    ("nitro_36", 36),
    ("nitro_48", 48),
)


def badge_icon_url(icon_hash: str | None) -> str | None:
    if not icon_hash:
        return None
    return BADGE_CDN.format(hash=icon_hash)


@dataclass(frozen=True)
class BadgeState:
    name: str
    owned: bool
    icon_url: str | None
    how: str


def decode_flags(flags: int, premium_type: int = 0) -> list[BadgeState]:
    out: list[BadgeState] = []
    nitro_key = NITRO.get(int(premium_type), "Nitro")
    nitro = t(nitro_key) if nitro_key == "nitro_none" else nitro_key
    out.append(
        BadgeState(
            name=f"Nitro ({nitro})",
            owned=int(premium_type) > 0,
            icon_url=None,
            how=t("nitro_sub"),
        )
    )
    for bit, name, icon_hash in HOUSE_BADGES:
        out.append(
            BadgeState(
                name=name,
                owned=bool(flags & bit),
                icon_url=badge_icon_url(icon_hash),
                how=t("house_how"),
            )
        )
    for bit, name, icon_hash, how in FLAG_BADGES:
        out.append(
            BadgeState(
                name=name,
                owned=bool(flags & bit),
                icon_url=badge_icon_url(icon_hash),
                how=t(how),
            )
        )
    return out
