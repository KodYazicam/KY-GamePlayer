from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from ky_gameplayer.activity import ActivityConfig
from ky_gameplayer.hooks import load_hook, run_hook


class FakeGame:
    id = "42"
    name = "Hook Quest"


def _write_hook(tmp: str, body: str) -> Path:
    path = Path(tmp) / "hook.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_hook_returning_config(self) -> None:
        path = _write_hook(
            self.tmp.name,
            """
            from ky_gameplayer.activity import ActivityConfig
            def build_activity(game):
                return ActivityConfig(name=game.name, details="from hook")
            """,
        )
        hook = load_hook(path)
        config = run_hook(hook, FakeGame())
        self.assertIsInstance(config, ActivityConfig)
        self.assertEqual(config.name, "Hook Quest")
        self.assertEqual(config.details, "from hook")

    def test_hook_returning_dict_and_none(self) -> None:
        path = _write_hook(
            self.tmp.name,
            """
            def build_activity(game):
                return {"name": game.name, "type": 2}
            """,
        )
        config = run_hook(load_hook(path), FakeGame())
        self.assertEqual(config.name, "Hook Quest")
        self.assertEqual(config.type, 2)

        path_none = _write_hook(self.tmp.name, "def build_activity(game):\n    return None\n")
        self.assertIsNone(run_hook(load_hook(path_none), FakeGame()))

    def test_hook_errors_are_wrapped(self) -> None:
        broken = _write_hook(self.tmp.name, "def build_activity(game):\n    raise RuntimeError('nope')\n")
        with self.assertRaises(ValueError):
            run_hook(load_hook(broken), FakeGame())

        bad_import = _write_hook(self.tmp.name, "raise SyntaxError('bad')\n")
        with self.assertRaises(ValueError):
            load_hook(bad_import)

        no_hook = _write_hook(self.tmp.name, "x = 1\n")
        with self.assertRaises(ValueError):
            load_hook(no_hook)

        with self.assertRaises(ValueError):
            load_hook(Path(self.tmp.name) / "missing.py")

        bad_return = _write_hook(self.tmp.name, "def build_activity(game):\n    return 42\n")
        with self.assertRaises(ValueError):
            run_hook(load_hook(bad_return), FakeGame())

    def test_non_python_file_rejected(self) -> None:
        path = Path(self.tmp.name) / "hook.txt"
        path.write_text("def build_activity(game): pass", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_hook(path)


if __name__ == "__main__":
    unittest.main()
