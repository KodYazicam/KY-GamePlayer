"""Qt-level tests.

The default CI unit-test job intentionally does not install PySide6, so this
module skips there and runs in the dedicated ``ui`` job (offscreen).
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - PySide6 is optional for the core suite
    raise unittest.SkipTest("PySide6 is not installed") from None

from ky_gameplayer.ui.tasks import TaskRunner


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TaskRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def _pump(self, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.01)

    def test_result_is_delivered_on_the_gui_thread(self) -> None:
        runner = TaskRunner()
        seen: list[object] = []
        runner.submit(lambda: 21 * 2, on_done=seen.append, name="test")
        self._pump(lambda: bool(seen))
        self.assertEqual(seen, [42])
        self.assertEqual(runner.pending, 0)

    def test_error_is_delivered(self) -> None:
        runner = TaskRunner()
        errors: list[BaseException] = []

        def boom() -> None:
            raise ValueError("nope")

        runner.submit(boom, on_error=errors.append, name="test-error")
        self._pump(lambda: bool(errors))
        self.assertIsInstance(errors[0], ValueError)
        self.assertEqual(runner.pending, 0)

    def test_unhandled_error_does_not_keep_the_job(self) -> None:
        runner = TaskRunner()

        def boom() -> None:
            raise RuntimeError("silent")

        runner.submit(boom, name="test-silent")
        self._pump(lambda: runner.pending == 0)
        self.assertEqual(runner.pending, 0)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_row_index_follows_resets(self) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPixmap

        from ky_gameplayer.games import Game
        from ky_gameplayer.model import GameListModel

        model = GameListModel()
        first = [Game(id="a", name="A"), Game(id="b", name="B")]
        model.reset_games(first)
        self.assertEqual(model.index_for_id("b"), 1)
        self.assertEqual(model.index_for_id("missing"), -1)

        icon = QPixmap(4, 4)
        icon.fill(QColor("#ff0000"))
        model.set_icon("b", icon)
        stored = model.index(1).data(Qt.ItemDataRole.DecorationRole)
        self.assertEqual(stored.cacheKey(), icon.cacheKey())

        model.reset_games(list(reversed(first)))
        self.assertEqual(model.index_for_id("a"), 1)
        self.assertEqual(model.index_for_id("b"), 0)


@unittest.skipUnless(os.environ.get("KODYAZAR_UI_TESTS"), "set KODYAZAR_UI_TESTS=1 to build the window")
class WindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()

    def test_main_window_builds_with_theme(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.paths import app_root

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                win.show()
                self.app.processEvents()
                self.assertTrue(win.windowTitle())
                self.assertIsNotNone(win.pages)
                win.tasks.cancel_all()
                self.assertEqual(win.tasks.pending, 0)

    def test_theme_switch_persists(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.paths import app_root
        from ky_gameplayer.ui import theme

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                try:
                    win._on_setting_changed("theme_mode", "light")
                    self.assertEqual(win.store.settings()["theme_mode"], "light")
                    self.assertEqual(theme.mode(), "light")
                    self.assertIn(theme.LIGHT.BG, self.app.styleSheet())
                finally:
                    win.tasks.cancel_all()
                    theme.apply_theme(self.app, "dark")

    def test_diagnostics_copy_is_redacted(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.paths import app_root

        token = "A" * 24 + "." + "B" * 6 + "." + "C" * 27
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                try:
                    win._log(text=f"token={token}")
                    win._copy_diagnostics()
                    report = self.app.clipboard().text()
                finally:
                    win.tasks.cancel_all()
                    win.hide()
                    win.deleteLater()
                    self.app.processEvents()
        self.assertIn("diagnostics", report)
        self.assertIn("version:", report)
        self.assertNotIn(token, report)

    def test_catalog_apply_switches_source_and_reloads_list(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.games import GameCatalog
        from ky_gameplayer.paths import app_root

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                try:
                    target = win._catalog_user_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        json.dumps([{"id": "1", "name": "Alpha"}, {"id": "2", "name": "Beta"}]),
                        encoding="utf-8",
                    )
                    win._apply_catalog(GameCatalog.load(target), target)
                    self.assertEqual(win._catalog_source, "user")
                    self.assertEqual(len(win.catalog.games), 2)
                    self.assertIn("2", win.count_label.text())
                    self.assertIn("Güncellendi", win.catalog_status.text())
                    self.assertTrue(win.btn_catalog_restore.isHidden())
                finally:
                    win.tasks.cancel_all()
                    win.hide()
                    win.deleteLater()
                    self.app.processEvents()
