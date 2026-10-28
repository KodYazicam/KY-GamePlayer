from __future__ import annotations

import unittest
from unittest import mock

from ky_gameplayer import discord_rest
from ky_gameplayer.discord_rest import DiscordRest


class RequestTests(unittest.TestCase):
    def test_request_forwards_url_headers_and_body(self) -> None:
        rest = DiscordRest(" token ", " cookie ")
        with mock.patch.object(
            discord_rest, "http_request", return_value=(200, {"ok": True}, {})
        ) as request:
            status, payload = rest.request("POST", "/users/@me", {"a": 1})
        self.assertEqual((status, payload), (200, {"ok": True}))
        args, kwargs = request.call_args
        self.assertEqual(args, ("POST", "https://discord.com/api/v9/users/@me"))
        self.assertEqual(kwargs["body"], {"a": 1})
        self.assertEqual(kwargs["headers"]["authorization"], "token")
        self.assertEqual(kwargs["headers"]["cookie"], "cookie")
        self.assertEqual(kwargs["retries"], 3)

    def test_request_uses_absolute_url(self) -> None:
        rest = DiscordRest("tok")
        with mock.patch.object(
            discord_rest, "http_request", return_value=(204, None, {})
        ) as request:
            rest.request("GET", "https://example.invalid/x")
        self.assertEqual(request.call_args.args[1], "https://example.invalid/x")
        self.assertNotIn("cookie", request.call_args.kwargs["headers"])

    def test_headers_and_me(self) -> None:
        rest = DiscordRest("tok")
        headers = rest._headers()
        self.assertEqual(headers["origin"], "https://discord.com")
        self.assertIn("x-super-properties", headers)
        with mock.patch.object(rest, "request", return_value=(200, {"id": "1"})) as request:
            self.assertEqual(rest.me(), (200, {"id": "1"}))
        request.assert_called_once_with("GET", "/users/@me")


class GuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rest = DiscordRest("tok")

    def test_user_guilds_paginates_and_returns_short_page(self) -> None:
        first = [{"id": str(i)} for i in range(1, 201)]
        with mock.patch.object(
            self.rest,
            "request",
            side_effect=[(200, first), (200, [{"id": "201"}])],
        ) as request:
            status, rows = self.rest.user_guilds()
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 201)
        self.assertIn("after=200", request.call_args_list[1].args[1])

    def test_user_guilds_handles_dict_and_bad_payloads(self) -> None:
        with mock.patch.object(
            self.rest, "request", return_value=(200, {"guilds": [{"id": "1"}]})
        ):
            self.assertEqual(self.rest.user_guilds()[1], [{"id": "1"}])
        with mock.patch.object(self.rest, "request", return_value=(200, {"items": [{"id": "2"}]})):
            self.assertEqual(self.rest.user_guilds()[1], [{"id": "2"}])
        with mock.patch.object(self.rest, "request", return_value=(200, {"guilds": "not-a-list"})):
            self.assertEqual(self.rest.user_guilds(), (200, {"guilds": "not-a-list"}))
        with mock.patch.object(self.rest, "request", return_value=(200, [])):
            self.assertEqual(self.rest.user_guilds(), (200, []))

    def test_user_guilds_keeps_partial_rows_on_error(self) -> None:
        first = [{"id": str(i)} for i in range(200)]
        with mock.patch.object(
            self.rest, "request", side_effect=[(200, first), (500, {"message": "boom"})]
        ):
            status, rows = self.rest.user_guilds()
        self.assertEqual(status, 200)
        self.assertEqual(len(rows), 200)

    def test_user_guilds_returns_first_error(self) -> None:
        with mock.patch.object(self.rest, "request", return_value=(403, {"message": "no"})):
            self.assertEqual(self.rest.user_guilds(), (403, {"message": "no"}))

    def test_guild_member_falls_back(self) -> None:
        with mock.patch.object(
            self.rest, "request", side_effect=[(405, {}), (200, {"ok": True})]
        ):
            self.assertEqual(self.rest.guild_member("g"), (200, {"ok": True}))
        with mock.patch.object(
            self.rest, "request", side_effect=[(404, {}), (404, {})]
        ):
            self.assertEqual(self.rest.guild_member("g"), (404, {}))
        with mock.patch.object(self.rest, "request", return_value=(500, {"message": "x"})):
            self.assertEqual(self.rest.guild_member("g"), (500, {"message": "x"}))

    def test_quests_me_retries_without_preview(self) -> None:
        with mock.patch.object(
            self.rest, "request", side_effect=[(404, {}), (200, {"quests": []})]
        ) as request:
            self.assertEqual(self.rest.quests_me(), (200, {"quests": []}))
        self.assertNotIn("include_preview", request.call_args.args[1])


class ActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rest = DiscordRest("tok")

    def test_simple_actions(self) -> None:
        calls: list[tuple[str, str, object]] = []

        def fake(method: str, path: str, body: object = None):
            calls.append((method, path, body))
            return 204, None

        with mock.patch.object(self.rest, "request", side_effect=fake):
            self.rest.enroll("q")
            self.rest.video_progress("q", 12)
            self.rest.heartbeat("q", "stream", terminal=True)
            self.rest.dm_channels()
            self.rest.hypesquad_join(2)
            self.rest.hypesquad_leave()
            self.rest.settings()
            self.rest.entitlements()
            self.rest.connections()
            self.rest.application_assets("app")
            self.rest.set_custom_status("  ", emoji_name="x")
        self.assertIn(("POST", "/quests/q/enroll", {}), calls)
        self.assertEqual(calls[1][2], {"timestamp": 12.0})
        self.assertEqual(calls[2][2], {"stream_key": "stream", "terminal": True})
        self.assertIn(("GET", "/applications/app/assets", None), calls)
        self.assertEqual(calls[-1][2]["custom_status"]["text"], None)

    def test_set_clan_without_identity_stops_at_success(self) -> None:
        with mock.patch.object(
            self.rest, "request", side_effect=[(404, {}), (200, {"ok": True})]
        ) as request:
            self.assertEqual(self.rest.set_clan(None), (200, {"ok": True}))
        self.assertEqual(request.call_count, 2)

    def test_set_clan_with_identity_and_non_fallback_error(self) -> None:
        with mock.patch.object(self.rest, "request", return_value=(200, {"ok": True})) as request:
            self.assertEqual(self.rest.set_clan("42"), (200, {"ok": True}))
        self.assertEqual(request.call_args.args[2]["identity_guild_id"], "42")
        with mock.patch.object(
            self.rest, "request", side_effect=[(500, {"message": "x"})]
        ):
            self.assertEqual(self.rest.set_clan("42"), (500, {"message": "x"}))

    def test_claim_quest_tries_alternate_routes(self) -> None:
        with mock.patch.object(
            self.rest, "request", side_effect=[(404, {}), (201, {"ok": True})]
        ) as request:
            self.assertEqual(self.rest.claim_quest("q"), (201, {"ok": True}))
        self.assertTrue(request.call_args.args[1].endswith("/claim"))
        with mock.patch.object(self.rest, "request", return_value=(404, {})):
            self.assertEqual(self.rest.claim_quest("q"), (404, {"message": "claim yok"}))

    def test_set_privacy_levels(self) -> None:
        with mock.patch.object(self.rest, "request", return_value=(204, None)) as request:
            self.assertEqual(self.rest.set_privacy(1), (204, None))
        self.assertFalse(request.call_args.args[2]["profile_visibility"] == 0)

        with mock.patch.object(
            self.rest, "request", side_effect=[(500, {}), (200, {"ok": True})]
        ) as request:
            self.assertEqual(self.rest.set_privacy(2), (200, {"ok": True}))
        fallback = request.call_args.args[2]
        self.assertTrue(fallback["default_guilds_restricted"])

        with mock.patch.object(
            self.rest, "request", side_effect=[(403, {}), (204, None)]
        ) as request:
            self.assertEqual(self.rest.set_privacy(3), (204, None))
        self.assertFalse(request.call_args.args[2]["default_guilds_restricted"])


if __name__ == "__main__":
    unittest.main()
