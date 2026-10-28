from __future__ import annotations

import time
from collections import deque
from pathlib import Path


from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QWidget,
)

from .detect import DetectedGame, ProcessIndex
from .games import Game, GameCatalog
from .images import ImageCache
from .ipc import DiscordIpc, find_discord_ipc
from .model import GameListModel
from .brand import APP_TITLE
from .i18n import t as i18n
from .paths import cache_dir as _cache_dir
from .paths import config_dir as _config_dir
from .profiles import ProfileStore
from .quest_engine import QuestEngine
from .science_worker import ScienceEngine

from .ui.common import ExtraSlot
from .ui.lock import LockMixin
from .ui.tray import TrayMixin
from .ui.language import LanguageMixin
from .ui.account import AccountMixin
from .ui.layout import LayoutMixin
from .ui.forms import FormsMixin
from .ui.games import GamesMixin
from .ui.presence import PresenceMixin
from .ui.profiles import ProfilesMixin
from .ui.science_ui import ScienceMixin
from .ui.tasks import TaskRunner
from .ui.theme import apply_theme


class MainWindow(LockMixin, TrayMixin, LanguageMixin, AccountMixin, LayoutMixin, FormsMixin, GamesMixin, PresenceMixin, ProfilesMixin, ScienceMixin, QWidget):
    membership_ready = Signal(object, object)

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = app_root
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(960, 640)
        self.resize(1320, 860)
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            avail = screen.availableGeometry()
            w = min(self.width(), max(960, avail.width() - 80))
            h = min(self.height(), max(640, avail.height() - 80))
            self.resize(w, h)
            self.move(
                avail.x() + (avail.width() - w) // 2,
                avail.y() + (avail.height() - h) // 2,
            )
        self._member_ok = False
        self._lang = "tr"
        self._preferred_client = None
        self._clients = []
        self._science_last_ids: list[str] = []
        self._log_records: list[tuple[str, str, dict]] = []
        self._force_quit = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_usable = False
        self._tray_show: QAction | None = None
        self._tray_quit: QAction | None = None
        from .paths import resource

        self.catalog = GameCatalog.load(resource("games.json"))
        self.store = ProfileStore(_config_dir() / "profiles.json")
        geometry = self.store.settings().get("window_geometry")
        if isinstance(geometry, str) and geometry:
            try:
                self.restoreGeometry(bytes.fromhex(geometry))
            except ValueError:
                pass
        self._lock_timeout = max(5, int(self.store.settings().get("lock_timeout") or 20))
        self._harvest_enabled = bool(self.store.settings().get("harvest_enabled", True))
        self.images = ImageCache(_cache_dir() / "cdn", self)
        self.science = ScienceEngine(_config_dir() / "science_state.json", self)
        self.quest_engine = QuestEngine(self)
        self.ipc = DiscordIpc()
        self.model = GameListModel()
        self._game: Game | None = None
        self._ready_user = ""
        self._icon_queue: list[Game] = []
        self._icon_requested: set[str] = set()
        self._pending_update = False
        self.extra_slots: list[ExtraSlot] = []
        self._extra_pids = set()
        self._want_connected = False
        self._reconnect_tries = 0
        self._last_activity_at = time.monotonic()
        self._random_history: deque[str] = deque(maxlen=12)
        self._cycle_index = 0
        self._detected: list[DetectedGame] = []
        self._detector = ProcessIndex(self.catalog)
        self._applying_cycle = False
        self._science_ran_slot = ""
        self._member_busy = False
        self._scan_busy = False
        self.tasks = TaskRunner(self)
        self._icon_timer = QTimer(self)
        self._icon_timer.setInterval(80)
        self._icon_timer.timeout.connect(self._pump_icons)
        self.membership_ready.connect(self._on_membership, Qt.ConnectionType.QueuedConnection)

        self.ipc.ready.connect(self._on_ready, Qt.ConnectionType.QueuedConnection)
        self.ipc.failed.connect(self._on_ipc_failed, Qt.ConnectionType.QueuedConnection)
        self.ipc.closed.connect(self._on_ipc_closed, Qt.ConnectionType.QueuedConnection)
        self.ipc.frame.connect(self._on_frame, Qt.ConnectionType.QueuedConnection)
        self.ipc.status.connect(self._set_socket_status, Qt.ConnectionType.QueuedConnection)
        self._style_hints = QGuiApplication.styleHints()
        self._style_hints.colorSchemeChanged.connect(self._on_system_scheme)
        self.science.progress.connect(self._on_science_progress, Qt.ConnectionType.QueuedConnection)
        self.science.finished.connect(self._on_science_finished, Qt.ConnectionType.QueuedConnection)
        self.science.failed.connect(self._on_science_failed, Qt.ConnectionType.QueuedConnection)
        self.science.status.connect(self._on_science_status, Qt.ConnectionType.QueuedConnection)
        self.science.state_changed.connect(self._refresh_science_status, Qt.ConnectionType.QueuedConnection)
        self.science.harvested.connect(self._on_science_harvested, Qt.ConnectionType.QueuedConnection)
        self.quest_engine.log.connect(self._on_quest_log, Qt.ConnectionType.QueuedConnection)
        self.quest_engine.failed.connect(self._on_quest_failed, Qt.ConnectionType.QueuedConnection)
        self.quest_engine.finished.connect(self._on_quest_finished, Qt.ConnectionType.QueuedConnection)
        self.quest_engine.house.connect(self._on_quest_house, Qt.ConnectionType.QueuedConnection)
        self.quest_engine.privacy.connect(self._on_quest_privacy, Qt.ConnectionType.QueuedConnection)

        self._build()
        self._apply_style()
        self._reload_list()
        last = self.store.last_game_id
        if last:
            self._select_game_id(last)
        self._refresh_profiles()
        QTimer.singleShot(0, self._update_preview)
        self._tick = QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start()
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(80)
        self._filter_timer.timeout.connect(self._reload_list)
        if self._icon_queue:
            self._icon_timer.start()
        self._random_timer = QTimer(self)
        self._random_timer.timeout.connect(self._random_switch)
        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self._cycle_step)
        self._detect_timer = QTimer(self)
        self._detect_timer.setInterval(5000)
        self._detect_timer.timeout.connect(self._scan_running)
        self._restore_extra_settings()
        self._bind_shortcuts()
        self._set_status(i18n("status_discord_off"))
        try:
            path = find_discord_ipc()
        except Exception:
            path = None
        if path:
            self._set_socket_status(i18n("socket_ready", path=path))
        self._log(key="log_loaded", n=len(self.catalog.games))
        QTimer.singleShot(800, self._scan_running)
        QTimer.singleShot(50, self._enforce_membership)

    def _apply_style(self) -> None:
        mode = str(self.store.settings().get("theme_mode") or "dark")
        app = QApplication.instance()
        apply_theme(app if app is not None else self, mode=mode)
        if hasattr(self, "list_view"):
            self.list_view.viewport().update()
        if hasattr(self, "preview"):
            self.preview.update()

    def _on_system_scheme(self, *_args) -> None:
        mode = str(self.store.settings().get("theme_mode") or "dark")
        if mode == "system":
            self._apply_style()
