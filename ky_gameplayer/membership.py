from __future__ import annotations

from dataclasses import dataclass

from .brand import GUILD_NAME, INVITE_URL, REQUIRED_GUILD_ID
from .discord_rest import DiscordRest
from .i18n import t


@dataclass
class Membership:
    ok: bool
    user_id: str = ""
    username: str = ""
    guild_id: str = REQUIRED_GUILD_ID
    guild_name: str = GUILD_NAME
    invite: str = INVITE_URL
    message: str = ""
    me: dict | None = None


def _sid(value: object) -> str:
    return str(value or "").strip()


def _guilds_contain(guilds: object, target: str) -> bool:
    if not isinstance(guilds, list):
        return False
    want = _sid(target)
    if not want:
        return False
    for guild in guilds:
        if not isinstance(guild, dict):
            continue
        if _sid(guild.get("id")) == want or _sid(guild.get("guild_id")) == want:
            return True
    return False


def _member_payload_ok(status: int, payload: object) -> bool:
    if status not in (200, 204):
        return False
    if not isinstance(payload, dict):
        return True
    code = payload.get("code")
    if code in (10004, 10007, 50001, 50013):
        return False
    if payload.get("message") and not payload.get("user") and not payload.get("roles") and not payload.get("joined_at"):
        return False
    return True


def check_membership(token: str, cookie: str = "") -> Membership:
    if not token.strip():
        return Membership(ok=False, message=t("lock_no_token"))
    rest = DiscordRest(token, cookie, super_props="e30=")
    status, me = rest.me()
    if status != 200 or not isinstance(me, dict) or not me.get("id"):
        message = me.get("message") if isinstance(me, dict) else str(me)
        return Membership(ok=False, message=t("lock_account_fail", status=status, message=message))
    user_id = _sid(me.get("id"))
    username = str(me.get("global_name") or me.get("username") or "")
    who = username or user_id
    base = dict(user_id=user_id, username=username, me=me)

    guilds_status, guilds = rest.user_guilds()
    if guilds_status == 200 and _guilds_contain(guilds, REQUIRED_GUILD_ID):
        return Membership(ok=True, **base)

    member_status, member = rest.guild_member(REQUIRED_GUILD_ID)
    if _member_payload_ok(member_status, member):
        return Membership(ok=True, **base)

    if guilds_status == 200:
        return Membership(
            ok=False,
            **base,
            message=t("lock_not_member_who", who=who, guild=GUILD_NAME, invite=INVITE_URL),
        )

    fail = member if isinstance(member, dict) else {}
    text = fail.get("message") if isinstance(fail, dict) else str(member)
    return Membership(
        ok=False,
        **base,
        message=t(
            "lock_member_fail",
            status=member_status,
            message=f"{text} · guilds={guilds_status} · {who}",
        ),
    )
