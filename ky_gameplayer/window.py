from __future__ import annotations

import json
import os
import random
import time
from collections import deque
from pathlib import Path

from threading import Thread

from PySide6.QtCore import QDateTime, QObject, QTime, QTimer, QTimeZone, Qt, Signal, Slot
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QSystemTrayIcon,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from .activity import (
    ACTIVITY_FLAGS,
    ACTIVITY_TYPES,
    PARTY_PRIVACY,
    STATUS_DISPLAY_TYPES,
    ActivityConfig,
)
from .detect import DetectedGame, ProcessIndex
from .games import Game, GameCatalog
from .images import ImageCache
from .ipc import DiscordIpc, find_discord_ipc
from .model import GameDelegate, GameListModel
from .autostart import enabled as autostart_on
from .autostart import set_enabled as set_autostart
from .brand import APP_TITLE, GUILD_NAME, INVITE_URL
from .client_auth import harvest, list_running_clients
from .discord_rest import DiscordRest
from .i18n import set_lang, t as i18n
from .membership import check_membership
from .panel import Pages
from .paths import cache_dir as _cache_dir
from .paths import config_dir as _config_dir
from .preview import PresencePreview
from .processes import list_processes
from .profiles import ProfileStore
from .quest_engine import QuestEngine
from .science_worker import ScienceEngine
from .store import game_store_links, primary_store_button


MAX_EXTRA_SLOTS = 8


class ExtraSlot(QObject):
    changed = Signal()

    def __init__(self, game: Game, config: ActivityConfig, pid: int, parent=None) -> None:
        super().__init__(parent)
        self.game = game
        self.config = config
        self.pid = pid
        self.state = "connecting"
        self.ipc = DiscordIpc()
        self.ipc.ready.connect(self._on_ready, Qt.ConnectionType.QueuedConnection)
        self.ipc.failed.connect(self._on_failed, Qt.ConnectionType.QueuedConnection)
        self.ipc.closed.connect(self._on_closed, Qt.ConnectionType.QueuedConnection)
        self.ipc.frame.connect(self._on_frame, Qt.ConnectionType.QueuedConnection)

    @property
    def game_id(self) -> str:
        return self.game.id

    def start(self) -> None:
        self.state = "connecting"
        self.changed.emit()
        self.ipc.connect(self.game.id)

    def stop(self) -> None:
        if self.ipc.connected:
            self.ipc.set_activity(self.pid, None)
        self.ipc.disconnect("slot", emit=False)
        self.state = "closed"

    def _on_ready(self, _data: dict) -> None:
        activity = self.config.build()
        self.ipc.set_activity(self.pid, activity)
        self.state = "live"
        self.changed.emit()

    def _on_failed(self, message: str) -> None:
        self.state = f"error:{message}"
        self.changed.emit()

    def _on_closed(self, _reason: str) -> None:
        if self.state != "closed":
            self.state = "dropped"
            self.changed.emit()

    def _on_frame(self, payload: dict) -> None:
        if payload.get("evt") == "ERROR":
            data = payload.get("data") or {}
            message = data.get("message") if isinstance(data, dict) else data
            self.state = f"error:{message}"
            self.changed.emit()
        elif payload.get("cmd") == "SET_ACTIVITY":
            self.state = "live"
            self.changed.emit()


def _line(placeholder: str = "", maxlen: int = 0) -> QLineEdit:
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    if maxlen:
        edit.setMaxLength(maxlen)
    edit.setClearButtonEnabled(True)
    return edit


