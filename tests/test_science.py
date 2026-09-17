from __future__ import annotations

import unittest

from ky_gameplayer.science import (
    ScienceGame,
    ScienceSession,
    chunked,
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


if __name__ == "__main__":
    unittest.main()
