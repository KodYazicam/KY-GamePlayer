from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from ky_gameplayer.science import (
    HARD_CAP_GAMES,
    ScienceClient,
    ScienceGame,
    ScienceSession,
    ScienceState,
    chunked,
    farm,
    science_game_from,
    win_exe_from_entry,
)


class ScienceHelpersTests(unittest.TestCase):
    def test_win_exe_prefers_win32(self) -> None:
        game = {
            "executables": [
                {"os": "darwin", "name": "game.app"},
                {"os": "win32", "name": "game.exe"},
            ]
        }
        self.assertEqual(win_exe_from_entry(game), "game.exe")

    def test_chunked(self) -> None:
        items = [ScienceGame(str(i), f"g{i}", "e.exe") for i in range(5)]
        groups = list(chunked(items, 2))
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(groups[0]), 2)
        self.assertEqual(len(groups[-1]), 1)

    def test_session_props(self) -> None:
        session = ScienceSession.new()
        self.assertTrue(session.super_props)
        self.assertNotEqual(session.heartbeat_session, session.launch_signature)

    def test_science_game_from_object(self) -> None:
        class Fake:
            id = "99"
            name = "Demo"
            executables = [{"os": "win32", "name": "demo.exe"}]

        converted = science_game_from(Fake())
        self.assertEqual(converted.id, "99")
        self.assertEqual(converted.exe, "demo.exe")


class DryRunTests(unittest.TestCase):
    def _client(self) -> ScienceClient:
        state = ScienceState(token="t", cookie=None, fingerprint="", analytics_token="a", fetched_at=1e18)
        return ScienceClient(state, ScienceSession.new(), dry_run=True)

    def test_dry_run_post_skips_network(self) -> None:
        client = self._client()
        game = ScienceGame("1", "Game", "game.exe")
        events = client.build_session(game, 60_000)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = client.post(events)
        self.assertEqual(status, 204)
        self.assertIn("dry-run", stderr.getvalue())
        self.assertIn("3 events", stderr.getvalue())

    def test_farm_respects_hard_cap_without_confirmation(self) -> None:
        client = self._client()
        games = [ScienceGame(str(i), f"g{i}", "e.exe") for i in range(HARD_CAP_GAMES + 1)]
        with self.assertRaises(ValueError):
            farm(client, games, 60_000, delay=0, extra_delay=(0, 0))

    def test_farm_confirmed_over_cap_and_dry_run(self) -> None:
        client = self._client()
        games = [ScienceGame(str(i), f"g{i}", "e.exe") for i in range(HARD_CAP_GAMES + 10)]
        sent = farm(client, games, 60_000, delay=0, extra_delay=(0, 0), confirmed=True)
        self.assertEqual(sent, len(games))


if __name__ == "__main__":
    unittest.main()
