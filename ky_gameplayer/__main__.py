from __future__ import annotations

import logging
import os
import signal
import sys
from datetime import datetime

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false;qt.qpa.fonts=false")

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .brand import APP_NAME, APP_TITLE
from .instance import claim, wire
from .paths import app_root, log_dir
from .ui.theme import apply_theme
from .window import MainWindow


def _setup_logging() -> None:
    log_path = log_dir() / f"kodyazar-{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )

    def _hook(exc_type, exc, tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            app = QApplication.instance()
            if app is not None:
                app.quit()
            return
        logging.getLogger("kodyazar").exception("unhandled", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook


def main() -> int:
    _setup_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    if sys.platform == "darwin":
        try:
            from PySide6.QtGui import QGuiApplication as _Gui

            _Gui.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    app.setOrganizationName(APP_NAME)
    from .paths import resource

    icon = resource("assets/icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    app.setStyle("Fusion")
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 10))
    apply_theme(app)
    lock = claim(app)
    if lock is None:
        from .i18n import t

        QMessageBox.information(None, APP_TITLE, t("already_running"))
        return 0

    def _stop(*_args) -> None:
        app.quit()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _stop)
    wake = QTimer(app)
    wake.setInterval(200)
    wake.timeout.connect(lambda: None)
    wake.start()
    window = MainWindow(app_root())
    wire(lock, window._show_from_tray)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
