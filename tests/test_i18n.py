from __future__ import annotations

import string
import unittest

from ky_gameplayer import i18n


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        i18n._load()
        cls.tr = i18n.STRINGS["tr"]
        cls.en = i18n.STRINGS["en"]

    def test_languages_share_the_same_keys(self) -> None:
        self.assertEqual(set(self.tr), set(self.en))

    def test_placeholders_match_between_languages(self) -> None:
        mismatched = {
            key: (_fields(self.tr[key]), _fields(self.en[key]))
            for key in set(self.tr) & set(self.en)
            if _fields(self.tr[key]) != _fields(self.en[key])
        }
        self.assertEqual(mismatched, {})

    def test_lookup_falls_back_to_turkish(self) -> None:
        i18n.set_lang("en")
        self.addCleanup(i18n.set_lang, "tr")
        self.assertEqual(i18n.t("tab_games"), self.en["tab_games"])
        self.assertEqual(i18n.t("no_such_key_anywhere"), "no_such_key_anywhere")


if __name__ == "__main__":
    unittest.main()
