from __future__ import annotations

import json
from pathlib import Path


from PySide6.QtCore import QTime
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)

from ..brand import APP_TITLE
from ..i18n import set_lang, t as i18n


class ProfilesMixin:
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

    def _on_setting_changed(self, key: str, value: object) -> None:
        settings = self.store.settings()
        settings[key] = value
        self.store.save()
        if key == "log_level":
            import logging

            logging.getLogger().setLevel(str(value))
        elif key == "lock_timeout":
            self._lock_timeout = max(5, int(value))
        elif key == "harvest_enabled":
            self._harvest_enabled = bool(value)
        self._log(key="log_setting", setting=key, value=str(value))

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
        self.science_dry_run.setChecked(bool(settings.get("science_dry_run")))
        if hasattr(self, "template_box"):
            self.template_box.setChecked(bool(settings.get("use_game_templates", True)))
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
        if hasattr(self.pages, "log_level_box"):
            index = self.pages.log_level_box.findData(str(settings.get("log_level") or "INFO"))
            if index >= 0:
                self.pages.log_level_box.blockSignals(True)
                self.pages.log_level_box.setCurrentIndex(index)
                self.pages.log_level_box.blockSignals(False)
        if hasattr(self.pages, "harvest_box"):
            self.pages.harvest_box.blockSignals(True)
            self.pages.harvest_box.setChecked(bool(settings.get("harvest_enabled", True)))
            self.pages.harvest_box.blockSignals(False)
        if hasattr(self.pages, "lock_timeout"):
            self.pages.lock_timeout.blockSignals(True)
            self.pages.lock_timeout.setValue(max(5, int(settings.get("lock_timeout") or 20)))
            self.pages.lock_timeout.blockSignals(False)

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
        settings["science_dry_run"] = self.science_dry_run.isChecked()
        if hasattr(self, "template_box"):
            settings["use_game_templates"] = self.template_box.isChecked()
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
