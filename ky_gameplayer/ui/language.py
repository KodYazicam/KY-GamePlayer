from __future__ import annotations



from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
)

from ..i18n import set_lang, t as i18n


class LanguageMixin:
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
        self.btn_catalog_update.setToolTip(i18n("catalog_update_tip"))
        self.btn_catalog_restore.setToolTip(i18n("catalog_restore"))
        if not self._catalog_busy:
            self._refresh_catalog_actions()
            self._update_catalog_status()
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
        for value, button in self.scope_buttons.items():
            button.setText(i18n(f"scope_{value}_short"))
            button.setToolTip(i18n(f"scope_{value}"))
        self.btn_filters.setText(i18n("filters"))
        self.btn_clear_filters.setText(i18n("filters_clear"))
        self.btn_details.setText(i18n("details_hide" if self.btn_details.isChecked() else "details_show"))
        self._update_filter_badge()
        self.btn_fav.setText(i18n("btn_fav"))
        self.btn_playlist.setText(i18n("btn_playlist"))
        self.btn_exclude.setText(i18n("btn_exclude"))
        if not self.ipc.connected:
            self.status_label.setText(i18n("status_offline"))
        self.btn_connect.setText(i18n("btn_connect"))
        self.btn_update.setText(i18n("btn_update"))
        self.btn_clear.setText(i18n("btn_clear"))
        self.btn_disconnect.setText(i18n("btn_disconnect"))
        self.btn_more.setToolTip(i18n("more_actions"))
        self.menu_copy.setText(i18n("btn_copy"))
        self.menu_export.setText(i18n("btn_export"))
        self.menu_import.setText(i18n("btn_import"))
        for index, key in enumerate(
            ("subtab_presence", "subtab_advanced", "subtab_automation", "subtab_science", "subtab_log")
        ):
            if index < self.right_tabs.count():
                self.right_tabs.setTabText(index, i18n(key))
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
        self.grp_identity_advanced.setTitle(i18n("grp_identity_advanced"))
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
        self.grp_text_advanced.setTitle(i18n("grp_text_advanced"))
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
        elif self.app_id.text().strip():
            self.selection_name.setText(i18n("custom_app", id=self.app_id.text().strip()))
            self.selection_meta.setText(i18n("custom_app_hint"))
        else:
            self._set_selection_controls(False)
        self._refresh_extra_list()
        self._refresh_random_countdown()
        self._replay_logs()
