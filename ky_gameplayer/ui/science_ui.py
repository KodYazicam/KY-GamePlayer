from __future__ import annotations

import time
from pathlib import Path

from threading import Thread

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from ..activity import (
    listening_config,
)
from ..games import Game
from ..brand import APP_TITLE
from ..client_auth import harvest, list_running_clients
from ..i18n import t as i18n
from ..science import HARD_CAP_GAMES


class ScienceMixin:
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
        dry_run = self.science_dry_run.isChecked()
        confirmed = False
        if not dry_run and len(pool) > HARD_CAP_GAMES:
            answer = QMessageBox.question(
                self,
                APP_TITLE,
                i18n("confirm_science_all", n=len(pool), cap=HARD_CAP_GAMES),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self._log(key="log_science_capped", n=len(pool), cap=HARD_CAP_GAMES)
                self._set_status(i18n("status_science_capped", cap=HARD_CAP_GAMES))
                return
            confirmed = True
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
            dry_run=dry_run,
            confirmed=confirmed,
        )
        self._refresh_science_status()
        if dry_run:
            self._log(key="log_science_dry_run", n=len(pool), reason=reason)
        else:
            self._log(key="log_science_run", mode=mode, n=len(pool), reason=reason)

    def _save_science_credentials(self) -> None:
        self.science.save_credentials(
            self.science_token.text(),
            self.science_cookie.text(),
            self.science_fp.text(),
        )
        self._set_status(i18n("status_science_saved"))

    def _capture_fingerprint(self) -> None:
        """Copy the executable fingerprint from Discord's own disk state."""
        self.btn_science_fp_capture.setEnabled(False)
        self._set_status(i18n("fp_capture_busy"))

        def work() -> None:
            fingerprint = ""
            message = ""
            try:
                from ..client_auth import harvest_fingerprint, known_user_data_dirs

                root = None
                if self._preferred_client is not None and getattr(self._preferred_client, "user_data", None):
                    root = self._preferred_client.user_data
                if root is None:
                    clients = list_running_clients()
                    if clients:
                        root = clients[0].user_data
                if root is None:
                    dirs = known_user_data_dirs()
                    root = dirs[0] if dirs else None
                if root is None:
                    message = i18n("fp_capture_no_client")
                else:
                    fingerprint = harvest_fingerprint(root) or ""
                    message = i18n("fp_capture_ok") if fingerprint else i18n("fp_capture_empty")
            except Exception as exc:  # noqa: BLE001 - surfaced to the user
                message = i18n("fp_capture_fail", exc=exc)

            def done() -> None:
                self.btn_science_fp_capture.setEnabled(True)
                if fingerprint:
                    self.science_fp.setText(fingerprint)
                    self.science.save_credentials(fingerprint=fingerprint)
                self._set_status(message)
                self._log(key="log_fp_capture", message=message)

            QTimer.singleShot(0, done)

        Thread(target=work, daemon=True).start()

    def _save_game_template(self) -> None:
        if self._game is None:
            self._set_status(i18n("status_need_game"))
            return
        self.store.put_game_template(self._game.id, self.collect())
        self._set_status(i18n("status_template_saved", name=self._game.name))
        self._log(key="log_template_saved", name=self._game.name)

    def _listening_helper(self) -> None:
        track, ok = QInputDialog.getText(self, i18n("listening_title"), i18n("listening_track"))
        if not ok or not track.strip():
            return
        artist, ok = QInputDialog.getText(self, i18n("listening_title"), i18n("listening_artist"))
        if not ok:
            return
        album, ok = QInputDialog.getText(self, i18n("listening_title"), i18n("listening_album"))
        if not ok:
            return
        art, ok = QInputDialog.getText(self, i18n("listening_title"), i18n("listening_art"))
        if not ok:
            return
        duration, ok = QInputDialog.getInt(
            self, i18n("listening_title"), i18n("listening_duration"), 210, 0, 36000, 30
        )
        if not ok:
            return
        config = listening_config(
            track,
            artist,
            album=album,
            art_url=art,
            duration_s=int(duration),
            game_id=self.app_id.text().strip(),
        )
        self.apply_config(self.app_id.text().strip(), config)
        self._update_preview()
        self._set_status(i18n("status_listening_applied"))
        self._log(key="log_listening_applied", track=track)

    def _load_hook(self) -> None:
        if not self._require_member():
            return
        path, _filter = QFileDialog.getOpenFileName(
            self, i18n("dialog_hook"), str(Path.home()), "Python (*.py)"
        )
        if not path:
            return
        try:
            from ..hooks import load_hook, run_hook

            config = run_hook(load_hook(path), self._game)
        except ValueError as exc:
            QMessageBox.warning(self, APP_TITLE, i18n("warn_hook", exc=exc))
            return
        if config is None:
            self._set_status(i18n("status_hook_none"))
            return
        self.apply_config(self._game.id if self._game else self.app_id.text().strip(), config)
        self._update_preview()
        self._set_status(i18n("status_hook_applied", path=Path(path).name))
        self._log(key="log_hook_applied", path=Path(path).name)

    def _pull_science_from_client(self, silent: bool = False) -> None:
        if not self._harvest_enabled and not silent:
            self._set_status(i18n("status_harvest_off"))
            self._log(key="log_harvest_off")
            return
        if getattr(self, "_pull_busy", False):
            return
        self._pull_busy = True
        if not silent:
            self._set_status(i18n("status_pulling"))

        def done(auth) -> None:
            self._pull_busy = False
            if auth.token or auth.cookie:
                self.science.apply_auth(auth)
            self.science.last_auth = auth
            self.science_token.setText(self.science.state.token)
            self.science_cookie.setText(self.science.state.cookie)
            if auth.fingerprint:
                self.science_fp.setText(self.science.state.fingerprint)
            self._refresh_science_status()
            if silent:
                return
            if auth.token and auth.cookie:
                self._on_science_harvested(
                    auth.token, auth.cookie, auth.fingerprint, auth.client or "disk"
                )
                who = auth.client or "disk"
                uid = f" uid={auth.user_id}" if auth.user_id else ""
                self._set_status(i18n("status_science_who", who=who, uid=uid))
            else:
                extra = "\n".join(auth.notes[-4:]) if auth.notes else i18n("warn_no_auth")
                QMessageBox.warning(self, APP_TITLE, extra)

        def failed(exc: BaseException) -> None:
            self._pull_busy = False
            self._set_status(i18n("status_science_err", message=exc))
            if not silent:
                QMessageBox.warning(self, APP_TITLE, str(exc))

        self.tasks.submit(
            lambda: harvest(self.science.preferred),
            on_done=done,
            on_error=failed,
            name="harvest",
        )

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
        from ..science import ScienceState

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
        live = self._live_client_cached()
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

    def _live_client_cached(self):
        """Process scans cost ~75 ms; reuse the answer for a few seconds."""
        now = time.monotonic()
        cached = getattr(self, "_live_client_cache", None)
        if cached is not None and now - cached[0] < 5.0:
            return cached[1]
        try:
            clients = list_running_clients()
        except Exception:
            clients = []
        live = clients[0] if clients else None
        self._live_client_cache = (now, live)
        return live

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
