from __future__ import annotations

import json
import os
import time
from pathlib import Path

from threading import Thread

from .common import MAX_EXTRA_SLOTS, ExtraSlot

from PySide6.QtCore import QTime, QTimer, Qt
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import (
    QListWidgetItem,
    QMessageBox,
)

from ..detect import DetectedGame
from ..games import Game
from ..ipc import discord_ipc_available
from ..brand import APP_TITLE
from ..i18n import t as i18n
from ..processes import list_processes
from ..store import game_store_links, primary_store_button


class PresenceMixin:
    def _connect(self, silent: bool = False) -> None:
        if not silent and not self._require_member():
            return
        app_id = self.app_id.text().strip()
        if not app_id:
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("warn_no_game"))
            return
        if not discord_ipc_available():
            self._log(key="log_no_ipc")
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("msg_no_ipc"))
            if self.auto_reconnect.isChecked() and self._want_connected:
                self._schedule_reconnect()
            return
        if self.ipc.connected and self.ipc.client_id == app_id:
            self._set_status(i18n("status_already", id=app_id))
            return
        if self.ipc.connecting and self.ipc.client_id == app_id:
            return
        self._want_connected = True
        self._set_status(i18n("status_connecting"))
        self._log(key="log_connecting", id=app_id)
        self.ipc.connect(app_id)

    def _disconnect(self) -> None:
        self._want_connected = False
        self._reconnect_tries = 0
        self._stop_reconnect_timer()
        self.ipc.disconnect("user")
        self._log(key="log_disconnected")

    def _update_rpc(self, silent: bool = False) -> None:
        app_id = self.app_id.text().strip()
        if not app_id:
            if not silent:
                QMessageBox.warning(self, APP_TITLE, i18n("warn_no_game"))
            return
        if self.ipc.connecting and self.ipc.client_id == app_id:
            # Do not cancel an in-flight connect: send the activity once READY.
            self._pending_update = True
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

    def _on_ready(self, data: dict) -> None:
        self._stop_reconnect_timer()
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
        if not discord_ipc_available():
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

    def _fill_assets(self, game: Game) -> None:
        self.asset_box.blockSignals(True)
        self.asset_box.clear()
        if game.cover_image_hash:
            self.asset_box.addItem(i18n("asset_cover"), ("cover", game.cover_image_hash, game.cover_url(256)))
        if game.icon_hash:
            self.asset_box.addItem(i18n("asset_icon"), ("icon", game.icon_hash, game.icon_url(128)))
        for dist, _sku, url in game_store_links(game):
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
        if not self._want_connected:
            return
        self._reconnect_tries += 1
        delay = min(30, 2 ** min(self._reconnect_tries, 5)) * 1000
        self._log(key="log_reconnect", s=delay // 1000)
        timer = getattr(self, "_reconnect_timer", None)
        if timer is None:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._reconnect_tick)
            self._reconnect_timer = timer
        timer.start(delay)

    def _reconnect_tick(self) -> None:
        if self._want_connected:
            self._connect(silent=True)

    def _stop_reconnect_timer(self) -> None:
        timer = getattr(self, "_reconnect_timer", None)
        if timer is not None:
            timer.stop()

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
