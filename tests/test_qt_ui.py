"""Qt-level tests.

The default CI unit-test job intentionally does not install PySide6, so this
module skips there and runs in the dedicated ``ui`` job (offscreen).
"""

from __future__ import annotations

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
                self.assertEqual(win.tasks.pending, 0)
                win.hide()
                win.deleteLater()
                self.app.processEvents()
