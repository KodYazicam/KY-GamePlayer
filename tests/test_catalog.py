from __future__ import annotations

import unittest
from pathlib import Path

from ky_gameplayer.games import Game, GameCatalog
from ky_gameplayer.store import game_store_links, primary_store_button, store_url


ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = GameCatalog.load(ROOT / "games.json")

    def test_load_count(self) -> None:
        self.assertGreater(len(self.catalog.games), 10_000)
        self.assertEqual(len(self.catalog.by_id), len(self.catalog.games))

    def test_overwatch(self) -> None:
        game = self.catalog.get("356875221078245376")
        assert game is not None
        self.assertEqual(game.name, "Overwatch")
        self.assertTrue(game.icon_hash)
        self.assertTrue(any(sku.get("distributor") == "steam" for sku in game.third_party_skus))

    def test_filter_tokens(self) -> None:
        hits = self.catalog.filter(query="overwatch steam")
        self.assertTrue(any(g.name == "Overwatch" for g in hits))

    def test_filter_theme(self) -> None:
        hits = self.catalog.filter(theme="Horror", limit=20)
        self.assertTrue(hits)
        self.assertTrue(all("Horror" in g.themes for g in hits))

    def test_filter_os(self) -> None:
        hits = self.catalog.filter(os_name="linux", limit=5)
        self.assertTrue(hits)
        self.assertTrue(all("linux" in g.os_list() for g in hits))

    def test_icon_url(self) -> None:
        game = Game(id="1", name="X", icon_hash="abc")
        self.assertIn("/app-icons/1/abc.png", game.icon_url() or "")

    def test_skip_empty(self) -> None:
        self.assertTrue(all(g.id and g.name for g in self.catalog.games))


class CatalogRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = GameCatalog(
            [
                Game(id="1", name="Encounter Point"),
                Game(id="2", name="Counter-Strike 2"),
                Game(id="3", name="Counter"),
                Game(id="4", name="Point Counter"),
                Game(id="5", name="Grand Theft Auto V"),
                Game(id="6", name="Guitar Tuner App"),
            ]
        )

    def _names(self, query: str) -> list[str]:
        return [game.name for game in self.catalog.filter(query=query)]

    def test_exact_then_prefix_then_word_then_substring(self) -> None:
        self.assertEqual(
            self._names("counter"),
            ["Counter", "Counter-Strike 2", "Point Counter", "Encounter Point"],
        )

    def test_acronym_matches_name_initials(self) -> None:
        names = self._names("gta")
        self.assertEqual(names[:2], ["Grand Theft Auto V", "Guitar Tuner App"])

    def test_limit_applies_after_ranking(self) -> None:
        self.assertEqual([g.name for g in self.catalog.filter(query="counter", limit=1)], ["Counter"])

    def test_filters_still_apply_to_ranked_results(self) -> None:
        hits = self.catalog.filter(query="counter", overlay=False)
        self.assertEqual(len(hits), 4)


class StoreLinkTests(unittest.TestCase):
    def test_steam(self) -> None:
        self.assertEqual(
            store_url("steam", "2357570"),
            "https://store.steampowered.com/app/2357570",
        )

    def test_invalid_sku(self) -> None:
        self.assertIsNone(store_url("steam", "none"))
        self.assertIsNone(store_url("steam", ""))

    def test_primary_button(self) -> None:
        game = Game(
            id="1",
            name="X",
            third_party_skus=[
                {"distributor": "xbox", "id": "ABC"},
                {"distributor": "steam", "id": "123"},
            ],
        )
        links = game_store_links(game)
        self.assertEqual(links[0][0], "steam")
        button = primary_store_button(game)
        assert button is not None
        self.assertEqual(button["label"], "Steam")
        self.assertIn("steampowered.com", button["url"])


if __name__ == "__main__":
    unittest.main()
