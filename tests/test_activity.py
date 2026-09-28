from __future__ import annotations

import unittest

from ky_gameplayer.activity import ActivityConfig, listening_config


class ActivityConfigTests(unittest.TestCase):
    def test_build_playing(self) -> None:
        cfg = ActivityConfig(
            type=0,
            details="Ranked",
            state="In game",
            large_image="cover",
            large_text="Overwatch",
            start=1_700_000_000,
            instance=True,
        )
        payload = cfg.build()
        assert payload is not None
        self.assertEqual(payload["type"], 0)
        self.assertEqual(payload["details"], "Ranked")
        self.assertEqual(payload["state"], "In game")
        self.assertEqual(payload["assets"]["large_image"], "cover")
        self.assertEqual(payload["timestamps"]["start"], 1_700_000_000)
        self.assertTrue(payload["instance"])

    def test_buttons_win_over_secrets(self) -> None:
        cfg = ActivityConfig(
            button1_label="Steam",
            button1_url="https://store.steampowered.com/app/1",
            join_secret="secret",
        )
        payload = cfg.build()
        assert payload is not None
        self.assertIn("buttons", payload)
        self.assertNotIn("secrets", payload)
        self.assertEqual(payload["buttons"][0]["label"], "Steam")

    def test_secrets_when_no_buttons(self) -> None:
        cfg = ActivityConfig(join_secret="join-me", spectate_secret="spec")
        payload = cfg.build()
        assert payload is not None
        self.assertEqual(payload["secrets"]["join"], "join-me")
        self.assertEqual(payload["secrets"]["spectate"], "spec")

    def test_clip_empty_fields(self) -> None:
        cfg = ActivityConfig(details="   ", state="")
        payload = cfg.build()
        assert payload is not None
        self.assertNotIn("details", payload)
        self.assertNotIn("state", payload)

    def test_roundtrip_json(self) -> None:
        cfg = ActivityConfig(type=1, url="https://twitch.tv/x", details="live")
        restored = ActivityConfig.from_json(cfg.to_json())
        self.assertEqual(restored.type, 1)
        self.assertEqual(restored.url, "https://twitch.tv/x")
        self.assertEqual(restored.details, "live")

    def test_party_size(self) -> None:
        cfg = ActivityConfig(party_id="abc", party_size=2, party_max=5, party_privacy=1)
        payload = cfg.build()
        assert payload is not None
        self.assertEqual(payload["party"]["size"], [2, 5])
        self.assertEqual(payload["party"]["privacy"], 1)

    def test_streaming_url_only_for_type_1(self) -> None:
        playing = ActivityConfig(type=0, url="https://twitch.tv/x").build()
        streaming = ActivityConfig(type=1, url="https://twitch.tv/x").build()
        assert playing is not None and streaming is not None
        self.assertNotIn("url", playing)
        self.assertEqual(streaming["url"], "https://twitch.tv/x")


class ListeningHelperTests(unittest.TestCase):
    def test_listening_config_shape(self) -> None:
        cfg = listening_config(
            "Nightcall",
            "Kavinsky",
            album="OutRun",
            art_url="https://example.com/cover.png",
            duration_s=180,
            game_id="42",
        )
        self.assertEqual(cfg.type, 2)
        self.assertEqual(cfg.name, "Nightcall")
        self.assertEqual(cfg.details, "Kavinsky — OutRun")
        self.assertEqual(cfg.large_image, "https://example.com/cover.png")
        self.assertEqual(cfg.large_text, "OutRun")
        self.assertEqual(cfg.application_id, "42")
        self.assertTrue(cfg.use_elapsed)
        self.assertTrue(cfg.use_end)
        payload = cfg.build()
        assert payload is not None
        self.assertEqual(payload["type"], 2)
        self.assertIn("end", payload["timestamps"])
        self.assertIn("start", payload["timestamps"])

    def test_listening_config_minimal_has_no_timestamps(self) -> None:
        cfg = listening_config("Track")
        payload = cfg.build()
        assert payload is not None
        self.assertEqual(payload["name"], "Track")
        self.assertNotIn("details", payload)
        self.assertNotIn("timestamps", payload)

    def test_listening_config_empty_track(self) -> None:
        cfg = listening_config("")
        payload = cfg.build()
        assert payload is not None
        self.assertNotIn("name", payload)


if __name__ == "__main__":
    unittest.main()
