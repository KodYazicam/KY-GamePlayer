from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ky_gameplayer.catalog_sync import sync, validate_games

ROOT = Path(__file__).resolve().parents[1]


def payload(count: int, name_prefix: str = "Game") -> list[dict]:
    return [{"id": str(1000 + i), "name": f"{name_prefix} {i}"} for i in range(count)]


class ValidateTests(unittest.TestCase):
    def test_accepts_list_with_valid_rows(self) -> None:
        self.assertEqual(validate_games(payload(3), minimum=3), 3)

    def test_counts_only_rows_with_id_and_name(self) -> None:
        rows = payload(3) + [{"id": "9"}, {"name": "NoId"}, "junk"]
        self.assertEqual(validate_games(rows, minimum=3), 3)

    def test_rejects_non_list(self) -> None:
        with self.assertRaises(ValueError):
            validate_games({"id": "1"}, minimum=1)

    def test_rejects_below_minimum(self) -> None:
        with self.assertRaises(ValueError):
            validate_games(payload(3), minimum=10)


class SyncTests(unittest.TestCase):
    def test_writes_validated_payload_and_backs_up_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(5, "Old")), encoding="utf-8")

            written, previous = sync(target, payload(7, "New"), minimum=7)
            self.assertEqual((written, previous), (7, 5))

            on_disk = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(len(on_disk), 7)
            self.assertEqual(on_disk[0]["name"], "New 0")

            backup = target.with_name("games.json.bak")
            backed_up = json.loads(backup.read_text(encoding="utf-8"))
            self.assertEqual(backed_up[0]["name"], "Old 0")

    def test_sync_without_existing_target_has_no_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            written, previous = sync(target, payload(4), minimum=4)
            self.assertEqual((written, previous), (4, 0))
            self.assertFalse(target.with_name("games.json.bak").exists())
    def test_sync_refuses_bad_payload_and_keeps_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(5, "Old")), encoding="utf-8")
            with self.assertRaises(ValueError):
                sync(target, [{"id": "1", "name": "x"}], minimum=10)  # type: ignore[arg-type]
            self.assertEqual(len(json.loads(target.read_text(encoding="utf-8"))), 5)


class CliSmokeTests(unittest.TestCase):
    def test_help_runs_without_qt(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ky_gameplayer.catalog_sync", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("detectables", result.stdout)
        self.assertIn("--check", result.stdout)


if __name__ == "__main__":
    unittest.main()
