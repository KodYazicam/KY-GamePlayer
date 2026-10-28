from __future__ import annotations




from ..client_auth import harvest, list_running_clients
from ..discord_rest import DiscordRest
from ..i18n import t as i18n


class AccountMixin:
    def _refresh_clients(self) -> None:
        if not hasattr(self, "client_box"):
            return
        try:
            self._clients = list_running_clients()
        except Exception:
            self._clients = []
        self.client_box.blockSignals(True)
        current = self.client_box.currentData()
        self.client_box.clear()
        self.client_box.addItem(i18n("client_auto"), None)
        for item in self._clients:
            self.client_box.addItem(f"{item.name}  pid {item.pid}", item.pid)
        if current is not None:
            idx = self.client_box.findData(current)
            if idx >= 0:
                self.client_box.setCurrentIndex(idx)
        self.client_box.blockSignals(False)
        self._on_client_picked()

    def _on_client_picked(self, *_args) -> None:
        pid = self.client_box.currentData() if hasattr(self, "client_box") else None
        self._preferred_client = None
        if pid is not None:
            for item in self._clients:
                if item.pid == pid:
                    self._preferred_client = item
                    break
        self.science.preferred = self._preferred_client
        self.quest_engine.preferred = self._preferred_client

    def _rest(self) -> DiscordRest:
        auth = harvest(self._preferred_client)
        return DiscordRest(auth.token, auth.cookie)

    def _refresh_account(self) -> None:
        if not self._member_ok or getattr(self, "_account_busy", False):
            return
        self._account_busy = True

        def work():
            rest = self._rest()
            st_me, me = rest.me()
            st_set, settings = rest.settings()
            st_ent, ents = rest.entitlements()
            st_g, guilds = rest.user_guilds()
            return st_me, me, st_set, settings, st_ent, ents, st_g, guilds

        self.tasks.submit(
            work,
            on_done=self._apply_account,
            on_error=self._on_account_error,
            name="account",
        )

    def _apply_account(self, payload) -> None:
        self._account_busy = False
        st_me, me, st_set, settings, st_ent, ents, st_g, guilds = payload
        if st_ent == 200 and isinstance(ents, dict):
            ents = ents.get("entitlements") or ents.get("items") or []
        if st_g == 200 and isinstance(guilds, dict):
            guilds = guilds.get("guilds") or guilds.get("items") or []
        guild_list = guilds if isinstance(guilds, list) and st_g == 200 else []
        if st_me == 200 and isinstance(me, dict):
            self.pages.set_account_details(
                me,
                settings if st_set == 200 and isinstance(settings, dict) else None,
                ents if st_ent == 200 and isinstance(ents, list) else [],
                guild_list,
            )
            if st_g != 200:
                message = guilds.get("message") if isinstance(guilds, dict) else str(guilds)
                self._set_status(f"Sunucular [{st_g}] {message}")
            elif not guild_list:
                self._set_status(i18n("clan_none"))

    def _on_account_error(self, exc: BaseException) -> None:
        self._account_busy = False
        self._set_status(i18n("status_account_err", message=exc))

    def _apply_status(self, text: str) -> None:
        if not self._require_member():
            return

        def done(result) -> None:
            status, data = result
            if status in (200, 204):
                self._set_status(i18n("status_custom"))
            else:
                message = data.get("message") if isinstance(data, dict) else str(data)
                self._set_status(f"Durum [{status}] {message}")

        self.tasks.submit(
            lambda: self._rest().set_custom_status(text),
            on_done=done,
            on_error=lambda exc: self._set_status(i18n("status_custom_err", message=exc)),
            name="status",
        )

    def _apply_clan(self, guild_id: str) -> None:
        if not self._require_member():
            return

        def done(result) -> None:
            status, data = result
            if status in (200, 204):
                self._set_status(i18n("status_clan"))
                self._refresh_account()
            else:
                message = data.get("message") if isinstance(data, dict) else str(data)
                self._set_status(f"Clan [{status}] {message}")

        self.tasks.submit(
            lambda: self._rest().set_clan(guild_id or None, bool(guild_id)),
            on_done=done,
            on_error=lambda exc: self._set_status(i18n("status_clan_err", message=exc)),
            name="clan",
        )

    def _start_quests(self) -> None:
        if not self._require_member():
            return
        self.quest_engine.start()

    def _set_house(self, house_id: int) -> None:
        if not self._require_member():
            return
        self.quest_engine.set_house(house_id)

    def _leave_house(self) -> None:
        if not self._require_member():
            return
        self.quest_engine.leave_house()

    def _set_privacy(self, level: int) -> None:
        if not self._require_member():
            return
        self.quest_engine.set_privacy(level)

    def _on_quest_log(self, key: str, params: dict | None = None) -> None:
        self._log(key=key, **dict(params or {}))

    def _on_quest_failed(self, message: str) -> None:
        self._log(key="log_quest_err", message=message)
        self._set_status(i18n("status_quest_err", message=message))

    def _on_quest_finished(self, ok: int, total: int) -> None:
        self._log(key="log_quest_done", ok=ok, total=total)
        self._set_status(i18n("status_quest_done", ok=ok, total=total))
        self.quest_engine.refresh()

    def _on_quest_house(self, house_id: int, name: str) -> None:
        self._set_status(i18n("status_hypesquad", name=name))

    def _on_quest_privacy(self, level: int, name: str) -> None:
        self._set_status(i18n("status_privacy", name=name))
