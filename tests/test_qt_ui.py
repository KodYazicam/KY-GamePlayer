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

    def test_markers_are_exposed_without_rebuild(self) -> None:
        from ky_gameplayer.games import Game
        from ky_gameplayer.model import GameListModel

        model = GameListModel()
        model.reset_games([Game(id="a", name="A"), Game(id="b", name="B")])
        model.set_markers({"a"}, {"b"}, {"b"})
        index = model.index(0)
        self.assertTrue(index.data(GameListModel.FavoriteRole))
        self.assertFalse(index.data(GameListModel.PlaylistRole))
        self.assertFalse(index.data(GameListModel.ExcludedRole))
        self.assertTrue(model.index(1).data(GameListModel.PlaylistRole))
        self.assertTrue(model.index(1).data(GameListModel.ExcludedRole))

    def test_delegate_paints_states_icons_and_markers(self) -> None:
        from PySide6.QtCore import QModelIndex, QRect, QSize
        from PySide6.QtGui import QColor, QPainter, QPixmap
        from PySide6.QtWidgets import QStyle, QStyleOptionViewItem

        from ky_gameplayer.games import Game
        from ky_gameplayer.model import GameDelegate, GameListModel

        model = GameListModel()
        model.reset_games(
            [
                Game(id="a", name="Alpha", themes=["Theme One"]),
                Game(id="b", name="A very long game name that needs eliding"),
            ]
        )
        model.set_markers({"a"}, {"a"}, {"a", "b"})
        delegate = GameDelegate()
        asked: list[object] = []
        delegate.icon_needed.connect(asked.append)
        option = QStyleOptionViewItem()
        option.rect = QRect(0, 0, 260, 60)
        option.font = self.app.font()
        canvas = QPixmap(260, 60)
        painter = QPainter(canvas)
        try:
            self.assertEqual(delegate.sizeHint(option, model.index(0)), QSize(260, 52))
            delegate.paint(painter, option, model.index(0))
            delegate.paint(painter, option, model.index(0))
            self.assertEqual(len(asked), 1)
            self.assertIs(asked[0], model.games()[0])

            option.state |= QStyle.StateFlag.State_Selected
            delegate.paint(painter, option, model.index(0))
            option.state = QStyle.StateFlag.State_MouseOver
            delegate.paint(painter, option, model.index(1))

            icon = QPixmap(32, 32)
            icon.fill(QColor("#336699"))
            model.set_icon("a", icon)
            delegate.paint(painter, option, model.index(0))
            delegate.paint(painter, option, QModelIndex())
        finally:
            painter.end()


@unittest.skipUnless(os.environ.get("KODYAZAR_UI_TESTS"), "set KODYAZAR_UI_TESTS=1 to build the window")
class WindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = _app()
        # Never let a UI smoke test inspect the developer's Discord install or
        # start a membership check against a real harvested token. Timers are
        # disabled and HOME/XDG point at an empty temporary directory.
        cls._tmp = tempfile.TemporaryDirectory()
        home = Path(cls._tmp.name)
        cls._env_patch = mock.patch.dict(
            os.environ,
            {
                "HOME": str(home),
                "USERPROFILE": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
                "XDG_CACHE_HOME": str(home / ".cache"),
                "APPDATA": str(home / "AppData" / "Roaming"),
                "LOCALAPPDATA": str(home / "AppData" / "Local"),
            },
        )
        cls._env_patch.start()
        from ky_gameplayer import window as window_module

        cls._membership_patch = mock.patch.object(
            window_module.MainWindow, "_enforce_membership", return_value=None
        )
        cls._scan_patch = mock.patch.object(window_module.MainWindow, "_scan_running", return_value=None)
        cls._ipc_patch = mock.patch.object(window_module, "find_discord_ipc", return_value=None)
        cls._membership_patch.start()
        cls._scan_patch.start()
        cls._ipc_patch.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._ipc_patch.stop()
        cls._scan_patch.stop()
        cls._membership_patch.stop()
        cls._env_patch.stop()
        cls._tmp.cleanup()

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

    def test_language_switch_retranslates_new_panels(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.i18n import set_lang
        from ky_gameplayer.paths import app_root

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                try:
                    win._lang = "en"
                    set_lang("en")
                    win._apply_language()
                    self.assertEqual(win.right_tabs.tabText(0), "Presence")
                    self.assertEqual(win.right_tabs.tabText(4), "Log")
                    self.assertEqual(win.scope_buttons["all"].text(), "All")
                    self.assertIn("Filters", win.btn_filters.text())
                    self.assertEqual(win.grp_identity.title(), "Basics")
                finally:
                    set_lang("tr")
                    win.tasks.cancel_all()
                    win.hide()
                    win.deleteLater()
                    self.app.processEvents()

    def test_games_panel_defaults_are_compact(self) -> None:
        from ky_gameplayer import window as window_module
        from ky_gameplayer.paths import app_root

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                mock.patch.object(window_module, "_config_dir", return_value=base / "cfg"),
                mock.patch.object(window_module, "_cache_dir", return_value=base / "cache"),
            ):
                win = window_module.MainWindow(app_root())
                try:
                    self.assertTrue(win.filter_drawer.isHidden())
                    self.assertTrue(win.details_panel.isHidden())
                    self.assertFalse(win.btn_details.isChecked())
                    self.assertEqual(win.right_tabs.count(), 5)
                    self.assertTrue(win.scope_buttons["all"].isChecked())

                    game = win.catalog.games[0]
                    win.store.toggle_favorite(game.id)
                    win._set_scope("favorites")
                    win._filter_timer.stop()
                    win._reload_list()
                    self.assertTrue(win.model.games())
                    self.assertTrue(all(g.id == game.id for g in win.model.games()))
                    self.assertTrue(win.model.index(0).data(win.model.FavoriteRole))

                    win._set_scope("all")
                    win.theme_filter.setCurrentIndex(1)
                    self.assertEqual(win._active_filter_count(), 1)
                    self.assertIn("Filtreler · 1", win.btn_filters.text())
                    win._clear_filters()
                    self.assertEqual(win._active_filter_count(), 0)

                    win._toggle_details(True)
                    self.assertFalse(win.details_panel.isHidden())
                    self.assertIn("Teknik", win.btn_details.text())
                finally:
                    win.tasks.cancel_all()
                    win.hide()
                    win.deleteLater()
                    self.app.processEvents()
