from __future__ import annotations

import os


from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QSystemTrayIcon,
)

from ..autostart import set_enabled as set_autostart
from ..brand import APP_TITLE
from ..i18n import t as i18n


class TrayMixin:
    def _setup_tray(self) -> None:
        from PySide6.QtWidgets import QApplication, QMenu, QStyle

        from ..paths import resource

        icon_path = resource("assets/icon.png")
        icon = QIcon(str(icon_path)) if icon_path.exists() else self.style().standardIcon(
            QStyle.StandardPixmap.SP_ComputerIcon
        )
        self.setWindowIcon(icon)
        usable = QSystemTrayIcon.isSystemTrayAvailable()
        if not usable:
            QApplication.instance().setQuitOnLastWindowClosed(True)
            return
        tray_menu = QMenu()
        self._tray_show = QAction(i18n("tray_show"), self)
        self._tray_quit = QAction(i18n("tray_quit"), self)
        self._tray_show.triggered.connect(self._show_from_tray)
        self._tray_quit.triggered.connect(self._quit_app)
        tray_menu.addAction(self._tray_show)
        tray_menu.addAction(self._tray_quit)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setContextMenu(tray_menu)
        self._tray.setToolTip(APP_TITLE)
        self._tray.activated.connect(self._on_tray)
        self._tray.show()
        self._tray_usable = bool(self._tray.isVisible())
        if not self._tray_usable:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
            QApplication.instance().setQuitOnLastWindowClosed(True)
            return
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def _on_tray(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self) -> None:
        from PySide6.QtWidgets import QApplication

        self._force_quit = True
        if self._tray is not None:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
        self.close()
        QApplication.instance().quit()

    def _on_autostart(self, on: bool) -> None:
        from ..paths import app_root as live_root

        set_autostart(on, live_root() / "run.py")

    def closeEvent(self, event) -> None:
        from PySide6.QtWidgets import QApplication

        if self._tray_usable and self._tray is not None and self._tray.isVisible() and not self._force_quit:
            event.ignore()
            self.hide()
            self._tray.showMessage(APP_TITLE, i18n("tray_hidden"), QSystemTrayIcon.MessageIcon.Information, 1500)
            return
        if self._tray is not None:
            self._tray.hide()
            self._tray.deleteLater()
            self._tray = None
        if hasattr(self, "random_enabled") and self.random_enabled.isChecked():
            self.random_enabled.setChecked(False)
        if hasattr(self, "store"):
            settings = self.store.settings()
            settings["window_geometry"] = self.saveGeometry().toHex().data().decode()
            if hasattr(self, "splitter"):
                settings["splitter_sizes"] = [int(size) for size in self.splitter.sizes()]
        if hasattr(self, "_save_random_settings"):
            self._save_random_settings()
        if hasattr(self, "tasks"):
            self.tasks.cancel_all()
        self._want_connected = False
        self._cycle_timer.stop()
        self._detect_timer.stop()
        if hasattr(self, "_tick"):
            self._tick.stop()
        if hasattr(self, "_icon_timer"):
            self._icon_timer.stop()
        if hasattr(self, "_random_timer"):
            self._random_timer.stop()
        if hasattr(self, "_filter_timer"):
            self._filter_timer.stop()
        if hasattr(self, "science"):
            self.science.stop()
        if hasattr(self, "quest_engine"):
            self.quest_engine.stop()
        self._unpin_all()
        if self.ipc.connected:
            self.ipc.set_activity(self.pid.value() or os.getpid(), None)
        self.ipc.disconnect("exit")
        event.accept()
        super().closeEvent(event)
        QApplication.instance().quit()
