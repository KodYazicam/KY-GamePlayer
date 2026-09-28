from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ky_gameplayer.activity import ActivityConfig
from ky_gameplayer.paths import atomic_write
from ky_gameplayer.profiles import ProfileStore


class ProfileStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "profiles.json"
        self.store = ProfileStore(self.path)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_put_get_delete(self) -> None:
        cfg = ActivityConfig(details="hi")
        self.store.put("main", "123", cfg)
        loaded = self.store.get("main")
        assert loaded is not None
        game_id, activity = loaded
        self.assertEqual(game_id, "123")
        self.assertEqual(activity.details, "hi")
        self.store.delete("main")
        self.assertIsNone(self.store.get("main"))

    def test_favorites_and_recents(self) -> None:
        self.assertTrue(self.store.toggle_favorite("a"))
        self.assertFalse(self.store.toggle_favorite("a"))
        self.store.add_recent("b")
        self.store.add_recent("c")
        self.store.add_recent("b")
        self.assertEqual(self.store.recents()[0], "b")
        self.assertEqual(self.store.weight("missing"), 1)
        self.store.set_weight("b", 99)
        self.assertEqual(self.store.weight("b"), 20)

    def test_merge_import(self) -> None:
        self.store.merge_import(
            {
                "profiles": {"x": {"game_id": "1", "activity": {"details": "z"}}},
                "game_templates": {"7": {"details": "tpl"}},
                "favorites": ["1"],
                "last_game_id": "1",
            }
        )
        self.assertIn("x", self.store.names())
        self.assertEqual(self.store.last_game_id, "1")
        self.assertIn("1", self.store.favorites())
        template = self.store.game_template("7")
        assert template is not None
        self.assertEqual(template.details, "tpl")

    def test_game_templates_roundtrip(self) -> None:
        cfg = ActivityConfig(type=2, name="Track", details="Artist — Album")
        self.assertIsNone(self.store.game_template("42"))
        self.store.put_game_template("42", cfg)
        loaded = self.store.game_template("42")
        assert loaded is not None
        self.assertEqual(loaded.type, 2)
        self.assertEqual(loaded.name, "Track")
        self.assertTrue(self.store.delete_game_template("42"))
        self.assertFalse(self.store.delete_game_template("42"))
        self.assertIsNone(self.store.game_template("42"))
        # templates survive a reload
        self.store.put_game_template("42", cfg)
        reloaded = ProfileStore(self.path)
        again = reloaded.game_template("42")
        assert again is not None
        self.assertEqual(again.name, "Track")

    def test_atomic_write(self) -> None:
        target = Path(self.tmp.name) / "out.txt"
        atomic_write(target, "hello")
        self.assertEqual(target.read_text(encoding="utf-8"), "hello")


if __name__ == "__main__":
    unittest.main()
