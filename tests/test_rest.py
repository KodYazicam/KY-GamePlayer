from __future__ import annotations

import unittest

from ky_gameplayer.badges import decode_flags
from ky_gameplayer.brand import APP_TITLE, INVITE_URL, REQUIRED_GUILD_ID
from ky_gameplayer.discord_rest import house_from_flags, parse_quest, parse_quest_list
from ky_gameplayer.i18n import set_lang, t
from ky_gameplayer.membership import _guilds_contain, _member_payload_ok


class RestParseTests(unittest.TestCase):
    def test_parse_video_quest(self) -> None:
        payload = {
            "id": "q1",
            "config": {
                "messages": {"questName": "Watch ad"},
                "taskConfigV2": {"tasks": {"WATCH_VIDEO": {"target": 30}}},
                "application": {"id": "app", "icon": "hash"},
            },
            "userStatus": {"enrolledAt": "now", "progress": {"WATCH_VIDEO": {"value": 10}}},
        }
        task = parse_quest(payload)
        assert task is not None
        self.assertEqual(task.name, "Watch ad")
        self.assertEqual(task.task_type, "WATCH_VIDEO")
        self.assertEqual(task.progress, 10)
        self.assertEqual(task.target, 30)
        self.assertFalse(task.completed)
        self.assertTrue(task.enrolled)

    def test_parse_list_dedupes(self) -> None:
        item = {
            "id": "q1",
            "config": {"taskConfig": {"tasks": {"PLAY_ON_DESKTOP": {"target": 60}}}},
            "userStatus": {},
        }
        tasks = parse_quest_list({"quests": [item], "excluded_quests": [item]})
        self.assertEqual(len(tasks), 1)

    def test_house_from_flags(self) -> None:
        self.assertEqual(house_from_flags(1 << 6), 1)
        self.assertEqual(house_from_flags(1 << 7), 2)
        self.assertEqual(house_from_flags(1 << 8), 3)
        self.assertIsNone(house_from_flags(0))


class MembershipHelpersTests(unittest.TestCase):
    def test_guilds_contain(self) -> None:
        self.assertTrue(_guilds_contain([{"id": REQUIRED_GUILD_ID}], REQUIRED_GUILD_ID))
        self.assertFalse(_guilds_contain([{"id": "1"}], REQUIRED_GUILD_ID))
        self.assertFalse(_guilds_contain({}, REQUIRED_GUILD_ID))

    def test_member_payload(self) -> None:
        self.assertTrue(_member_payload_ok(200, {"user": {"id": "1"}}))
        self.assertFalse(_member_payload_ok(200, {"code": 10007, "message": "Unknown Member"}))
        self.assertFalse(_member_payload_ok(404, {}))


class BadgeAndI18nTests(unittest.TestCase):
    def test_decode_flags(self) -> None:
        states = decode_flags(1 << 6, premium_type=2)
        names = {item.name for item in states}
        self.assertTrue(any(item.owned and "Bravery" in item.name for item in states))
        self.assertTrue(any("Nitro" in item.name and item.owned for item in states))
        self.assertIn("Staff", names)

    def test_i18n_switch(self) -> None:
        set_lang("en")
        self.assertEqual(t("tab_games"), "Games")
        set_lang("tr")
        self.assertEqual(t("tab_games"), "Oyun menüsü")
        self.assertIn("{n}", t("games_count"))
        self.assertEqual(t("games_count", n=3), "3 oyun")

    def test_brand(self) -> None:
        self.assertEqual(APP_TITLE, "KodYazar Client")
        self.assertTrue(INVITE_URL.startswith("https://discord.gg/"))
        self.assertTrue(REQUIRED_GUILD_ID.isdigit())


if __name__ == "__main__":
    unittest.main()
