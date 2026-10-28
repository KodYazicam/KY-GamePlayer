from __future__ import annotations

from .common import _line



from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..model import GameDelegate
from ..autostart import enabled as autostart_on
from ..brand import APP_TITLE
from ..i18n import t as i18n
from ..panel import Pages
from ..preview import PresencePreview


class LayoutMixin:
    def _build(self) -> None:
        from PySide6.QtWidgets import QStackedWidget

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        self._lock_page = self._build_lock()
        app_page = QWidget()
        root = QVBoxLayout(app_page)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)
        header = QVBoxLayout()
        header.setSpacing(2)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)
        title = QLabel(APP_TITLE)
        title.setObjectName("sectionTitle")
        top_bar.addWidget(title)
        top_bar.addStretch(1)
        self.client_caption = QLabel(i18n("client"))
        self.client_caption.setObjectName("muted")
        self.client_box = QComboBox()
        self.client_box.setMinimumWidth(160)
        self.client_box.setMaximumWidth(260)
        self.client_box.currentIndexChanged.connect(self._on_client_picked)
        self.lang_box = QComboBox()
        self.lang_box.addItem("TR", "tr")
        self.lang_box.addItem("EN", "en")
        self.lang_box.setMinimumWidth(64)
        self.lang_box.currentIndexChanged.connect(self._on_lang_changed)
        self.autostart_box = QCheckBox(i18n("autostart"))
        self.autostart_box.setChecked(autostart_on())
        self.autostart_box.toggled.connect(self._on_autostart)
        top_bar.addWidget(self.client_caption)
        top_bar.addWidget(self.client_box)
        top_bar.addWidget(self.lang_box)
        top_bar.addWidget(self.autostart_box)
        header.addLayout(top_bar)
        self.member_label = QLabel(i18n("member_checking"))
        self.member_label.setObjectName("muted")
        self.member_label.setMinimumWidth(0)
        self.member_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        header.addWidget(self.member_label)
        root.addLayout(header)
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
        self.pages.settings_changed.connect(self._on_setting_changed)
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
        self.splitter = splitter
        saved_sizes = self.store.settings().get("splitter_sizes")
        if isinstance(saved_sizes, list) and len(saved_sizes) == 2:
            try:
                splitter.setSizes([max(80, int(size)) for size in saved_sizes])
            except (TypeError, ValueError):
                pass
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

        fav_row = QGridLayout()
        fav_row.setHorizontalSpacing(6)
        fav_row.setVerticalSpacing(6)
        self.btn_fav = QPushButton(i18n("btn_fav"))
        self.btn_playlist = QPushButton(i18n("btn_playlist"))
        self.btn_exclude = QPushButton(i18n("btn_exclude"))
        self.weight_box = QSpinBox()
        self.weight_box.setRange(1, 20)
        self.weight_box.setValue(1)
        self.weight_box.setPrefix(i18n("weight_prefix"))
        self.weight_box.setMaximumWidth(140)
        for btn in (self.btn_fav, self.btn_playlist, self.btn_exclude):
            btn.setProperty("variant", "ghost")
        self.btn_fav.clicked.connect(self._toggle_favorite)
        self.btn_playlist.clicked.connect(self._toggle_playlist)
        self.btn_exclude.clicked.connect(self._toggle_excluded)
        self.weight_box.valueChanged.connect(self._on_weight_changed)
        fav_row.addWidget(self.btn_fav, 0, 0)
        fav_row.addWidget(self.btn_playlist, 0, 1)
        fav_row.addWidget(self.btn_exclude, 1, 0)
        fav_row.addWidget(self.weight_box, 1, 1)
        fav_row.setColumnStretch(0, 1)
        fav_row.setColumnStretch(1, 1)
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
        for btn in (self.btn_clear, self.btn_disconnect, self.btn_copy, self.btn_export, self.btn_import):
            btn.setProperty("variant", "ghost")
        self.btn_disconnect.setProperty("variant", "danger")
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
        for btn in (self.btn_profile_save, self.btn_profile_load, self.btn_profile_del):
            btn.setProperty("variant", "ghost")
        profiles.addWidget(self.profile_caption)
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
        self.btn_random_now.setProperty("variant", "ghost")
        self.btn_random_now.clicked.connect(self._random_switch)
        self.random_interval.setMaximumWidth(110)
        self.random_norepeat.setMaximumWidth(150)
        random_row.addWidget(self.random_enabled)
        self.random_duration_label = QLabel(i18n("label_duration"))
        random_row.addWidget(self.random_duration_label)
        random_row.addWidget(self.random_interval)
        random_row.addWidget(self.btn_random_now)
        random_row.addWidget(self.random_countdown, 1)
        layout.addLayout(random_row)

        random_opts = QHBoxLayout()
        random_opts.addWidget(self.random_source, 1)
        random_opts.addWidget(self.random_norepeat)
        layout.addLayout(random_opts)

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
        for btn in (self.btn_pin, self.btn_unpin, self.btn_unpin_all):
            btn.setProperty("variant", "ghost")
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
        detect_row.addStretch(1)
        layout.addLayout(detect_row)

        detect_pick = QHBoxLayout()
        self.detect_box.setMinimumWidth(150)
        detect_pick.addWidget(self.detect_box, 1)
        detect_pick.addWidget(self.btn_detect_now)
        detect_pick.addWidget(self.btn_use_detect)
        layout.addLayout(detect_pick)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
