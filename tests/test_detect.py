from __future__ import annotations

import unittest

from ky_gameplayer.detect import ProcessIndex
from ky_gameplayer.games import Game, GameCatalog
from ky_gameplayer.processes import RunningProcess, process_names


class DetectTests(unittest.TestCase):
    def test_match_exe(self) -> None:
        catalog = GameCatalog(
            [
                Game(
                    id="1",
                    name="Demo",
                    executables=[{"name": "overwatch.exe", "os": "win32", "is_launcher": False}],
                )
            ]
        )
        index = ProcessIndex(catalog)
        found = index.scan(
            [RunningProcess(pid=42, name="Overwatch.exe", cmdline="", exe=r"C:\Games\Overwatch.exe")]
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].game.id, "1")
        self.assertEqual(found[0].process.pid, 42)

    def test_skip_launcher(self) -> None:
        catalog = GameCatalog(
            [
                Game(
                    id="1",
                    name="Demo",
                    executables=[{"name": "launcher.exe", "os": "win32", "is_launcher": True}],
                )
            ]
        )
        index = ProcessIndex(catalog)
        found = index.scan(
            [RunningProcess(pid=1, name="launcher.exe", cmdline="", exe="launcher.exe")]
        )
        self.assertEqual(found, [])

    def test_process_names(self) -> None:
        names = process_names(
            RunningProcess(pid=1, name="Demo", cmdline="/opt/demo.bin --flag", exe="/opt/demo.bin")
        )
        self.assertIn("demo.bin", names)
        self.assertIn("demo", names)


if __name__ == "__main__":
    unittest.main()
