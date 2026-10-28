from __future__ import annotations

from .common import _line

import os


from PySide6.QtCore import QDateTime, QTime, QTimeZone, Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
)

from ..activity import (
    ACTIVITY_FLAGS,
    ACTIVITY_TYPES,
    PARTY_PRIVACY,
    STATUS_DISPLAY_TYPES,
    ActivityConfig,
)
from ..i18n import t as i18n
from ..httputil import rate_limit_stats


class FormsMixin:
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
        self.template_box = QCheckBox(i18n("template_use"))
        self.template_box.setChecked(True)
        self.template_box.setToolTip(i18n("template_use_tip"))
        self.btn_template_save = QPushButton(i18n("btn_template_save"))
        self.btn_listening = QPushButton(i18n("btn_listening"))
        self.btn_hook = QPushButton(i18n("btn_hook"))
        self.btn_template_save.clicked.connect(self._save_game_template)
        self.btn_listening.clicked.connect(self._listening_helper)
        self.btn_hook.clicked.connect(self._load_hook)
        for widget in (
            self.app_id,
            self.activity_name,
            self.activity_type,
            self.status_display,
            self.stream_url,
            self.pid,
            self.auto_assets,
            self.template_box,
        ):
            self._watch(widget)
        self.app_id.editingFinished.connect(self._on_app_id_entered)
        grid.addRow(i18n("row_app_id"), self.app_id)
        grid.addRow(i18n("row_activity_name"), self.activity_name)
        grid.addRow("", self.auto_assets)
        return box

    def _identity_advanced_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_identity_advanced"))
        self.grp_identity_advanced = box
        grid = QFormLayout(box)
        grid.addRow(i18n("row_type"), self.activity_type)
        grid.addRow(i18n("row_status_display"), self.status_display)
        grid.addRow(i18n("row_stream"), self.stream_url)
        pid_row = QHBoxLayout()
        pid_row.addWidget(self.pid)
        pid_row.addWidget(self.pid_box, 1)
        pid_row.addWidget(self.btn_pid_refresh)
        pid_row.addWidget(self.btn_pid_self)
        grid.addRow("PID", pid_row)
        grid.addRow("", self.template_box)
        helper_row = QHBoxLayout()
        helper_row.addWidget(self.btn_template_save)
        helper_row.addWidget(self.btn_listening)
        helper_row.addWidget(self.btn_hook)
        grid.addRow("", helper_row)
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
        grid.addRow(i18n("row_state"), self.state)
        return box

    def _text_advanced_group(self) -> QGroupBox:
        box = QGroupBox(i18n("grp_text_advanced"))
        self.grp_text_advanced = box
        grid = QFormLayout(box)
        grid.addRow(i18n("row_details_url"), self.details_url)
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
        self.science_dry_run = QCheckBox(i18n("science_dry_run"))
        self.science_dry_run.setToolTip(i18n("science_dry_run_tip"))
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
        self.btn_science_fp_capture = QPushButton(i18n("btn_science_fp_capture"))
        self.btn_science_fp_capture.setToolTip(i18n("btn_science_fp_capture_tip"))
        self.btn_science_save.clicked.connect(self._save_science_credentials)
        self.btn_science_refresh.clicked.connect(self.science.refresh_analytics)
        self.btn_science_pull.clicked.connect(self._pull_science_from_client)
        self.btn_science_run.clicked.connect(lambda: self._run_science(reason="manual"))
        self.btn_science_stop.clicked.connect(self.science.stop)
        self.btn_science_import.clicked.connect(self._import_science_state)
        self.btn_science_fp_capture.clicked.connect(self._capture_fingerprint)
        for widget in (
            self.science_enabled,
            self.science_on_random,
            self.science_on_detect,
            self.science_on_current,
            self.science_dry_run,
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
        flags.addWidget(self.science_dry_run)
        creds = QHBoxLayout()
        creds.addWidget(self.btn_science_pull)
        creds.addWidget(self.btn_science_save)
        creds.addWidget(self.btn_science_refresh)
        creds.addWidget(self.btn_science_import)
        creds.addWidget(self.btn_science_fp_capture)
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
        if hasattr(self.pages, "rate_label"):
            stats = rate_limit_stats()
            self.pages.rate_label.setText(
                i18n(
                    "rate_stats",
                    requests=stats["requests"],
                    rate_limited=stats["rate_limited"],
                    retries=stats["retries"],
                )
            )

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