class MainWindow(QWidget):
    membership_ready = Signal(object, object)

    def __init__(self, app_root: Path) -> None:
        super().__init__()
        self.app_root = app_root
        self.setWindowTitle(APP_TITLE)
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
        self._icon_timer = QTimer(self)
        self._icon_timer.setInterval(80)
        self._icon_timer.timeout.connect(self._pump_icons)
        self.membership_ready.connect(self._on_membership, Qt.ConnectionType.QueuedConnection)

        self.ipc.ready.connect(self._on_ready, Qt.ConnectionType.QueuedConnection)
        self.ipc.failed.connect(self._on_ipc_failed, Qt.ConnectionType.QueuedConnection)
        self.ipc.closed.connect(self._on_ipc_closed, Qt.ConnectionType.QueuedConnection)
        self.ipc.frame.connect(self._on_frame, Qt.ConnectionType.QueuedConnection)
        self.ipc.status.connect(self._set_socket_status, Qt.ConnectionType.QueuedConnection)
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

    def _build(self) -> None:
        from PySide6.QtWidgets import QStackedWidget

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        self._lock_page = self._build_lock()
        app_page = QWidget()
        root = QVBoxLayout(app_page)
        root.setContentsMargins(10, 10, 10, 10)
        brand = QHBoxLayout()
        title = QLabel(APP_TITLE)
        title.setObjectName("sectionTitle")
        self.member_label = QLabel(i18n("member_checking"))
        self.member_label.setObjectName("muted")
        brand.addWidget(title)
        brand.addWidget(self.member_label, 1)
        self.client_box = QComboBox()
        self.client_box.setMinimumWidth(180)
        self.client_box.currentIndexChanged.connect(self._on_client_picked)
        self.lang_box = QComboBox()
        self.lang_box.addItem("TR", "tr")
        self.lang_box.addItem("EN", "en")
        self.lang_box.currentIndexChanged.connect(self._on_lang_changed)
        self.client_caption = QLabel(i18n("client"))
        brand.addWidget(self.client_caption)
        brand.addWidget(self.client_box)
        brand.addWidget(self.lang_box)
        self.autostart_box = QCheckBox(i18n("autostart"))
        self.autostart_box.setChecked(autostart_on())
        self.autostart_box.toggled.connect(self._on_autostart)
        brand.addWidget(self.autostart_box)
        root.addLayout(brand)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.pages = Pages(self.images, self)
        self.pages.house_chosen.connect(self._set_house)
        self.pages.house_leave.connect(self._leave_house)
        self.pages.privacy_chosen.connect(self._set_privacy)
        self.pages.quests_refresh.connect(self.quest_engine.refresh)
        self.pages.quests_start.connect(self._start_quests)
        self.pages.quests_stop.connect(self.quest_engine.stop)
        self.pages.status_apply.connect(self._apply_status)
        self.pages.clan_apply.connect(self._apply_clan)
        self.pages.account_refresh.connect(self._refresh_account)
        self.quest_engine.quests.connect(self.pages.set_quests)
        self.quest_engine.progress.connect(self.pages.update_quest)
        self.quest_engine.me.connect(self.pages.set_account)
        game = QWidget()
        game_layout = QHBoxLayout(game)
        game_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        game_layout.addWidget(splitter)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([420, 860])
        self.tabs.addTab(self.pages.house_page, i18n("tab_house"))
        self.tabs.addTab(self.pages.badge_page, i18n("tab_badges"))
        self.tabs.addTab(game, i18n("tab_games"))
        self.tabs.addTab(self.pages.privacy_page, i18n("tab_privacy"))
        self.tabs.addTab(self.pages.quest_page, i18n("tab_quests"))
        self.tabs.addTab(self.pages.account_page, i18n("tab_account"))
        self.tabs.addTab(self.pages.help_page, i18n("tab_help"))
        root.addWidget(self.tabs, 1)
        self._stack.addWidget(self._lock_page)
        self._stack.addWidget(app_page)
        outer.addWidget(self._stack)
        self._setup_tray()
        self._refresh_clients()

    def _build_lock(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel(APP_TITLE)
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_text = QLabel(i18n("lock_need", guild=GUILD_NAME, invite=INVITE_URL))
        self.lock_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_text.setWordWrap(True)
        self.lock_join = QPushButton(i18n("lock_join"))
        self.lock_retry = QPushButton(i18n("lock_retry"))
        self.lock_join.clicked.connect(self._open_invite)
        self.lock_retry.clicked.connect(self._enforce_membership)
        self.lock_token = QLineEdit()
        self.lock_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.lock_token.setPlaceholderText(i18n("lock_token_ph"))
        self.lock_cookie = QLineEdit()
        self.lock_cookie.setEchoMode(QLineEdit.EchoMode.Password)
        self.lock_cookie.setPlaceholderText(i18n("lock_cookie_ph"))
        self.lock_token_btn = QPushButton(i18n("lock_token_go"))
        self.lock_token_btn.clicked.connect(self._submit_lock_token)
        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(self.lock_text)
        layout.addWidget(self.lock_token)
        layout.addWidget(self.lock_cookie)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.lock_join)
        row.addWidget(self.lock_retry)
        row.addWidget(self.lock_token_btn)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        return page

    def _open_invite(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(INVITE_URL))

    def _submit_lock_token(self) -> None:
        from .client_auth import ClientAuth
        from .membership import Membership, check_membership

        raw = self.lock_token.text().strip().strip('"')
        cookie = self.lock_cookie.text().strip()
        if not raw:
            self.lock_text.setText(i18n("lock_token_ph"))
            return
        auth = ClientAuth(token=raw, cookie=cookie, client="paste")
        if not auth.cookie:
            from .client_auth import harvest_disk_extras

            harvest_disk_extras(auth)
        try:
            membership = check_membership(raw, auth.cookie)
        except Exception as exc:
            membership = Membership(ok=False, message=str(exc))
        self._on_membership(auth, membership)

    def _enforce_membership(self) -> None:
        if self._member_busy:
            return
        self._refresh_clients()
        self._member_busy = True
        preferred = self._preferred_client
        self.member_label.setText(i18n("member_checking"))
        self.lock_text.setText(i18n("member_checking"))
        QTimer.singleShot(20000, self._membership_timeout)

        def work() -> None:
            from .client_auth import ClientAuth
            from .membership import Membership

            auth = ClientAuth()
            try:
                auth = harvest(preferred, quick=True)
                membership = check_membership(auth.token, auth.cookie or "")
            except Exception as exc:
                membership = Membership(ok=False, message=f"{type(exc).__name__}: {exc}")
            self.membership_ready.emit(auth, membership)

        Thread(target=work, name="ky-membership", daemon=True).start()

    def _membership_timeout(self) -> None:
        if not self._member_busy:
            return
        self._member_busy = False
        self.lock_text.setText(i18n("lock_timeout"))
        self.member_label.setText(i18n("lock_timeout"))
        self._set_status(i18n("lock_timeout"))

    @Slot(object, object)
    def _on_membership(self, auth, membership) -> None:
        self._member_busy = False
        self._member_ok = bool(getattr(membership, "ok", False))
        self._log(f"üyelik ok={self._member_ok} {getattr(membership, 'username', '')} {getattr(membership, 'message', '')}")
        if not self._member_ok and auth is not None and not getattr(auth, "token", ""):
            self._stack.setCurrentIndex(0)
            self.lock_text.setText(i18n("lock_no_token"))
            self.member_label.setText(i18n("lock_no_token"))
            self._set_status(i18n("member_lock"))
            return
        if self._member_ok:
            self._stack.setCurrentIndex(1)
            who = membership.username or membership.user_id
            client = auth.client or "disk"
            self.member_label.setText(f"{who}  ·  {client}  ·  {GUILD_NAME}")
            if membership.me:
                self.pages.set_account(membership.me)
            self.science.preferred = self._preferred_client
            self.quest_engine.preferred = self._preferred_client
            self.science.apply_auth(auth)
            if not self.science.state.cookie:
                from .client_auth import harvest_disk_extras

                harvest_disk_extras(auth)
                self.science.apply_auth(auth)
            if hasattr(self, "science_token"):
                self.science_token.setText(self.science.state.token)
                self.science_cookie.setText(self.science.state.cookie)
                if auth.fingerprint:
                    self.science_fp.setText(self.science.state.fingerprint)
                self._refresh_science_status()
            self.quest_engine.refresh()
            self._refresh_account()
            self._set_status(i18n("member_ok", who=who))
            return
        self._stack.setCurrentIndex(0)
        self.lock_text.setText(membership.message or i18n("lock_not_member", guild=GUILD_NAME, invite=INVITE_URL))
        self._set_status(i18n("member_lock"))

    def _require_member(self) -> bool:
        if self._member_ok:
            return True
        if self._member_busy:
            self._set_status(i18n("member_checking"))
            return False
        self._enforce_membership()
        return False

    def _setup_tray(self) -> None:
        from PySide6.QtWidgets import QApplication, QMenu, QStyle

        from .paths import resource

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
        from .paths import app_root as live_root

        set_autostart(on, live_root() / "run.py")

    def _on_lang_changed(self, *_args) -> None:
        self._lang = str(self.lang_box.currentData() or "tr")
        set_lang(self._lang)
        self._save_random_settings()
        self._apply_language()

    def _retitle_combo(self, box: QComboBox, mapping: dict) -> None:
        current = box.currentData()
        box.blockSignals(True)
        for i in range(box.count()):
            data = box.itemData(i)
            if data in mapping:
                box.setItemText(i, mapping[data])
        box.blockSignals(False)
        if current is not None:
            idx = box.findData(current)
            if idx >= 0:
                box.setCurrentIndex(idx)

    def _form_label(self, widget, key: str) -> None:
        parent = widget.parent()
        layout = parent.layout() if parent is not None else None
        if isinstance(layout, QFormLayout):
            label = layout.labelForField(widget)
            if label is not None:
                label.setText(i18n(key))

    def _apply_language(self) -> None:
        set_lang(self._lang)
        tabs = (
            "tab_house",
            "tab_badges",
            "tab_games",
            "tab_privacy",
            "tab_quests",
            "tab_account",
            "tab_help",
        )
        for i, key in enumerate(tabs):
            if i < self.tabs.count():
                self.tabs.setTabText(i, i18n(key))
        self.member_label.setText(i18n("member_checking") if not self._member_ok else self.member_label.text())
        self.client_caption.setText(i18n("client"))
        self.autostart_box.setText(i18n("autostart"))
        self.lock_join.setText(i18n("lock_join"))
        self.lock_retry.setText(i18n("lock_retry"))
        if hasattr(self, "lock_token"):
            self.lock_token.setPlaceholderText(i18n("lock_token_ph"))
            self.lock_cookie.setPlaceholderText(i18n("lock_cookie_ph"))
            self.lock_token_btn.setText(i18n("lock_token_go"))
        if self._tray_show:
            self._tray_show.setText(i18n("tray_show"))
            self._tray_quit.setText(i18n("tray_quit"))
        self.games_title.setText(i18n("approved_games"))
        self.count_label.setText(i18n("games_count", n=len(self.catalog.games)))
        self.search.setPlaceholderText(i18n("search_ph"))
        self._retitle_combo(
            self.theme_filter,
            {"": i18n("filter_theme_all")},
        )
        self._retitle_combo(self.dist_filter, {"": i18n("filter_store_all")})
        self._retitle_combo(self.os_filter, {"": i18n("filter_os_all")})
        self._retitle_combo(
            self.icon_filter,
            {"all": i18n("filter_icon_all"), "yes": i18n("filter_icon_yes"), "no": i18n("filter_icon_no")},
        )
        self._retitle_combo(
            self.cover_filter,
            {"all": i18n("filter_cover_all"), "yes": i18n("filter_cover_yes"), "no": i18n("filter_cover_no")},
        )
        self._retitle_combo(
            self.overlay_filter,
            {"all": i18n("filter_overlay_all"), "yes": i18n("filter_overlay_yes"), "no": i18n("filter_overlay_no")},
        )
        self._retitle_combo(
            self.list_scope,
            {
                "all": i18n("scope_all"),
                "favorites": i18n("scope_favorites"),
                "recents": i18n("scope_recents"),
                "playlist": i18n("scope_playlist"),
                "excluded": i18n("scope_excluded"),
            },
        )
        self.btn_fav.setText(i18n("btn_fav"))
        self.btn_playlist.setText(i18n("btn_playlist"))
        self.btn_exclude.setText(i18n("btn_exclude"))
        if not self.ipc.connected:
            self.status_label.setText(i18n("status_offline"))
        self.btn_connect.setText(i18n("btn_connect"))
        self.btn_update.setText(i18n("btn_update"))
        self.btn_clear.setText(i18n("btn_clear"))
        self.btn_disconnect.setText(i18n("btn_disconnect"))
        self.btn_copy.setText(i18n("btn_copy"))
        self.btn_export.setText(i18n("btn_export"))
        self.btn_import.setText(i18n("btn_import"))
        self.profile_caption.setText(i18n("profile"))
        self.btn_profile_save.setText(i18n("profile_save"))
        self.btn_profile_load.setText(i18n("profile_load"))
        self.btn_profile_del.setText(i18n("profile_del"))
        self.random_enabled.setText(i18n("random_mode"))
        self.random_interval.setSuffix(i18n("suffix_sec"))
        self.random_interval.setToolTip(i18n("random_tip"))
        self.random_duration_label.setText(i18n("label_duration"))
        self._retitle_combo(
            self.random_source,
            {
                "filter": i18n("random_source_filter"),
                "all": i18n("random_source_all"),
                "favorites": i18n("random_source_fav"),
                "playlist": i18n("random_source_pl"),
            },
        )
        self.random_norepeat.setPrefix(i18n("norepeat_prefix"))
        self.random_norepeat.setToolTip(i18n("norepeat_tip"))
        self.weight_box.setPrefix(i18n("weight_prefix"))
        self.btn_random_now.setText(i18n("random_now"))
        self.extras_label.setText(i18n("extras"))
        self.extras_label.setToolTip(i18n("extras_tip"))
        self.btn_pin.setText(i18n("btn_pin"))
        self.btn_unpin.setText(i18n("btn_unpin"))
        self.btn_unpin_all.setText(i18n("btn_unpin_all"))
        self.detect_enabled.setText(i18n("detect_enabled"))
        self.detect_apply.setText(i18n("detect_apply"))
        self.detect_pid.setText(i18n("detect_pid"))
        self.btn_detect_now.setText(i18n("btn_scan"))
        self.btn_use_detect.setText(i18n("btn_use_detect"))
        self.grp_identity.setTitle(i18n("grp_identity"))
        self.app_id.setPlaceholderText(i18n("ph_app_id"))
        self.activity_name.setPlaceholderText(i18n("ph_activity_name"))
        self.stream_url.setPlaceholderText(i18n("ph_stream"))
        self.btn_pid_refresh.setText(i18n("btn_pid_refresh"))
        self.btn_pid_self.setText(i18n("btn_pid_self"))
        self.auto_assets.setText(i18n("auto_assets"))
        self._form_label(self.app_id, "row_app_id")
        self._form_label(self.activity_name, "row_activity_name")
        self._form_label(self.activity_type, "row_type")
        self._form_label(self.status_display, "row_status_display")
        self._form_label(self.stream_url, "row_stream")
        self.grp_text.setTitle(i18n("grp_text"))
        self.emoji_anim.setText(i18n("emoji_anim"))
        self.details.setPlaceholderText(i18n("ph_details"))
        self.details_url.setPlaceholderText(i18n("ph_details_url"))
        self.state.setPlaceholderText(i18n("ph_state"))
        self.state_url.setPlaceholderText(i18n("ph_state_url"))
        self._form_label(self.details, "row_details")
        self._form_label(self.details_url, "row_details_url")
        self._form_label(self.state, "row_state")
        self._form_label(self.state_url, "row_state_url")
        self.emoji_name.setPlaceholderText(i18n("ph_emoji_name"))
        self.emoji_id.setPlaceholderText(i18n("ph_emoji_id"))
        self._form_label(self.emoji_name, "row_emoji")
        self._form_label(self.emoji_id, "row_emoji_id")
        self.grp_assets.setTitle(i18n("grp_assets"))
        self.large_image.setPlaceholderText(i18n("ph_large_image"))
        self.large_text.setPlaceholderText(i18n("ph_large_text"))
        self.small_image.setPlaceholderText(i18n("ph_small_image"))
        self.small_text.setPlaceholderText(i18n("ph_small_text"))
        self._form_label(self.large_image, "row_large_image")
        self._form_label(self.large_text, "row_large_text")
        self._form_label(self.large_url, "row_large_url")
        self._form_label(self.small_image, "row_small_image")
        self._form_label(self.small_text, "row_small_text")
        self._form_label(self.small_url, "row_small_url")
        self.btn_asset_large.setText(i18n("btn_asset_large"))
        self.btn_asset_small.setText(i18n("btn_asset_small"))
        self.btn_asset_copy.setText(i18n("btn_asset_copy"))
        self._form_label(self.asset_preview, "row_preview")
        self.grp_time.setTitle(i18n("grp_time"))
        self.use_start.setText(i18n("use_start"))
        self.start_now.setText(i18n("btn_now"))
        self.btn_dur.setText(i18n("btn_end_from_dur"))
        self.use_end.setText(i18n("use_end"))
        self.duration.setSuffix(i18n("suffix_sec"))
        self._form_label(self.duration, "row_duration")
        self.grp_party.setTitle(i18n("grp_party"))
        self.use_party.setText(i18n("use_party"))
        self._retitle_combo(self.party_privacy, {-1: i18n("party_omit")})
        self._form_label(self.party_id, "row_party_id")
        self._form_label(self.party_privacy, "row_privacy")
        self.grp_buttons.setTitle(i18n("grp_buttons"))
        self.btn_store.setText(i18n("btn_store"))
        self.btn1_label.setPlaceholderText(i18n("ph_btn1"))
        self.btn2_label.setPlaceholderText(i18n("ph_btn2"))
        self._form_label(self.btn1_label, "row_btn1")
        self._form_label(self.btn1_url, "row_url1")
        self._form_label(self.btn2_label, "row_btn2")
        self._form_label(self.btn2_url, "row_url2")
        self.grp_secrets.setTitle(i18n("grp_secrets"))
        self.grp_flags.setTitle(i18n("grp_flags"))
        self.instance.setText(i18n("instance"))
        self.grp_cycle.setTitle(i18n("grp_cycle"))
        self.cycle_enabled.setText(i18n("cycle_enabled"))
        self.cycle_interval.setSuffix(i18n("suffix_sec"))
        self.cycle_lines.setPlaceholderText(i18n("cycle_ph"))
        self._form_label(self.cycle_interval, "label_duration")
        self._form_label(self.cycle_lines, "row_frames")
        self.grp_schedule.setTitle(i18n("grp_schedule"))
        self.schedule_enabled.setText(i18n("schedule_enabled"))
        self.idle_clear.setText(i18n("idle_clear"))
        self.idle_seconds.setSuffix(i18n("suffix_sec"))
        self.auto_reconnect.setText(i18n("auto_reconnect"))
        self._form_label(self.idle_clear, "row_idle")
        self.grp_science.setTitle(i18n("grp_science"))
        self.science_enabled.setText(i18n("science_enabled"))
        self.science_on_random.setText(i18n("science_on_random"))
        self.science_on_detect.setText(i18n("science_on_detect"))
        self.science_on_current.setText(i18n("science_on_current"))
        self._retitle_combo(
            self.science_mode,
            {"playtime": i18n("science_mode_hours"), "played": i18n("science_mode_played")},
        )
        self.science_hours.setSuffix(i18n("suffix_hours"))
        self.science_delay.setSuffix(i18n("suffix_sec"))
        self.science_target_hours.setSuffix(i18n("suffix_target"))
        self.science_target_hours.setToolTip(i18n("science_target_tip"))
        self._retitle_combo(
            self.science_source,
            {
                "current": i18n("science_source_current"),
                "filter": i18n("science_source_filter"),
                "favorites": i18n("science_source_fav"),
                "playlist": i18n("science_source_pl"),
                "all": i18n("science_source_all"),
                "missing": i18n("science_source_missing"),
            },
        )
        self.science_token.setPlaceholderText(i18n("ph_token"))
        self.science_cookie.setPlaceholderText(i18n("ph_cookie"))
        self.science_fp.setPlaceholderText(i18n("ph_fp"))
        self.btn_science_save.setText(i18n("btn_science_save"))
        self.btn_science_refresh.setText(i18n("btn_science_refresh"))
        self.btn_science_pull.setText(i18n("btn_science_pull"))
        self.btn_science_run.setText(i18n("btn_science_run"))
        self.btn_science_stop.setText(i18n("btn_science_stop"))
        self.btn_science_import.setText(i18n("btn_science_import"))
        self._form_label(self.science_mode, "row_mode")
        self._form_label(self.science_hours, "row_hours")
        self._form_label(self.science_source, "row_source")
        self._form_label(self.science_target_hours, "row_target")
        self._form_label(self.science_batch, "row_batch")
        self._form_label(self.science_delay, "row_delay")
        self._form_label(self.science_jitter, "row_jitter")
        self._form_label(self.science_token, "row_token")
        self._form_label(self.science_cookie, "row_cookie")
        self._form_label(self.science_fp, "row_fp")
        self._form_label(self.science_status, "row_status")
        self.grp_log.setTitle(i18n("grp_log"))
        self.btn_log_clear.setText(i18n("btn_log_clear"))
        self.pages.retranslate()
        self._refresh_clients()
        self._refresh_science_status()
        if self._game is not None:
            self._refresh_fav_buttons()
            self._fill_game_meta(self._game)
            self._fill_assets(self._game)
        self._refresh_extra_list()
        self._refresh_random_countdown()
        self._replay_logs()

    def _refresh_clients(self) -> None:
        if not hasattr(self, "client_box"):
            return
        try:
            self._clients = list_running_clients()
        except Exception:
            self._clients = []
        self.client_box.blockSignals(True)
        current = self.client_box.currentData()
        self.client_box.clear()
        self.client_box.addItem(i18n("client_auto"), None)
        for item in self._clients:
            self.client_box.addItem(f"{item.name}  pid {item.pid}", item.pid)
        if current is not None:
            idx = self.client_box.findData(current)
            if idx >= 0:
                self.client_box.setCurrentIndex(idx)
        self.client_box.blockSignals(False)
        self._on_client_picked()

    def _on_client_picked(self, *_args) -> None:
        pid = self.client_box.currentData() if hasattr(self, "client_box") else None
        self._preferred_client = None
        if pid is not None:
            for item in self._clients:
                if item.pid == pid:
                    self._preferred_client = item
                    break
        self.science.preferred = self._preferred_client
        self.quest_engine.preferred = self._preferred_client

    def _rest(self) -> DiscordRest:
        auth = harvest(self._preferred_client)
        return DiscordRest(auth.token, auth.cookie)

    def _refresh_account(self) -> None:
        if not self._member_ok:
            return
        rest = self._rest()
        st_me, me = rest.me()
        st_set, settings = rest.settings()
        st_ent, ents = rest.entitlements()
        if st_ent == 200 and isinstance(ents, dict):
            ents = ents.get("entitlements") or ents.get("items") or []
        st_g, guilds = rest.user_guilds()
        if st_g == 200 and isinstance(guilds, dict):
            guilds = guilds.get("guilds") or guilds.get("items") or []
        guild_list = guilds if isinstance(guilds, list) and st_g == 200 else []
        if st_me == 200 and isinstance(me, dict):
            self.pages.set_account_details(
                me,
                settings if st_set == 200 and isinstance(settings, dict) else None,
                ents if st_ent == 200 and isinstance(ents, list) else [],
                guild_list,
            )
            if st_g != 200:
                message = guilds.get("message") if isinstance(guilds, dict) else str(guilds)
                self._set_status(f"Sunucular [{st_g}] {message}")
            elif not guild_list:
                self._set_status(i18n("clan_none"))

    def _apply_status(self, text: str) -> None:
        if not self._require_member():
            return
        status, data = self._rest().set_custom_status(text)
        if status in (200, 204):
            self._set_status(i18n("status_custom"))
        else:
            message = data.get("message") if isinstance(data, dict) else str(data)
            self._set_status(f"Durum [{status}] {message}")

    def _apply_clan(self, guild_id: str) -> None:
        if not self._require_member():
            return
        status, data = self._rest().set_clan(guild_id or None, bool(guild_id))
        if status in (200, 204):
            self._set_status(i18n("status_clan"))
            self._refresh_account()
        else:
            message = data.get("message") if isinstance(data, dict) else str(data)
            self._set_status(f"Clan [{status}] {message}")

    def _start_quests(self) -> None:
        if not self._require_member():
            return
        self.quest_engine.start()

    def _set_house(self, house_id: int) -> None:
        if not self._require_member():
            return
        self.quest_engine.set_house(house_id)

    def _leave_house(self) -> None:
        if not self._require_member():
            return
        self.quest_engine.leave_house()

    def _set_privacy(self, level: int) -> None:
        if not self._require_member():
            return
        self.quest_engine.set_privacy(level)

    def _build_left(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        self.games_title = QLabel(i18n("approved_games"))
        self.games_title.setObjectName("sectionTitle")
        layout.addWidget(self.games_title)
        self.count_label = QLabel(i18n("games_count", n=len(self.catalog.games)))
        self.count_label.setObjectName("muted")
        layout.addWidget(self.count_label)

        self.search = _line(i18n("search_ph"))
        self.search.textChanged.connect(self._schedule_filter)
        self.search.setFocus()
        layout.addWidget(self.search)

        filters = QGridLayout()
        self.theme_filter = QComboBox()
        self.theme_filter.addItem(i18n("filter_theme_all"), "")
        for theme in self.catalog.themes:
            self.theme_filter.addItem(theme, theme)
        self.dist_filter = QComboBox()
        self.dist_filter.addItem(i18n("filter_store_all"), "")
        for dist in self.catalog.distributors:
            self.dist_filter.addItem(dist, dist)
        self.os_filter = QComboBox()
        self.os_filter.addItem(i18n("filter_os_all"), "")
        for os_name in ("linux", "win32", "darwin"):
            self.os_filter.addItem(os_name, os_name)
        self.icon_filter = QComboBox()
        self.icon_filter.addItem(i18n("filter_icon_all"), "all")
        self.icon_filter.addItem(i18n("filter_icon_yes"), "yes")
        self.icon_filter.addItem(i18n("filter_icon_no"), "no")
        self.cover_filter = QComboBox()
        self.cover_filter.addItem(i18n("filter_cover_all"), "all")
        self.cover_filter.addItem(i18n("filter_cover_yes"), "yes")
        self.cover_filter.addItem(i18n("filter_cover_no"), "no")
        self.overlay_filter = QComboBox()
        self.overlay_filter.addItem(i18n("filter_overlay_all"), "all")
        self.overlay_filter.addItem(i18n("filter_overlay_yes"), "yes")
        self.overlay_filter.addItem(i18n("filter_overlay_no"), "no")
        self.list_scope = QComboBox()
        self.list_scope.addItem(i18n("scope_all"), "all")
        self.list_scope.addItem(i18n("scope_favorites"), "favorites")
        self.list_scope.addItem(i18n("scope_recents"), "recents")
        self.list_scope.addItem(i18n("scope_playlist"), "playlist")
        self.list_scope.addItem(i18n("scope_excluded"), "excluded")
        for box in (
            self.theme_filter,
            self.dist_filter,
            self.os_filter,
            self.icon_filter,
            self.cover_filter,
            self.overlay_filter,
            self.list_scope,
        ):
            box.currentIndexChanged.connect(self._schedule_filter)
        filters.addWidget(self.theme_filter, 0, 0)
        filters.addWidget(self.dist_filter, 0, 1)
        filters.addWidget(self.os_filter, 1, 0)
        filters.addWidget(self.icon_filter, 1, 1)
        filters.addWidget(self.cover_filter, 2, 0)
        filters.addWidget(self.overlay_filter, 2, 1)
        filters.addWidget(self.list_scope, 3, 0, 1, 2)
        layout.addLayout(filters)

        fav_row = QHBoxLayout()
        self.btn_fav = QPushButton(i18n("btn_fav"))
        self.btn_playlist = QPushButton(i18n("btn_playlist"))
        self.btn_exclude = QPushButton(i18n("btn_exclude"))
        self.weight_box = QSpinBox()
        self.weight_box.setRange(1, 20)
        self.weight_box.setValue(1)
        self.weight_box.setPrefix(i18n("weight_prefix"))
        self.btn_fav.clicked.connect(self._toggle_favorite)
        self.btn_playlist.clicked.connect(self._toggle_playlist)
        self.btn_exclude.clicked.connect(self._toggle_excluded)
        self.weight_box.valueChanged.connect(self._on_weight_changed)
        fav_row.addWidget(self.btn_fav)
        fav_row.addWidget(self.btn_playlist)
        fav_row.addWidget(self.btn_exclude)
        fav_row.addWidget(self.weight_box)
        layout.addLayout(fav_row)

        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.delegate = GameDelegate(self.list_view)
        self.delegate.icon_needed.connect(self._queue_icon)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_view.selectionModel().currentChanged.connect(self._on_game_changed)
        layout.addWidget(self.list_view, 1)

        self.game_meta = QTextEdit()
        self.game_meta.setReadOnly(True)
        self.game_meta.setMaximumHeight(168)
        layout.addWidget(self.game_meta)
        return panel

    def _build_right(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusOff")
        self.status_label = QLabel(i18n("status_offline"))
        self.socket_label = QLabel("")
        self.socket_label.setObjectName("muted")
        top.addWidget(self.status_dot)
        top.addWidget(self.status_label, 1)
        top.addWidget(self.socket_label, 1)
        layout.addLayout(top)

        self.preview = PresencePreview()
        layout.addWidget(self.preview)

        actions = QHBoxLayout()
        self.btn_connect = QPushButton(i18n("btn_connect"))
        self.btn_update = QPushButton(i18n("btn_update"))
        self.btn_clear = QPushButton(i18n("btn_clear"))
        self.btn_disconnect = QPushButton(i18n("btn_disconnect"))
        self.btn_copy = QPushButton(i18n("btn_copy"))
        self.btn_export = QPushButton(i18n("btn_export"))
        self.btn_import = QPushButton(i18n("btn_import"))
        self.btn_connect.clicked.connect(lambda: self._connect())
        self.btn_update.clicked.connect(lambda: self._update_rpc())
        self.btn_clear.clicked.connect(self._clear_rpc)
        self.btn_disconnect.clicked.connect(self._disconnect)
        self.btn_copy.clicked.connect(self._copy_json)
        self.btn_export.clicked.connect(self._export_profiles)
        self.btn_import.clicked.connect(self._import_profiles)
        for btn in (
            self.btn_connect,
            self.btn_update,
            self.btn_clear,
            self.btn_disconnect,
            self.btn_copy,
            self.btn_export,
            self.btn_import,
        ):
            actions.addWidget(btn)
        layout.addLayout(actions)

        profiles = QHBoxLayout()
        self.profile_box = QComboBox()
        self.profile_box.setEditable(True)
        self.profile_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.btn_profile_save = QPushButton(i18n("profile_save"))
        self.btn_profile_load = QPushButton(i18n("profile_load"))
        self.btn_profile_del = QPushButton(i18n("profile_del"))
        self.btn_profile_save.clicked.connect(self._save_profile)
        self.btn_profile_load.clicked.connect(self._load_profile)
        self.btn_profile_del.clicked.connect(self._delete_profile)
        self.profile_caption = QLabel(i18n("profile"))
        profiles.addWidget(self.profile_box, 1)
        profiles.addWidget(self.btn_profile_save)
        profiles.addWidget(self.btn_profile_load)
        profiles.addWidget(self.btn_profile_del)
        layout.addLayout(profiles)

        random_row = QHBoxLayout()
        self.random_enabled = QCheckBox(i18n("random_mode"))
        self.random_interval = QSpinBox()
        self.random_interval.setRange(5, 86400)
        self.random_interval.setValue(60)
        self.random_interval.setSuffix(" sn")
        self.random_interval.setToolTip(i18n("random_tip"))
        self.random_source = QComboBox()
        self.random_source.addItem(i18n("random_source_filter"), "filter")
        self.random_source.addItem(i18n("random_source_all"), "all")
        self.random_source.addItem(i18n("random_source_fav"), "favorites")
        self.random_source.addItem(i18n("random_source_pl"), "playlist")
        self.random_norepeat = QSpinBox()
        self.random_norepeat.setRange(0, 50)
        self.random_norepeat.setValue(8)
        self.random_norepeat.setPrefix(i18n("norepeat_prefix"))
        self.random_norepeat.setToolTip("Son N oyunu tekrarlama")
        self.random_norepeat.valueChanged.connect(self._save_random_settings)
        self.btn_random_now = QPushButton(i18n("random_now"))
        self.random_countdown = QLabel("")
        self.random_countdown.setObjectName("muted")
        self.random_enabled.toggled.connect(self._on_random_toggled)
        self.random_interval.valueChanged.connect(self._on_random_interval_changed)
        self.random_source.currentIndexChanged.connect(self._save_random_settings)
        self.btn_random_now.clicked.connect(self._random_switch)
        random_row.addWidget(self.random_enabled)
        self.random_duration_label = QLabel(i18n("label_duration"))
        random_row.addWidget(self.random_duration_label)
        random_row.addWidget(self.random_interval)
        random_row.addWidget(self.random_source)
        random_row.addWidget(self.random_norepeat)
        random_row.addWidget(self.btn_random_now)
        random_row.addWidget(self.random_countdown, 1)
        layout.addLayout(random_row)

        extras = QHBoxLayout()
        extras_box = QVBoxLayout()
        self.extras_label = QLabel(i18n("extras"))
        self.extras_label.setToolTip(i18n("extras_tip"))
        extras_btns = QHBoxLayout()
        self.btn_pin = QPushButton(i18n("btn_pin"))
        self.btn_unpin = QPushButton(i18n("btn_unpin"))
        self.btn_unpin_all = QPushButton(i18n("btn_unpin_all"))
        self.btn_pin.clicked.connect(self._pin_current)
        self.btn_unpin.clicked.connect(self._unpin_selected)
        self.btn_unpin_all.clicked.connect(self._unpin_all)
        extras_btns.addWidget(self.btn_pin)
        extras_btns.addWidget(self.btn_unpin)
        extras_btns.addWidget(self.btn_unpin_all)
        extras_box.addWidget(self.extras_label)
        extras_box.addLayout(extras_btns)
        self.extra_list = QListWidget()
        self.extra_list.setMaximumHeight(92)
        extras.addLayout(extras_box, 1)
        extras.addWidget(self.extra_list, 2)
        layout.addLayout(extras)

        detect_row = QHBoxLayout()
        self.detect_enabled = QCheckBox(i18n("detect_enabled"))
        self.detect_apply = QCheckBox(i18n("detect_apply"))
        self.detect_pid = QCheckBox(i18n("detect_pid"))
        self.detect_pid.setChecked(True)
        self.btn_detect_now = QPushButton(i18n("btn_scan"))
        self.detect_box = QComboBox()
        self.detect_box.setMinimumWidth(220)
        self.btn_use_detect = QPushButton(i18n("btn_use_detect"))
        self.detect_enabled.toggled.connect(self._on_detect_toggled)
        self.btn_detect_now.clicked.connect(self._scan_running)
        self.btn_use_detect.clicked.connect(self._use_detected)
        detect_row.addWidget(self.detect_enabled)
        detect_row.addWidget(self.detect_apply)
        detect_row.addWidget(self.detect_pid)
        detect_row.addWidget(self.btn_detect_now)
        detect_row.addWidget(self.detect_box, 1)
        detect_row.addWidget(self.btn_use_detect)
        layout.addLayout(detect_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_host = QWidget()
        form = QVBoxLayout(form_host)
        form.addWidget(self._identity_group())
        form.addWidget(self._text_group())
        form.addWidget(self._assets_group())
        form.addWidget(self._time_group())
        form.addWidget(self._party_group())
        form.addWidget(self._buttons_group())
        form.addWidget(self._secrets_group())
        form.addWidget(self._flags_group())
        form.addWidget(self._cycle_group())
        form.addWidget(self._schedule_group())
        form.addWidget(self._science_group())
        form.addWidget(self._log_group())
        form.addStretch(1)
        scroll.setWidget(form_host)
        layout.addWidget(scroll, 1)
        return panel

    def _identity_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_identity"))
        self.grp_identity = box
        grid = QFormLayout(box)
        self.app_id = _line("Application ID")
        self.activity_name = _line(i18n("ph_activity_name"), 128)
        self.activity_type = QComboBox()
        for value, label in ACTIVITY_TYPES:
            self.activity_type.addItem(f"{label} ({value})", value)
        self.status_display = QComboBox()
        for value, label in STATUS_DISPLAY_TYPES:
            self.status_display.addItem(f"{label} ({value})", value)
        self.stream_url = _line("Twitch/YouTube URL (Streaming)", 512)
        self.pid = QSpinBox()
        self.pid.setRange(1, 2_147_483_647)
        self.pid.setValue(max(1, os.getpid() % 2_147_483_647))
        self.pid_box = QComboBox()
        self.pid_box.setEditable(False)
        self.btn_pid_refresh = QPushButton(i18n("btn_pid_refresh"))
        self.btn_pid_self = QPushButton(i18n("btn_pid_self"))
        self.btn_pid_refresh.clicked.connect(self._refresh_pid_list)
        self.btn_pid_self.clicked.connect(self._use_self_pid)
        self.pid_box.currentIndexChanged.connect(self._on_pid_picked)
        self.auto_assets = QCheckBox(i18n("auto_assets"))
        self.auto_assets.setChecked(True)
        for widget in (
            self.app_id,
            self.activity_name,
            self.activity_type,
            self.status_display,
            self.stream_url,
            self.pid,
            self.auto_assets,
        ):
            self._watch(widget)
        self.app_id.editingFinished.connect(self._on_app_id_entered)
        grid.addRow(i18n("row_app_id"), self.app_id)
        grid.addRow(i18n("row_activity_name"), self.activity_name)
        grid.addRow(i18n("row_type"), self.activity_type)
        grid.addRow(i18n("row_status_display"), self.status_display)
        grid.addRow(i18n("row_stream"), self.stream_url)
        pid_row = QHBoxLayout()
        pid_row.addWidget(self.pid)
        pid_row.addWidget(self.pid_box, 1)
        pid_row.addWidget(self.btn_pid_refresh)
        pid_row.addWidget(self.btn_pid_self)
        grid.addRow("PID", pid_row)
        grid.addRow("", self.auto_assets)
        return box

    def _text_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_text"))
        self.grp_text = box
        grid = QFormLayout(box)
        self.details = _line(i18n("ph_details"), 128)
        self.details_url = _line(i18n("ph_details_url"), 256)
        self.state = _line(i18n("ph_state"), 128)
        self.state_url = _line(i18n("ph_state_url"), 256)
        self.emoji_name = _line(i18n("ph_emoji_name"), 32)
        self.emoji_id = _line(i18n("ph_emoji_id"), 32)
        self.emoji_anim = QCheckBox("Animated emoji")
        for widget in (
            self.details,
            self.details_url,
            self.state,
            self.state_url,
            self.emoji_name,
            self.emoji_id,
            self.emoji_anim,
        ):
            self._watch(widget)
        grid.addRow(i18n("row_details"), self.details)
        grid.addRow(i18n("row_details_url"), self.details_url)
        grid.addRow(i18n("row_state"), self.state)
        grid.addRow(i18n("row_state_url"), self.state_url)
        grid.addRow(i18n("row_emoji"), self.emoji_name)
        grid.addRow(i18n("row_emoji_id"), self.emoji_id)
        grid.addRow("", self.emoji_anim)
        return box

    def _assets_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_assets"))
        self.grp_assets = box
        grid = QFormLayout(box)
        self.large_image = _line(i18n("ph_large_image"), 256)
        self.large_text = _line(i18n("ph_large_text"), 128)
        self.large_url = _line("large_url", 256)
        self.small_image = _line(i18n("ph_small_image"), 256)
        self.small_text = _line(i18n("ph_small_text"), 128)
        self.small_url = _line("small_url", 256)
        for widget in (
            self.large_image,
            self.large_text,
            self.large_url,
            self.small_image,
            self.small_text,
            self.small_url,
        ):
            self._watch(widget)
        grid.addRow(i18n("row_large_image"), self.large_image)
        grid.addRow(i18n("row_large_text"), self.large_text)
        grid.addRow(i18n("row_large_url"), self.large_url)
        grid.addRow(i18n("row_small_image"), self.small_image)
        grid.addRow(i18n("row_small_text"), self.small_text)
        grid.addRow(i18n("row_small_url"), self.small_url)
        self.asset_preview = QLabel(i18n("asset_none"))
        self.asset_preview.setMinimumHeight(72)
        self.asset_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.asset_preview.setStyleSheet("background:#111214; border-radius:8px;")
        self.asset_box = QComboBox()
        self.btn_asset_large = QPushButton(i18n("btn_asset_large"))
        self.btn_asset_small = QPushButton(i18n("btn_asset_small"))
        self.btn_asset_copy = QPushButton(i18n("btn_asset_copy"))
        self.asset_box.currentIndexChanged.connect(self._on_asset_picked)
        self.btn_asset_large.clicked.connect(lambda: self._apply_asset("large"))
        self.btn_asset_small.clicked.connect(lambda: self._apply_asset("small"))
        self.btn_asset_copy.clicked.connect(self._copy_asset_url)
        asset_row = QHBoxLayout()
        asset_row.addWidget(self.asset_box, 1)
        asset_row.addWidget(self.btn_asset_large)
        asset_row.addWidget(self.btn_asset_small)
        asset_row.addWidget(self.btn_asset_copy)
        grid.addRow(i18n("row_assets"), asset_row)
        grid.addRow(i18n("row_preview"), self.asset_preview)
        return box

    def _time_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_time"))
        self.grp_time = box
        grid = QFormLayout(box)
        self.use_start = QCheckBox("Start timestamp")
        self.use_start.setChecked(True)
        self.start_now = QPushButton(i18n("btn_now"))
        self.start_dt = QDateTimeEdit()
        self.start_dt.setCalendarPopup(True)
        self.start_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_dt.setDateTime(QDateTime.currentDateTime())
        self.use_end = QCheckBox("End timestamp")
        self.end_dt = QDateTimeEdit()
        self.end_dt.setCalendarPopup(True)
        self.end_dt.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_dt.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.duration = QSpinBox()
        self.duration.setRange(0, 86400 * 7)
        self.duration.setSuffix(" sn")
        self.duration.setValue(0)
        self.btn_dur = QPushButton(i18n("btn_end_from_dur"))
        self.btn_dur.clicked.connect(self._apply_duration)
        self.start_now.clicked.connect(self._stamp_now)
        for widget in (
            self.use_start,
            self.start_dt,
            self.use_end,
            self.end_dt,
            self.duration,
        ):
            self._watch(widget)
        start_row = QHBoxLayout()
        start_row.addWidget(self.start_dt, 1)
        start_row.addWidget(self.start_now)
        end_row = QHBoxLayout()
        end_row.addWidget(self.end_dt, 1)
        end_row.addWidget(self.btn_dur)
        grid.addRow(self.use_start, start_row)
        grid.addRow(self.use_end, end_row)
        grid.addRow(i18n("row_duration"), self.duration)
        return box

    def _party_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_party"))
        self.grp_party = box
        grid = QFormLayout(box)
        self.party_id = _line("party id", 128)
        self.use_party = QCheckBox(i18n("use_party"))
        self.party_size = QSpinBox()
        self.party_size.setRange(1, 10000)
        self.party_max = QSpinBox()
        self.party_max.setRange(1, 10000)
        self.party_max.setValue(5)
        self.party_privacy = QComboBox()
        self.party_privacy.addItem(i18n("party_omit"), -1)
        for value, label in PARTY_PRIVACY:
            self.party_privacy.addItem(f"{label} ({value})", value)
        size_row = QHBoxLayout()
        size_row.addWidget(self.party_size)
        size_row.addWidget(QLabel("/"))
        size_row.addWidget(self.party_max)
        for widget in (
            self.party_id,
            self.use_party,
            self.party_size,
            self.party_max,
            self.party_privacy,
        ):
            self._watch(widget)
        grid.addRow(i18n("row_party_id"), self.party_id)
        grid.addRow("", self.use_party)
        grid.addRow("Size", size_row)
        grid.addRow(i18n("row_privacy"), self.party_privacy)
        return box

    def _buttons_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_buttons"))
        self.grp_buttons = box
        grid = QFormLayout(box)
        self.btn1_label = _line(i18n("ph_btn1"), 32)
        self.btn1_url = _line("https://", 512)
        self.btn2_label = _line(i18n("ph_btn2"), 32)
        self.btn2_url = _line("https://", 512)
        for widget in (self.btn1_label, self.btn1_url, self.btn2_label, self.btn2_url):
            self._watch(widget)
        store_row = QHBoxLayout()
        self.btn_store = QPushButton(i18n("btn_store"))
        self.btn_store.clicked.connect(self._fill_store_button)
        store_row.addWidget(self.btn_store)
        store_row.addStretch(1)
        grid.addRow(i18n("row_btn1"), self.btn1_label)
        grid.addRow(i18n("row_url1"), self.btn1_url)
        grid.addRow(i18n("row_btn2"), self.btn2_label)
        grid.addRow(i18n("row_url2"), self.btn2_url)
        grid.addRow("", store_row)
        return box

    def _secrets_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_secrets"))
        self.grp_secrets = box
        grid = QFormLayout(box)
        self.join_secret = _line("join secret", 128)
        self.spectate_secret = _line("spectate secret", 128)
        self.match_secret = _line("match secret", 128)
        for widget in (self.join_secret, self.spectate_secret, self.match_secret):
            self._watch(widget)
        grid.addRow("Join", self.join_secret)
        grid.addRow("Spectate", self.spectate_secret)
        grid.addRow("Match", self.match_secret)
        return box

    def _flags_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_flags"))
        self.grp_flags = box
        layout = QVBoxLayout(box)
        self.instance = QCheckBox("instance")
        self.instance.setChecked(True)
        self._watch(self.instance)
        layout.addWidget(self.instance)
        grid = QGridLayout()
        self.flag_boxes: list[tuple[int, QCheckBox]] = []
        for i, (bit, name) in enumerate(ACTIVITY_FLAGS):
            cb = QCheckBox(f"{name} ({bit})")
            self._watch(cb)
            self.flag_boxes.append((bit, cb))
            grid.addWidget(cb, i // 2, i % 2)
        layout.addLayout(grid)
        return box

    def _cycle_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_cycle"))
        self.grp_cycle = box
        grid = QFormLayout(box)
        self.cycle_enabled = QCheckBox(i18n("cycle_enabled"))
        self.cycle_interval = QSpinBox()
        self.cycle_interval.setRange(5, 3600)
        self.cycle_interval.setValue(20)
        self.cycle_interval.setSuffix(" sn")
        self.cycle_lines = QTextEdit()
        self.cycle_lines.setPlaceholderText(i18n("cycle_ph"))
        self.cycle_lines.setMaximumHeight(90)
        self.cycle_enabled.toggled.connect(self._on_cycle_toggled)
        self.cycle_interval.valueChanged.connect(self._restart_cycle_timer)
        grid.addRow("", self.cycle_enabled)
        grid.addRow(i18n("label_duration"), self.cycle_interval)
        grid.addRow(i18n("row_frames"), self.cycle_lines)
        return box

    def _schedule_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_schedule"))
        self.grp_schedule = box
        grid = QFormLayout(box)
        self.schedule_enabled = QCheckBox(i18n("schedule_enabled"))
        self.schedule_start = QTimeEdit()
        self.schedule_start.setDisplayFormat("HH:mm")
        self.schedule_start.setTime(QTime(9, 0))
        self.schedule_end = QTimeEdit()
        self.schedule_end.setDisplayFormat("HH:mm")
        self.schedule_end.setTime(QTime(23, 0))
        self.idle_clear = QCheckBox(i18n("idle_clear"))
        self.idle_seconds = QSpinBox()
        self.idle_seconds.setRange(30, 86400)
        self.idle_seconds.setValue(1800)
        self.idle_seconds.setSuffix(" sn")
        self.auto_reconnect = QCheckBox(i18n("auto_reconnect"))
        self.auto_reconnect.setChecked(True)
        self.schedule_enabled.toggled.connect(self._save_random_settings)
        self.idle_clear.toggled.connect(self._save_random_settings)
        self.auto_reconnect.toggled.connect(self._save_random_settings)
        range_row = QHBoxLayout()
        range_row.addWidget(self.schedule_start)
        range_row.addWidget(QLabel("→"))
        range_row.addWidget(self.schedule_end)
        idle_row = QHBoxLayout()
        idle_row.addWidget(self.idle_clear)
        idle_row.addWidget(self.idle_seconds)
        grid.addRow("", self.schedule_enabled)
        grid.addRow(i18n("row_range"), range_row)
        grid.addRow(i18n("row_idle"), idle_row)
        grid.addRow("", self.auto_reconnect)
        return box

    def _science_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_science"))
        self.grp_science = box
        grid = QFormLayout(box)
        self.science_enabled = QCheckBox(i18n("science_enabled"))
        self.science_on_random = QCheckBox(i18n("science_on_random"))
        self.science_on_random.setChecked(True)
        self.science_on_detect = QCheckBox(i18n("science_on_detect"))
        self.science_on_current = QCheckBox(i18n("science_on_current"))
        self.science_on_current.setChecked(True)
        self.science_mode = QComboBox()
        self.science_mode.addItem(i18n("science_mode_hours"), "playtime")
        self.science_mode.addItem(i18n("science_mode_played"), "played")
        self.science_hours = QDoubleSpinBox()
        self.science_hours.setRange(0.01, 24.0)
        self.science_hours.setDecimals(2)
        self.science_hours.setSingleStep(0.25)
        self.science_hours.setValue(2.0)
        self.science_hours.setSuffix(" saat")
        self.science_batch = QSpinBox()
        self.science_batch.setRange(1, 200)
        self.science_batch.setValue(20)
        self.science_delay = QDoubleSpinBox()
        self.science_delay.setRange(0.0, 10.0)
        self.science_delay.setDecimals(2)
        self.science_delay.setValue(0.8)
        self.science_delay.setSuffix(" sn")
        self.science_jitter = QDoubleSpinBox()
        self.science_jitter.setRange(0.0, 0.5)
        self.science_jitter.setDecimals(2)
        self.science_jitter.setSingleStep(0.01)
        self.science_jitter.setValue(0.05)
        self.science_source = QComboBox()
        self.science_source.addItem(i18n("science_source_current"), "current")
        self.science_source.addItem(i18n("science_source_filter"), "filter")
        self.science_source.addItem(i18n("science_source_fav"), "favorites")
        self.science_source.addItem(i18n("science_source_pl"), "playlist")
        self.science_source.addItem(i18n("science_source_all"), "all")
        self.science_source.addItem(i18n("science_source_missing"), "missing")
        self.science_target_hours = QDoubleSpinBox()
        self.science_target_hours.setRange(0.0, 500.0)
        self.science_target_hours.setDecimals(1)
        self.science_target_hours.setValue(0.0)
        self.science_target_hours.setSuffix(" saat hedef")
        self.science_target_hours.setToolTip(i18n("science_target_tip"))
        self.science_token = QLineEdit()
        self.science_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.science_token.setPlaceholderText("authorization")
        self.science_cookie = QLineEdit()
        self.science_cookie.setEchoMode(QLineEdit.EchoMode.Password)
        self.science_cookie.setPlaceholderText("cookie")
        self.science_fp = QLineEdit()
        self.science_fp.setPlaceholderText(i18n("ph_fp"))
        self.science_status = QLabel("")
        self.science_status.setObjectName("muted")
        self.science_status.setWordWrap(True)
        self.btn_science_save = QPushButton(i18n("btn_science_save"))
        self.btn_science_refresh = QPushButton(i18n("btn_science_refresh"))
        self.btn_science_pull = QPushButton(i18n("btn_science_pull"))
        self.btn_science_run = QPushButton(i18n("btn_science_run"))
        self.btn_science_stop = QPushButton(i18n("btn_science_stop"))
        self.btn_science_import = QPushButton(i18n("btn_science_import"))
        self.btn_science_save.clicked.connect(self._save_science_credentials)
        self.btn_science_refresh.clicked.connect(self.science.refresh_analytics)
        self.btn_science_pull.clicked.connect(self._pull_science_from_client)
        self.btn_science_run.clicked.connect(lambda: self._run_science(reason="manual"))
        self.btn_science_stop.clicked.connect(self.science.stop)
        self.btn_science_import.clicked.connect(self._import_science_state)
        for widget in (
            self.science_enabled,
            self.science_on_random,
            self.science_on_detect,
            self.science_on_current,
            self.science_mode,
            self.science_hours,
            self.science_batch,
            self.science_delay,
            self.science_jitter,
            self.science_source,
            self.science_target_hours,
        ):
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(self._save_random_settings)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self._save_random_settings)
            else:
                widget.valueChanged.connect(self._save_random_settings)
        flags = QHBoxLayout()
        flags.addWidget(self.science_enabled)
        flags.addWidget(self.science_on_random)
        flags.addWidget(self.science_on_detect)
        flags.addWidget(self.science_on_current)
        creds = QHBoxLayout()
        creds.addWidget(self.btn_science_pull)
        creds.addWidget(self.btn_science_save)
        creds.addWidget(self.btn_science_refresh)
        creds.addWidget(self.btn_science_import)
        run_row = QHBoxLayout()
        run_row.addWidget(self.btn_science_run)
        run_row.addWidget(self.btn_science_stop)
        grid.addRow("", flags)
        grid.addRow(i18n("row_mode"), self.science_mode)
        grid.addRow(i18n("row_hours"), self.science_hours)
        grid.addRow(i18n("row_source"), self.science_source)
        grid.addRow(i18n("row_target"), self.science_target_hours)
        grid.addRow(i18n("row_batch"), self.science_batch)
        grid.addRow(i18n("row_delay"), self.science_delay)
        grid.addRow(i18n("row_jitter"), self.science_jitter)
        grid.addRow(i18n("row_token"), self.science_token)
        grid.addRow(i18n("row_cookie"), self.science_cookie)
        grid.addRow(i18n("row_fp"), self.science_fp)
        grid.addRow("", creds)
        grid.addRow("", run_row)
        grid.addRow(i18n("row_status"), self.science_status)
        return box

    def _log_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_log"))
        self.grp_log = box
        layout = QVBoxLayout(box)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        self.btn_log_clear = QPushButton(i18n("btn_log_clear"))
        self.btn_log_clear.clicked.connect(self._clear_log)
        layout.addWidget(self.log_view)
        layout.addWidget(self.btn_log_clear, alignment=Qt.AlignmentFlag.AlignRight)
        return box

    def _watch(self, widget) -> None:
        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._update_preview)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._update_preview)
        elif isinstance(widget, QSpinBox):
            widget.valueChanged.connect(self._update_preview)
        elif isinstance(widget, QCheckBox):
            widget.toggled.connect(self._update_preview)
        elif isinstance(widget, QDateTimeEdit):
            widget.dateTimeChanged.connect(self._update_preview)

    def _schedule_filter(self) -> None:
        self._filter_timer.start()

    def _filter_bool(self, combo: QComboBox) -> bool | None:
        value = combo.currentData()
        if value == "yes":
            return True
        if value == "no":
            return False
        return None

    def _reload_list(self) -> None:
        current_id = self._game.id if self._game else None
        games = self.catalog.filter(
            query=self.search.text(),
            theme=self.theme_filter.currentData() or None,
            distributor=self.dist_filter.currentData() or None,
            os_name=self.os_filter.currentData() or None,
            has_icon=self._filter_bool(self.icon_filter),
            has_cover=self._filter_bool(self.cover_filter),
            overlay=self._filter_bool(self.overlay_filter),
        )
        scope = self.list_scope.currentData()
        if scope == "favorites":
            allow = set(self.store.favorites())
            games = [game for game in games if game.id in allow]
        elif scope == "recents":
            order = {game_id: i for i, game_id in enumerate(self.store.recents())}
            games = [game for game in games if game.id in order]
            games.sort(key=lambda game: order.get(game.id, 999))
        elif scope == "playlist":
            allow = set(self.store.playlist())
            games = [game for game in games if game.id in allow]
        elif scope == "excluded":
            allow = set(self.store.excluded())
            games = [game for game in games if game.id in allow]
        self.model.reset_games(games)
        self.count_label.setText(i18n("games_count_filter", shown=len(games), n=len(self.catalog.games)))
        if current_id:
            row = self.model.index_for_id(current_id)
            if row >= 0:
                self.list_view.setCurrentIndex(self.model.index(row))

    def _select_game_id(self, game_id: str) -> None:
        row = self.model.index_for_id(game_id)
        if row >= 0:
            self.list_view.setCurrentIndex(self.model.index(row))
            self.list_view.scrollTo(self.model.index(row))
            return
        game = self.catalog.get(game_id)
        if game is not None:
            self._apply_game(game)

    def _on_app_id_entered(self) -> None:
        game_id = self.app_id.text().strip()
        if not game_id:
            return
        game = self.catalog.get(game_id)
        if game is None:
            self._game = None
            self.game_meta.setPlainText(i18n("custom_app", id=game_id))
            self._update_preview()
            return
        if self._game and self._game.id == game_id:
            return
        self._select_game_id(game_id)

    def _on_game_changed(self, current, _previous) -> None:
        game = self.model.game_at(current.row())
        if game is not None:
            self._apply_game(game)

    def _apply_game(self, game: Game) -> None:
        same = self._game is not None and self._game.id == game.id
        self._game = game
        if same:
            self._update_preview()
            return
        self.app_id.setText(game.id)
        self.activity_name.setText(game.name)
        if self.auto_assets.isChecked():
            image = game.cover_image_hash or game.icon_hash or ""
            small = ""
            if game.cover_image_hash and game.icon_hash and game.icon_hash != game.cover_image_hash:
                small = game.icon_hash
            self.large_image.setText(image)
            self.large_text.setText(game.name)
            self.small_image.setText(small)
        self.store.last_game_id = game.id
        self.store.add_recent(game.id)
        self._fill_game_meta(game)
        self._fill_assets(game)
        self._refresh_fav_buttons()
        self._update_preview()
        self._queue_icon(game)

    def _fill_game_meta(self, game: Game) -> None:
        lines = [
            f"{game.name}",
            f"ID: {game.id}",
        ]
        if game.aliases:
            lines.append("Alias: " + ", ".join(game.aliases[:12]))
        if game.themes:
            lines.append(i18n("theme") + ": " + ", ".join(game.themes))
        lines.append(
            f"hook={game.hook} overlay={game.overlay} "
            f"compat_hook={game.overlay_compatibility_hook} "
            f"methods={game.overlay_methods} warn={game.overlay_warn}"
        )
        if game.executables:
            exe = ", ".join(
                f"{e.get('name')} ({e.get('os')}"
                + (" launcher" if e.get("is_launcher") else "")
                + ")"
                for e in game.executables[:12]
            )
            lines.append("Exe: " + exe)
        if game.third_party_skus:
            skus = ", ".join(
                f"{s.get('distributor')}:{s.get('id')}"
                for s in game.third_party_skus[:16]
                if s.get("distributor")
            )
            lines.append("SKU: " + skus)
        cc = game.content_classification or {}
        ratings = (cc.get("agency_ratings") or {}) if isinstance(cc, dict) else {}
        if ratings:
            bits = []
            for agency, payload in ratings.items():
                if isinstance(payload, dict):
                    bits.append(f"{agency}={payload.get('rating')}")
            if bits:
                lines.append("Rating: " + ", ".join(bits))
        classes = cc.get("discord_classifications") if isinstance(cc, dict) else None
        if classes:
            lines.append("Discord class: " + ", ".join(str(x) for x in classes))
        links = game_store_links(game)
        if links:
            lines.append(i18n("store") + ": " + ", ".join(f"{dist}:{url}" for dist, _sku, url in links[:6]))
        flags = []
        if self.store.is_favorite(game.id):
            flags.append(i18n("tag_fav"))
        if game.id in self.store.playlist():
            flags.append(i18n("tag_pl"))
        if game.id in self.store.excluded():
            flags.append(i18n("tag_ex"))
        if flags:
            lines.append(i18n("tag_line") + ": " + ", ".join(flags))
        self.game_meta.setPlainText("\n".join(lines))

    def _queue_icon(self, game: Game) -> None:
        if game is None or not game.icon_hash:
            return
        if game.id in self._icon_requested:
            return
        self._icon_requested.add(game.id)
        self._icon_queue.append(game)
        if not self._icon_timer.isActive():
            self._icon_timer.start()

    def _pump_icons(self) -> None:
        started = 0
        while self._icon_queue and started < 2:
            game = self._icon_queue.pop(0)
            url = game.icon_url(64)
            if not url:
                continue
            started += 1

            def done(pixmap: QPixmap, game_id: str = game.id) -> None:
                if not pixmap.isNull():
                    self.model.set_icon(game_id, pixmap)

            self.images.get(url, done)
        if not self._icon_queue:
            self._icon_timer.stop()

    def collect(self) -> ActivityConfig:
        flags = 0
        for bit, box in self.flag_boxes:
            if box.isChecked():
                flags |= bit
        start = None
        end = None
        if self.use_start.isChecked():
            start = int(self.start_dt.dateTime().toSecsSinceEpoch())
        if self.use_end.isChecked():
            end = int(self.end_dt.dateTime().toSecsSinceEpoch())
        privacy = self.party_privacy.currentData()
        return ActivityConfig(
            type=int(self.activity_type.currentData()),
            status_display_type=int(self.status_display.currentData()),
            name=self.activity_name.text() or None,
            url=self.stream_url.text() or None,
            details=self.details.text() or None,
            details_url=self.details_url.text() or None,
            state=self.state.text() or None,
            state_url=self.state_url.text() or None,
            start=start,
            end=end,
            large_image=self.large_image.text() or None,
            large_text=self.large_text.text() or None,
            large_url=self.large_url.text() or None,
            small_image=self.small_image.text() or None,
            small_text=self.small_text.text() or None,
            small_url=self.small_url.text() or None,
            party_id=self.party_id.text() or None,
            party_size=self.party_size.value() if self.use_party.isChecked() else None,
            party_max=self.party_max.value() if self.use_party.isChecked() else None,
            party_privacy=None if privacy == -1 else int(privacy),
            join_secret=self.join_secret.text() or None,
            spectate_secret=self.spectate_secret.text() or None,
            match_secret=self.match_secret.text() or None,
            button1_label=self.btn1_label.text() or None,
            button1_url=self.btn1_url.text() or None,
            button2_label=self.btn2_label.text() or None,
            button2_url=self.btn2_url.text() or None,
            instance=self.instance.isChecked(),
            flags=flags or None,
            emoji_name=self.emoji_name.text() or None,
            emoji_id=self.emoji_id.text() or None,
            emoji_animated=self.emoji_anim.isChecked(),
            application_id=self.app_id.text().strip() or None,
            pid=int(self.pid.value()) or os.getpid(),
        )

    def apply_config(self, game_id: str | None, config: ActivityConfig) -> None:
        if game_id:
            self._select_game_id(game_id)
        if config.application_id:
            self.app_id.setText(config.application_id)
        self.activity_name.setText(config.name or "")
        self.activity_type.setCurrentIndex(max(0, self.activity_type.findData(config.type)))
        self.status_display.setCurrentIndex(
            max(0, self.status_display.findData(config.status_display_type))
        )
        self.stream_url.setText(config.url or "")
        if config.pid:
            self.pid.setValue(int(config.pid))
        self.details.setText(config.details or "")
        self.details_url.setText(config.details_url or "")
        self.state.setText(config.state or "")
        self.state_url.setText(config.state_url or "")
        self.emoji_name.setText(config.emoji_name or "")
        self.emoji_id.setText(config.emoji_id or "")
        self.emoji_anim.setChecked(bool(config.emoji_animated))
        self.large_image.setText(config.large_image or "")
        self.large_text.setText(config.large_text or "")
        self.large_url.setText(config.large_url or "")
        self.small_image.setText(config.small_image or "")
        self.small_text.setText(config.small_text or "")
        self.small_url.setText(config.small_url or "")
        self.use_start.setChecked(bool(config.start))
        if config.start:
            self.start_dt.setDateTime(
                QDateTime.fromSecsSinceEpoch(int(config.start), QTimeZone.LocalTime)
            )
        self.use_end.setChecked(bool(config.end))
        if config.end:
            self.end_dt.setDateTime(
                QDateTime.fromSecsSinceEpoch(int(config.end), QTimeZone.LocalTime)
            )
        self.party_id.setText(config.party_id or "")
        self.use_party.setChecked(config.party_size is not None)
        if config.party_size:
            self.party_size.setValue(int(config.party_size))
        if config.party_max:
            self.party_max.setValue(int(config.party_max))
        privacy = -1 if config.party_privacy is None else int(config.party_privacy)
        self.party_privacy.setCurrentIndex(max(0, self.party_privacy.findData(privacy)))
        self.join_secret.setText(config.join_secret or "")
        self.spectate_secret.setText(config.spectate_secret or "")
        self.match_secret.setText(config.match_secret or "")
        self.btn1_label.setText(config.button1_label or "")
        self.btn1_url.setText(config.button1_url or "")
        self.btn2_label.setText(config.button2_label or "")
        self.btn2_url.setText(config.button2_url or "")
        self.instance.setChecked(bool(config.instance))
        flags = int(config.flags or 0)
        for bit, box in self.flag_boxes:
            box.setChecked(bool(flags & bit))
        self._update_preview()

    def _preview_pixmaps(self, config: ActivityConfig) -> None:
        game = self._game
        large = None
        small = None
        if game:
            if config.large_image and game.cover_image_hash == config.large_image:
                large = game.cover_url(128)
            elif config.large_image and game.icon_hash == config.large_image:
                large = game.icon_url(128)
            elif game.cover_url():
                large = game.cover_url(128)
            else:
                large = game.icon_url(128)
            if config.small_image and game.icon_hash == config.small_image:
                small = game.icon_url(64)
        if config.large_image and config.large_image.startswith("http"):
            large = config.large_image
        if config.small_image and config.small_image.startswith("http"):
            small = config.small_image
        if large:
            self.images.get(large, self.preview.set_large)
        else:
            self.preview.set_large(QPixmap())
        if small:
            self.images.get(small, self.preview.set_small)
        else:
            self.preview.set_small(QPixmap())

    @Slot()
    def _update_preview(self) -> None:
        config = self.collect()
        self.preview.set_game(self._game)
        self.preview.set_config(config)
        self._preview_pixmaps(config)

    def _on_tick(self) -> None:
        if self.use_start.isChecked():
            self.preview.set_config(self.collect())
        self._refresh_random_countdown()
        self._tick_schedule()
        self._tick_idle()

    def _stamp_now(self) -> None:
        self.start_dt.setDateTime(QDateTime.currentDateTime())
        self.use_start.setChecked(True)

    def _apply_duration(self) -> None:
        seconds = int(self.duration.value())
        if seconds <= 0:
            return
        start = self.start_dt.dateTime() if self.use_start.isChecked() else QDateTime.currentDateTime()
        if not self.use_start.isChecked():
            self.use_start.setChecked(True)
            self.start_dt.setDateTime(start)
        self.use_end.setChecked(True)
        self.end_dt.setDateTime(start.addSecs(seconds))

    def _connect(self, silent: bool = False) -> None:
        if not silent and not self._require_member():
            return
        app_id = self.app_id.text().strip()
        if not app_id:
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("warn_no_game"))
            return
        if not find_discord_ipc():
            self._log(key="log_no_ipc")
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("msg_no_ipc"))
            if self.auto_reconnect.isChecked() and self._want_connected:
                self._schedule_reconnect()
            return
        if self.ipc.connected and self.ipc.client_id == app_id:
            self._set_status(i18n("status_already", id=app_id))
            return
        self._want_connected = True
        self._set_status(i18n("status_connecting"))
        self._log(key="log_connecting", id=app_id)
        self.ipc.connect(app_id)

    def _disconnect(self) -> None:
        self._want_connected = False
        self._reconnect_tries = 0
        self.ipc.disconnect("user")
        self._log(key="log_disconnected")

    def _update_rpc(self, silent: bool = False) -> None:
        app_id = self.app_id.text().strip()
        if not app_id:
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("warn_no_game"))
            return
        if not self.ipc.connected or self.ipc.client_id != app_id:
            self._pending_update = True
            self._connect(silent=silent)
            return
        config = self.collect()
        activity = config.build()
        pid = config.pid or os.getpid()
        self.ipc.set_activity(pid, activity)
        self._last_activity_at = time.monotonic()
        self._log(key="log_set_activity", pid=pid, name=self._game.name if self._game else app_id)
        if not silent:
            self._set_status(i18n("status_rpc"))
        if self.science_enabled.isChecked() and not silent:
            self._run_science(reason=f"rpc:{app_id}")

    def _clear_rpc(self) -> None:
        if not self.ipc.connected:
            return
        self.ipc.set_activity(self.pid.value() or os.getpid(), None)
        self._set_status(i18n("status_cleared"))

    def _copy_json(self) -> None:
        payload = self.collect().build()
        QGuiApplication.clipboard().setText(json.dumps(payload, indent=2, ensure_ascii=False))
        self._set_status(i18n("status_json"))

    def _refresh_profiles(self) -> None:
        current = self.profile_box.currentText()
        self.profile_box.blockSignals(True)
        self.profile_box.clear()
        self.profile_box.addItems(self.store.names())
        self.profile_box.setCurrentText(current)
        self.profile_box.blockSignals(False)

    def _save_profile(self) -> None:
        name = self.profile_box.currentText().strip()
        if not name:
            name = (self._game.name if self._game else "profil") + " RPC"
            self.profile_box.setCurrentText(name)
        self.store.put(name, self._game.id if self._game else self.app_id.text().strip(), self.collect())
        self._refresh_profiles()
        self._set_status(i18n("status_profile_saved", name=name))

    def _load_profile(self) -> None:
        name = self.profile_box.currentText().strip()
        loaded = self.store.get(name)
        if loaded is None:
            QMessageBox.information(self, APP_TITLE, i18n("msg_no_profile"))
            return
        game_id, config = loaded
        self.apply_config(game_id, config)
        self._set_status(i18n("status_profile_loaded", name=name))

    def _delete_profile(self) -> None:
        name = self.profile_box.currentText().strip()
        if not name:
            return
        self.store.delete(name)
        self._refresh_profiles()

    def _restore_extra_settings(self) -> None:
        settings = self.store.settings()
        interval = int(settings.get("random_interval") or 60)
        self.random_interval.setValue(max(5, min(86400, interval)))
        source = str(settings.get("random_source") or "filter")
        index = self.random_source.findData(source)
        if index >= 0:
            self.random_source.setCurrentIndex(index)
        self.random_norepeat.setValue(int(settings.get("random_norepeat") or 8))
        self.cycle_interval.setValue(int(settings.get("cycle_interval") or 20))
        self.cycle_lines.setPlainText(str(settings.get("cycle_lines") or ""))
        self.auto_reconnect.setChecked(bool(settings.get("auto_reconnect", True)))
        self.idle_clear.setChecked(bool(settings.get("idle_clear")))
        self.idle_seconds.setValue(int(settings.get("idle_seconds") or 1800))
        self.schedule_enabled.setChecked(bool(settings.get("schedule_enabled")))
        start = str(settings.get("schedule_start") or "09:00")
        end = str(settings.get("schedule_end") or "23:00")
        self.schedule_start.setTime(QTime.fromString(start, "HH:mm"))
        self.schedule_end.setTime(QTime.fromString(end, "HH:mm"))
        self.detect_apply.setChecked(bool(settings.get("detect_apply")))
        self.detect_pid.setChecked(bool(settings.get("detect_pid", True)))
        if bool(settings.get("detect_enabled")):
            self.detect_enabled.setChecked(True)
        self.science_enabled.setChecked(bool(settings.get("science_enabled")))
        self.science_on_random.setChecked(bool(settings.get("science_on_random", True)))
        self.science_on_detect.setChecked(bool(settings.get("science_on_detect")))
        self.science_on_current.setChecked(bool(settings.get("science_on_current", True)))
        mode_index = self.science_mode.findData(str(settings.get("science_mode") or "playtime"))
        if mode_index >= 0:
            self.science_mode.setCurrentIndex(mode_index)
        self.science_hours.setValue(float(settings.get("science_hours") or 2.0))
        self.science_batch.setValue(int(settings.get("science_batch") or 20))
        self.science_delay.setValue(float(settings.get("science_delay") or 0.8))
        self.science_jitter.setValue(float(settings.get("science_jitter") or 0.05))
        source_index = self.science_source.findData(str(settings.get("science_source") or "current"))
        if source_index >= 0:
            self.science_source.setCurrentIndex(source_index)
        self.science_token.setText(self.science.state.token)
        self.science_cookie.setText(self.science.state.cookie)
        self.science_fp.setText(self.science.state.fingerprint)
        self.science_target_hours.setValue(float(settings.get("science_target_hours") or 0))
        lang = str(settings.get("lang") or "tr")
        idx = self.lang_box.findData(lang)
        if idx >= 0:
            self.lang_box.blockSignals(True)
            self.lang_box.setCurrentIndex(idx)
            self.lang_box.blockSignals(False)
        self._lang = lang
        set_lang(lang)
        self._apply_language()
        self._refresh_science_status()
        self._refresh_pid_list()

    def _save_random_settings(self, *_args) -> None:
        settings = self.store.settings()
        settings["random_interval"] = int(self.random_interval.value())
        settings["random_source"] = self.random_source.currentData()
        settings["random_norepeat"] = int(self.random_norepeat.value())
        settings["cycle_interval"] = int(self.cycle_interval.value())
        settings["cycle_lines"] = self.cycle_lines.toPlainText()
        settings["auto_reconnect"] = self.auto_reconnect.isChecked()
        settings["idle_clear"] = self.idle_clear.isChecked()
        settings["idle_seconds"] = int(self.idle_seconds.value())
        settings["schedule_enabled"] = self.schedule_enabled.isChecked()
        settings["schedule_start"] = self.schedule_start.time().toString("HH:mm")
        settings["schedule_end"] = self.schedule_end.time().toString("HH:mm")
        settings["detect_enabled"] = self.detect_enabled.isChecked()
        settings["detect_apply"] = self.detect_apply.isChecked()
        settings["detect_pid"] = self.detect_pid.isChecked()
        settings["science_enabled"] = self.science_enabled.isChecked()
        settings["science_on_random"] = self.science_on_random.isChecked()
        settings["science_on_detect"] = self.science_on_detect.isChecked()
        settings["science_on_current"] = self.science_on_current.isChecked()
        settings["science_mode"] = self.science_mode.currentData()
        settings["science_hours"] = float(self.science_hours.value())
        settings["science_batch"] = int(self.science_batch.value())
        settings["science_delay"] = float(self.science_delay.value())
        settings["science_jitter"] = float(self.science_jitter.value())
        settings["science_source"] = self.science_source.currentData()
        settings["science_target_hours"] = float(self.science_target_hours.value())
        settings["lang"] = self.lang_box.currentData() or "tr"
        self.store.save()

    def _on_random_interval_changed(self, _value: int = 0) -> None:
        self._save_random_settings()
        if self.random_enabled.isChecked():
            self._random_timer.start(int(self.random_interval.value()) * 1000)
            self._refresh_random_countdown()

    def _on_random_toggled(self, enabled: bool) -> None:
        if enabled:
            pool = self._random_pool()
            if not pool:
                self.random_enabled.blockSignals(True)
                self.random_enabled.setChecked(False)
                self.random_enabled.blockSignals(False)
                QMessageBox.warning(self, APP_TITLE, i18n("msg_no_random"))
                return
            self._random_switch()
        else:
            self._random_timer.stop()
            self.random_countdown.setText("")

    def _games_by_ids(self, ids: list[str]) -> list[Game]:
        games: list[Game] = []
        for game_id in ids:
            game = self.catalog.get(game_id)
            if game is not None:
                games.append(game)
        return games

    def _random_pool(self) -> list[Game]:
        source = self.random_source.currentData()
        if source == "favorites":
            pool = self._games_by_ids(self.store.favorites())
        elif source == "playlist":
            pool = self._games_by_ids(self.store.playlist())
        elif source == "filter":
            pool = list(self.model.games())
        else:
            pool = list(self.catalog.games)
        excluded = set(self.store.excluded())
        pool = [game for game in pool if game.id not in excluded]
        return pool

    def _pick_weighted(self, games: list[Game]) -> Game:
        blocked = set(self._random_history)
        blocked.update(self.store.excluded())
        current = self._game.id if self._game else None
        if current:
            blocked.add(current)
        candidates = [game for game in games if game.id not in blocked] or list(games)
        weights = [self.store.weight(game.id) for game in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _random_switch(self, _checked: bool = False) -> None:
        pool = self._random_pool()
        if not pool:
            self._set_status(i18n("status_random_none"))
            return
        norepeat = int(self.random_norepeat.value())
        self._random_history = deque(self._random_history, maxlen=max(1, norepeat or 1))
        if norepeat <= 0:
            self._random_history.clear()
        game = pool[0] if len(pool) == 1 else self._pick_weighted(pool)
        if norepeat > 0:
            self._random_history.append(game.id)
        self._select_game_id(game.id)
        self._stamp_now()
        if self.random_enabled.isChecked():
            self._random_timer.start(int(self.random_interval.value()) * 1000)
        self._update_rpc(silent=True)
        self._set_status(i18n("status_random", name=game.name))
        self._refresh_random_countdown()
        if self.science_enabled.isChecked() and self.science_on_random.isChecked():
            self._run_science(reason=f"random:{game.id}", games=[game])

    def _refresh_random_countdown(self) -> None:
        if not self.random_enabled.isChecked() or not self._random_timer.isActive():
            self.random_countdown.setText("")
            return
        remaining = max(0, int(self._random_timer.remainingTime() / 1000))
        name = self._game.name if self._game else "—"
        self.random_countdown.setText(i18n("countdown", name=name, s=remaining))

    def _on_ready(self, data: dict) -> None:
        user = data.get("user") or {}
        name = user.get("global_name") or user.get("username") or ""
        self._ready_user = str(name)
        extra = f" @{self._ready_user}" if self._ready_user else ""
        self._reconnect_tries = 0
        self._set_connected_visual(True)
        self._set_status(i18n("status_connected", extra=extra, id=self.ipc.client_id))
        self._log(key="log_ready", user=self._ready_user, id=self.ipc.client_id)
        self._pending_update = False
        QTimer.singleShot(50, lambda: self._update_rpc(silent=True))

    def _set_connected_visual(self, on: bool) -> None:
        self.status_dot.setObjectName("statusOn" if on else "statusOff")
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def _on_ipc_failed(self, message: str) -> None:
        self._set_connected_visual(False)
        self._pending_update = False
        self._set_status(message)
        self._log(message)
        if self._want_connected and self.auto_reconnect.isChecked():
            self._schedule_reconnect()

    def _on_ipc_closed(self, reason: str) -> None:
        self._set_connected_visual(False)
        self._log(key="log_ipc_closed", reason=reason)
        if reason not in {"disconnected", "user", "ipc-loop-end"}:
            self._set_status(i18n("status_cut", reason=reason))
        elif not self.ipc.connected:
            self._set_status(i18n("status_offline"))
        if self._want_connected and reason != "user" and self.auto_reconnect.isChecked():
            self._schedule_reconnect()

    def _on_frame(self, payload: dict) -> None:
        if payload.get("evt") == "ERROR":
            data = payload.get("data") or {}
            message = data.get("message") if isinstance(data, dict) else data
            self._set_status(i18n("status_rpc_err", message=message))
            self._log(key="log_error", message=message)
            return
        if payload.get("cmd") == "SET_ACTIVITY" and payload.get("evt") is None:
            self._log(key="log_set_ok")
            if self.random_enabled.isChecked():
                self._refresh_random_countdown()
            else:
                self._set_status(i18n("status_rpc_ok"))

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _set_socket_status(self, text: str) -> None:
        self.socket_label.setText(text)

    def _next_extra_pid(self) -> int:
        pid = max(1000, (os.getpid() % 1_000_000) + 10_000)
        used = {int(self.pid.value())} | self._extra_pids
        while pid in used:
            pid += 1
        self._extra_pids.add(pid)
        return pid

    def _pin_current(self) -> None:
        game = self._game
        if game is None:
            QMessageBox.warning(self, APP_TITLE, i18n("msg_pin_need"))
            return
        if any(slot.game_id == game.id for slot in self.extra_slots):
            QMessageBox.information(self, APP_TITLE, i18n("msg_pin_dup", name=game.name))
            return
        if len(self.extra_slots) >= MAX_EXTRA_SLOTS:
            QMessageBox.warning(self, APP_TITLE, i18n("msg_pin_max", n=MAX_EXTRA_SLOTS))
            return
        if not find_discord_ipc():
            QMessageBox.warning(self, APP_TITLE, i18n("msg_no_ipc"))
            return
        config = self.collect()
        config.application_id = game.id
        config.pid = self._next_extra_pid()
        slot = ExtraSlot(game, config, int(config.pid), self)
        slot.changed.connect(self._refresh_extra_list)
        self.extra_slots.append(slot)
        self._refresh_extra_list()
        slot.start()
        self._set_status(i18n("status_pin", name=game.name, n=len(self.extra_slots)))

    def _unpin_selected(self) -> None:
        item = self.extra_list.currentItem()
        if item is None:
            return
        game_id = item.data(Qt.ItemDataRole.UserRole)
        self._unpin_game_id(str(game_id) if game_id else "")

    def _unpin_game_id(self, game_id: str) -> None:
        keep: list[ExtraSlot] = []
        for slot in self.extra_slots:
            if slot.game_id == game_id:
                slot.stop()
                self._extra_pids.discard(slot.pid)
            else:
                keep.append(slot)
        self.extra_slots = keep
        self._refresh_extra_list()

    def _unpin_all(self) -> None:
        for slot in self.extra_slots:
            slot.stop()
            self._extra_pids.discard(slot.pid)
        self.extra_slots.clear()
        self._refresh_extra_list()
        self._set_status(i18n("status_extras_off"))

    def _slot_state(self, slot: ExtraSlot) -> str:
        raw = str(slot.state or "")
        mapping = {
            "connecting": i18n("slot_connecting"),
            "closed": i18n("slot_closed"),
            "live": i18n("slot_live"),
            "dropped": i18n("slot_cut"),
        }
        if raw in mapping:
            return mapping[raw]
        if raw.startswith("error:"):
            return i18n("slot_error", message=raw.split(":", 1)[-1])
        return raw

    def _refresh_extra_list(self) -> None:
        selected = None
        current = self.extra_list.currentItem()
        if current is not None:
            selected = current.data(Qt.ItemDataRole.UserRole)
        self.extra_list.clear()
        for slot in self.extra_slots:
            item = QListWidgetItem(f"{slot.game.name}  ·  {self._slot_state(slot)}  ·  pid {slot.pid}")
            item.setData(Qt.ItemDataRole.UserRole, slot.game_id)
            self.extra_list.addItem(item)
            if selected and slot.game_id == selected:
                self.extra_list.setCurrentItem(item)

    def _format_log(self, key: str, kwargs: dict) -> str:
        data = dict(kwargs)
        state_key = data.pop("state_key", None)
        if state_key:
            data["state"] = i18n(str(state_key))
        return i18n(key, **data) if key else str(data.get("text") or "")

    def _log(self, text: str = "", *, key: str = "", **kwargs) -> None:
        stamp = QTime.currentTime().toString("HH:mm:ss")
        if key:
            self._log_records.append((stamp, key, dict(kwargs)))
            text = self._format_log(key, kwargs)
        else:
            self._log_records.append((stamp, "", {"text": text}))
        if hasattr(self, "log_view"):
            self.log_view.append(f"[{stamp}] {text}")

    def _replay_logs(self) -> None:
        if not hasattr(self, "log_view"):
            return
        self.log_view.clear()
        for stamp, key, kwargs in self._log_records[-300:]:
            text = self._format_log(key, kwargs) if key else str(kwargs.get("text") or "")
            self.log_view.append(f"[{stamp}] {text}")

    def _clear_log(self) -> None:
        self._log_records.clear()
        if hasattr(self, "log_view"):
            self.log_view.clear()

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+R"), self, self._random_switch)
        QShortcut(QKeySequence("Ctrl+U"), self, lambda: self._update_rpc())
        QShortcut(QKeySequence("Ctrl+L"), self, self._clear_rpc)
        QShortcut(QKeySequence("Ctrl+P"), self, self._pin_current)
        QShortcut(QKeySequence("Ctrl+D"), self, self._scan_running)
        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_favorite)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self._fill_store_button)

    def _refresh_fav_buttons(self) -> None:
        game = self._game
        if game is None:
            return
        self.btn_fav.setText(i18n("fav_on") if self.store.is_favorite(game.id) else i18n("fav_off"))
        self.btn_playlist.setText(
            i18n("pl_on") if game.id in self.store.playlist() else i18n("pl_off")
        )
        self.btn_exclude.setText(
            i18n("ex_on") if game.id in self.store.excluded() else i18n("ex_off")
        )
        self.weight_box.blockSignals(True)
        self.weight_box.setValue(self.store.weight(game.id))
        self.weight_box.blockSignals(False)

    def _toggle_favorite(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_favorite(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._set_status(i18n("status_fav_on" if on else "status_fav_off", name=self._game.name))

    def _toggle_playlist(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_playlist(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._set_status(i18n("status_pl_on" if on else "status_pl_off", name=self._game.name))

    def _toggle_excluded(self) -> None:
        if self._game is None:
            return
        on = self.store.toggle_excluded(self._game.id)
        self._refresh_fav_buttons()
        self._fill_game_meta(self._game)
        self._set_status(i18n("status_ex_on" if on else "status_ex_off", name=self._game.name))

    def _on_weight_changed(self, value: int) -> None:
        if self._game is None:
            return
        self.store.set_weight(self._game.id, int(value))

    def _fill_assets(self, game: Game) -> None:
        self.asset_box.blockSignals(True)
        self.asset_box.clear()
        if game.cover_image_hash:
            self.asset_box.addItem(i18n("asset_cover"), ("cover", game.cover_image_hash, game.cover_url(256)))
        if game.icon_hash:
            self.asset_box.addItem(i18n("asset_icon"), ("icon", game.icon_hash, game.icon_url(128)))
        for dist, sku, url in game_store_links(game):
            self.asset_box.addItem(i18n("asset_store", dist=dist), ("url", url, url))
        self.asset_box.blockSignals(False)
        if self.asset_box.count():
            self._on_asset_picked()
        else:
            self.asset_preview.setText(i18n("asset_none"))
            self.asset_preview.setPixmap(QPixmap())

    def _current_asset(self) -> tuple[str, str, str] | None:
        data = self.asset_box.currentData()
        if not data:
            return None
        kind, value, url = data
        return str(kind), str(value or ""), str(url or "")

    def _on_asset_picked(self, *_args) -> None:
        asset = self._current_asset()
        if asset is None:
            return
        _kind, value, url = asset
        if url.startswith("http"):
            self.images.get(url, self._set_asset_preview)
        else:
            self.asset_preview.setText(value[:48] or "Asset")

    def _set_asset_preview(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.asset_preview.setPixmap(
            pixmap.scaled(72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def _apply_asset(self, target: str) -> None:
        asset = self._current_asset()
        if asset is None:
            return
        kind, value, url = asset
        payload = url if kind == "url" else value
        if target == "large":
            self.large_image.setText(payload)
            if self._game:
                self.large_text.setText(self._game.name)
        else:
            self.small_image.setText(payload)

    def _copy_asset_url(self) -> None:
        asset = self._current_asset()
        if asset is None:
            return
        QGuiApplication.clipboard().setText(asset[2] or asset[1])
        self._set_status(i18n("status_asset_copied"))

    def _fill_store_button(self) -> None:
        if self._game is None:
            return
        button = primary_store_button(self._game)
        if button is None:
            QMessageBox.information(self, APP_TITLE, i18n("warn_no_sku"))
            return
        if not self.btn1_label.text().strip():
            self.btn1_label.setText(button["label"])
            self.btn1_url.setText(button["url"])
        elif not self.btn2_label.text().strip():
            self.btn2_label.setText(button["label"])
            self.btn2_url.setText(button["url"])
        else:
            self.btn1_label.setText(button["label"])
            self.btn1_url.setText(button["url"])
        self._set_status(i18n("status_store", label=button["label"]))

    def _cycle_frames(self) -> list[list[str]]:
        frames: list[list[str]] = []
        for raw in self.cycle_lines.toPlainText().splitlines():
            line = raw.strip()
            if not line:
                continue
            frames.append([part.strip() for part in line.split("|")])
        return frames

    def _on_cycle_toggled(self, enabled: bool) -> None:
        self._save_random_settings()
        if enabled:
            if not self._cycle_frames():
                self.cycle_enabled.blockSignals(True)
                self.cycle_enabled.setChecked(False)
                self.cycle_enabled.blockSignals(False)
                QMessageBox.warning(self, APP_TITLE, i18n("msg_cycle"))
                return
            self._cycle_index = 0
            self._cycle_step()
            self._restart_cycle_timer()
        else:
            self._cycle_timer.stop()

    def _restart_cycle_timer(self, *_args) -> None:
        if self.cycle_enabled.isChecked():
            self._cycle_timer.start(int(self.cycle_interval.value()) * 1000)
        self._save_random_settings()

    def _cycle_step(self) -> None:
        frames = self._cycle_frames()
        if not frames:
            return
        frame = frames[self._cycle_index % len(frames)]
        self._cycle_index += 1
        self._applying_cycle = True
        if len(frame) > 0 and frame[0]:
            self.details.setText(frame[0][:128])
        if len(frame) > 1:
            self.state.setText(frame[1][:128])
        if len(frame) > 2 and frame[2]:
            self.btn1_label.setText(frame[2][:32])
        if len(frame) > 3 and frame[3]:
            self.btn1_url.setText(frame[3][:512])
        self._applying_cycle = False
        self._update_rpc(silent=True)
        self._log(key="log_cycle", n=self._cycle_index)

    def _in_schedule(self) -> bool:
        start = self.schedule_start.time()
        end = self.schedule_end.time()
        now = QTime.currentTime()
        if start <= end:
            return start <= now <= end
        return now >= start or now <= end

    def _tick_schedule(self) -> None:
        if not self.schedule_enabled.isChecked():
            return
        if self._in_schedule():
            if not self.ipc.connected and not self._want_connected:
                self._connect(silent=True)
        elif self.ipc.connected:
            self._clear_rpc()
            self._want_connected = False
            self.ipc.disconnect("schedule")
            self._set_status(i18n("status_sched_off"))

    def _tick_idle(self) -> None:
        if not self.idle_clear.isChecked() or not self.ipc.connected:
            return
        elapsed = time.monotonic() - self._last_activity_at
        if elapsed >= int(self.idle_seconds.value()):
            self._clear_rpc()
            self._last_activity_at = time.monotonic()
            self._log(key="log_idle")

    def _schedule_reconnect(self) -> None:
        self._reconnect_tries += 1
        delay = min(30, 2 ** min(self._reconnect_tries, 5)) * 1000
        self._log(key="log_reconnect", s=delay // 1000)
        QTimer.singleShot(delay, lambda: self._connect(silent=True) if self._want_connected else None)

    def _on_detect_toggled(self, enabled: bool) -> None:
        self._save_random_settings()
        if enabled:
            self._detect_timer.start()
            self._scan_running()
        else:
            self._detect_timer.stop()

    def _scan_running(self, *_args) -> None:
        if getattr(self, "_scan_busy", False):
            return
        self._scan_busy = True

        def work() -> None:
            try:
                found = self._detector.scan()
            except Exception:
                found = []
            QTimer.singleShot(0, lambda items=found: self._apply_scan(items))

        from threading import Thread

        Thread(target=work, name="ky-detect", daemon=True).start()

    def _apply_scan(self, found) -> None:
        self._scan_busy = False
        self._detected = found
        current = self.detect_box.currentData()
        self.detect_box.blockSignals(True)
        self.detect_box.clear()
        for item in found:
            self.detect_box.addItem(
                f"{item.game.name}  ·  pid {item.process.pid}  ·  {item.matched}",
                item.game.id,
            )
        self.detect_box.blockSignals(False)
        if current:
            index = self.detect_box.findData(current)
            if index >= 0:
                self.detect_box.setCurrentIndex(index)
        self._log(key="log_detect", n=len(found))
        if found and self.detect_apply.isChecked():
            first = found[0]
            if self._game is None or self._game.id != first.game.id:
                self._apply_detected(first)

    def _use_detected(self) -> None:
        game_id = self.detect_box.currentData()
        if not game_id:
            return
        for item in self._detected:
            if item.game.id == game_id:
                self._apply_detected(item)
                return

    def _apply_detected(self, item: DetectedGame) -> None:
        self._select_game_id(item.game.id)
        if self.detect_pid.isChecked():
            self.pid.setValue(int(item.process.pid))
        self._stamp_now()
        self._update_rpc(silent=True)
        self._set_status(i18n("status_detected", name=item.game.name, pid=item.process.pid))
        if not self.science.state.fingerprint:
            self._log(key="log_fp")
        if self.science_enabled.isChecked() and self.science_on_detect.isChecked():
            self._run_science(reason=f"detect:{item.game.id}", games=[item.game])

    def _refresh_pid_list(self) -> None:
        current = int(self.pid.value())
        self.pid_box.blockSignals(True)
        self.pid_box.clear()
        self.pid_box.addItem(i18n("pid_this", pid=os.getpid()), os.getpid())
        for item in self._detected:
            self.pid_box.addItem(
                f"{item.game.name} ({item.process.pid})",
                item.process.pid,
            )
        for proc in list_processes()[:80]:
            label = proc.name or Path(proc.exe).name or str(proc.pid)
            self.pid_box.addItem(f"{label} ({proc.pid})", proc.pid)
        index = self.pid_box.findData(current)
        if index >= 0:
            self.pid_box.setCurrentIndex(index)
        self.pid_box.blockSignals(False)

    def _on_pid_picked(self, *_args) -> None:
        value = self.pid_box.currentData()
        if value:
            self.pid.setValue(int(value))

    def _use_self_pid(self) -> None:
        self.pid.setValue(os.getpid())
        index = self.pid_box.findData(os.getpid())
        if index >= 0:
            self.pid_box.setCurrentIndex(index)

    def _science_pool(self, games: list[Game] | None = None) -> list[Game]:
        if games:
            return games
        source = self.science_source.currentData()
        if source == "current":
            return [self._game] if self._game else []
        if source == "favorites":
            return self._games_by_ids(self.store.favorites())
        if source == "playlist":
            return self._games_by_ids(self.store.playlist())
        if source == "filter":
            return list(self.model.games())
        if source == "missing":
            have = set(self.store.played())
            return [game for game in self.catalog.games if game.id not in have]
        return list(self.catalog.games)

    def _run_science(self, reason: str = "manual", games: list[Game] | None = None) -> None:
        if not self._require_member():
            return
        if self.science.busy:
            return
        if reason != "manual" and not self.science_enabled.isChecked():
            return
        if reason != "manual" and self.science_on_current.isChecked() and self._game:
            games = [self._game]
        pool = self._science_pool(games)
        if not pool:
            if reason == "manual":
                QMessageBox.warning(self, APP_TITLE, i18n("warn_no_science_games"))
            return
        slot = f"{reason}:{pool[0].id}:{len(pool)}"
        if reason != "manual" and slot == self._science_ran_slot:
            return
        self._science_ran_slot = slot
        mode = str(self.science_mode.currentData() or "playtime")
        hours = float(self.science_hours.value())
        target = float(self.science_target_hours.value())
        if target > 0 and self._game and (games is None or len(pool) == 1):
            hours = target
            pool = [self._game]
        if mode == "played":
            hours = 60 / 3600
        self._science_last_ids = [game.id for game in pool]
        extra = max(0.2, float(self.science_delay.value()) * 0.5)
        self.science.start_farm(
            pool,
            hours,
            batch_size=int(self.science_batch.value()),
            delay=float(self.science_delay.value()),
            jitter=float(self.science_jitter.value()),
            extra_delay=(extra, extra + 1.0),
            mode=mode,
        )
        self._refresh_science_status()
        self._log(key="log_science_run", mode=mode, n=len(pool), reason=reason)

    def _save_science_credentials(self) -> None:
        self.science.save_credentials(
            self.science_token.text(),
            self.science_cookie.text(),
            self.science_fp.text(),
        )
        self._set_status(i18n("status_science_saved"))

    def _pull_science_from_client(self, silent: bool = False) -> None:
        auth = self.science.pull_from_client()
        self.science_token.setText(self.science.state.token)
        self.science_cookie.setText(self.science.state.cookie)
        if auth.fingerprint:
            self.science_fp.setText(self.science.state.fingerprint)
        self._refresh_science_status()
        if silent:
            return
        if auth.token and auth.cookie:
            who = auth.client or "disk"
            uid = f" uid={auth.user_id}" if auth.user_id else ""
            self._set_status(i18n("status_science_who", who=who, uid=uid))
        else:
            extra = "\n".join(auth.notes[-4:]) if auth.notes else i18n("warn_no_auth")
            QMessageBox.warning(self, APP_TITLE, extra)

    def _on_science_harvested(self, token: str, cookie: str, fingerprint: str, label: str) -> None:
        if token:
            self.science_token.setText(token)
        if cookie:
            self.science_cookie.setText(cookie)
        if fingerprint:
            self.science_fp.setText(fingerprint)
        self._refresh_science_status()
        self._log(key="log_science_id", label=label)

    def _import_science_state(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n("dialog_science_import"), str(Path.home()), "JSON (*.json)"
        )
        if not path:
            return
        from .science import ScienceState

        incoming = ScienceState.load(Path(path))
        self.science.save_credentials(incoming.token, incoming.cookie, incoming.fingerprint)
        if incoming.analytics_token:
            self.science.state.analytics_token = incoming.analytics_token
            self.science.state.fetched_at = incoming.fetched_at
            self.science.state.save(self.science.state_path)
        self.science_token.setText(self.science.state.token)
        self.science_cookie.setText(self.science.state.cookie)
        self.science_fp.setText(self.science.state.fingerprint)
        self._refresh_science_status()
        self._set_status(i18n("status_science_imported", path=path))

    def _refresh_science_status(self) -> None:
        if not hasattr(self, "science_status"):
            return
        state = self.science.state
        bits = []
        live_clients = list_running_clients()
        live = live_clients[0] if live_clients else None
        if live:
            bits.append(f"{live.name} pid={live.pid}")
        elif self.science.last_auth and self.science.last_auth.client:
            bits.append(self.science.last_auth.client)
        bits.append(i18n("science_token_ok") if state.has_token else i18n("science_token_no"))
        bits.append(i18n("science_cookie_ok") if state.has_cookie else i18n("science_cookie_no"))
        bits.append(i18n("science_fp_ok") if state.fingerprint else i18n("science_fp_no"))
        bits.append(i18n("science_busy") if self.science.busy else i18n("science_idle"))
        self.science_status.setText(" · ".join(bits))
        busy = self.science.busy
        self.btn_science_run.setEnabled(not busy)
        self.btn_science_stop.setEnabled(busy)

    def _on_science_progress(self, request_no: int, sent_ok: int, status: int, detail: str) -> None:
        self._log(key="log_science_packet", n=request_no, status=status, detail=detail)
        if hasattr(self, "science_status"):
            self.science_status.setText(i18n("sci_packet", n=request_no, detail=detail))

    def _on_science_finished(self, mode: str, ok: int, total: int) -> None:
        self._log(key="science_done", mode=mode, ok=ok, total=total)
        self._set_status(i18n("science_done", mode=mode, ok=ok, total=total))
        if mode == "played" and self._science_last_ids:
            self.store.mark_played(self._science_last_ids[:ok])
        self._refresh_science_status()

    def _on_science_failed(self, message: str) -> None:
        self._log(key="log_science_err", message=message)
        self._set_status(i18n("status_science_err", message=message))
        self._refresh_science_status()

    def _on_science_status(self, key: str, params: dict | None = None) -> None:
        self._log(key=key, **dict(params or {}))

    def _on_quest_log(self, key: str, params: dict | None = None) -> None:
        self._log(key=key, **dict(params or {}))

    def _on_quest_failed(self, message: str) -> None:
        self._log(key="log_quest_err", message=message)
        self._set_status(i18n("status_quest_err", message=message))

    def _on_quest_finished(self, ok: int, total: int) -> None:
        self._log(key="log_quest_done", ok=ok, total=total)
        self._set_status(i18n("status_quest_done", ok=ok, total=total))
        self.quest_engine.refresh()

    def _on_quest_house(self, house_id: int, name: str) -> None:
        self._set_status(i18n("status_hypesquad", name=name))

    def _on_quest_privacy(self, level: int, name: str) -> None:
        self._set_status(i18n("status_privacy", name=name))

    def _export_profiles(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(
            self, i18n("dialog_export"), str(Path.home() / "ky-gameplayer.json"), "JSON (*.json)"
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.store.dump(), indent=2, ensure_ascii=False), encoding="utf-8")
        self._set_status(i18n("status_exported", path=path))

    def _import_profiles(self) -> None:
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n("dialog_import"), str(Path.home()), "JSON (*.json)"
        )
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, APP_TITLE, i18n("warn_json", exc=exc))
            return
        if not isinstance(payload, dict):
            QMessageBox.warning(self, APP_TITLE, i18n("warn_json_obj"))
            return
        self.store.merge_import(payload)
        self._refresh_profiles()
        self._restore_extra_settings()
        self._reload_list()
        self._set_status(i18n("status_imported", path=path))

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
        if hasattr(self, "_save_random_settings"):
            self._save_random_settings()
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

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QWidget { color: #f2f3f5; font-size: 13px; }
            QGroupBox {
                border: 1px solid #3f4147;
                border-radius: 8px;
                margin-top: 12px;
                padding: 10px 8px 8px 8px;
                font-weight: 600;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
            QLineEdit, QComboBox, QSpinBox, QDateTimeEdit, QTextEdit, QListView {
                background: #111214;
                border: 1px solid #3f4147;
                border-radius: 6px;
                padding: 4px 8px;
                selection-background-color: #5865f2;
            }
            QPushButton {
                background: #5865f2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 7px 12px;
                font-weight: 600;
            }
            QPushButton:hover { background: #4752c4; }
            QPushButton:pressed { background: #3c45a5; }
            QLabel#sectionTitle { font-size: 18px; font-weight: 700; }
            QLabel#muted { color: #949ba4; }
            QLabel#statusOn { color: #23a559; font-size: 16px; }
            QLabel#statusOff { color: #da373c; font-size: 16px; }
            QScrollArea { background: transparent; }
            QCheckBox { spacing: 8px; }
            QListWidget { background: #111214; border: 1px solid #3f4147; border-radius: 6px; }
            QFrame#panelBlock {
                background: #111214;
                border: 1px solid #3f4147;
                border-radius: 12px;
                padding: 8px;
            }
            QProgressBar {
                background: #111214;
                border: 1px solid #3f4147;
                border-radius: 7px;
                text-align: center;
                color: #f2f3f5;
            }
            QProgressBar::chunk { background: #5865f2; border-radius: 6px; }
            QTabWidget::pane { border: 1px solid #3f4147; border-radius: 8px; top: -1px; }
            QTabBar::tab {
                background: #2b2d31;
                color: #dbdee1;
                padding: 8px 14px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #5865f2; color: white; }
            """
        )
