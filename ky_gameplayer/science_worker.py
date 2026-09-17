from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .client_auth import ClientAuth, RunningClient, harvest
from .i18n import t
from .games import Game
from .science import (
    ScienceClient,
    ScienceSession,
    ScienceState,
    ensure_analytics,
    farm,
    science_game_from,
)


class ScienceEngine(QObject):
    progress = Signal(int, int, int, str)
    finished = Signal(str, int, int)
    failed = Signal(str)
    status = Signal(str, dict)
    state_changed = Signal()
    harvested = Signal(str, str, str, str)

    def __init__(self, state_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state_path = state_path
        self.state = ScienceState.load(state_path)
        self._cancel = False
        self._busy = False
        self._thread: QThread | None = None
        self._worker: _FarmWorker | None = None
        self.last_auth: ClientAuth | None = None
        self.preferred: RunningClient | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def reload(self) -> None:
        self.state = ScienceState.load(self.state_path)
        self.state_changed.emit()

    def save_credentials(
        self,
        token: str | None = None,
        cookie: str | None = None,
        fingerprint: str | None = None,
    ) -> None:
        if token is not None:
            self.state.token = token.strip()
        if cookie is not None:
            self.state.cookie = cookie.strip()
        if fingerprint is not None:
            self.state.fingerprint = fingerprint.strip()
        self.state.save(self.state_path)
        self.state_changed.emit()

    def apply_auth(self, auth: ClientAuth) -> None:
        if auth.token:
            self.state.token = auth.token.strip()
        if auth.cookie:
            self.state.cookie = auth.cookie.strip()
        if auth.fingerprint:
            self.state.fingerprint = auth.fingerprint.strip()
        if auth.analytics_token:
            self.state.analytics_token = auth.analytics_token.strip()
            self.state.fetched_at = int(time.time())
        elif auth.token:
            self.state.fetched_at = 0
        self.state.save(self.state_path)
        self.last_auth = auth
        self.state_changed.emit()

    def pull_from_client(self) -> ClientAuth:
        auth = harvest(self.preferred)
        self.last_auth = auth
        if not auth.token and not auth.cookie:
            extra = " · ".join(auth.notes[-3:]) if auth.notes else ""
            self.failed.emit(f"{t('sci_no_auth')}{(' · ' + extra) if extra else ''}")
            self.state_changed.emit()
            return auth
        self.apply_auth(auth)
        who = auth.client or "disk"
        extra = f" uid={auth.user_id}" if auth.user_id else ""
        self.status.emit("sci_got_auth", {"who": who, "extra": extra})
        self.harvested.emit(self.state.token, self.state.cookie, self.state.fingerprint, who)
        return auth

    def refresh_analytics(self) -> None:
        if not self.state.has_token:
            self.failed.emit(t("sci_no_token"))
            return
        try:
            self.state.fetched_at = 0
            ensure_analytics(self.state, self.state_path)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.status.emit("sci_analytics", {})
        self.state_changed.emit()

    def stop(self) -> None:
        self._cancel = True

    def start_farm(
        self,
        games: list[Game],
        hours: float,
        *,
        batch_size: int = 100,
        delay: float = 0.3,
        jitter: float = 0.05,
        extra_delay: tuple[float, float] = (0.5, 1.5),
        mode: str = "playtime",
    ) -> None:
        if self._busy:
            self.failed.emit(t("sci_busy"))
            return
        if not games:
            self.failed.emit(t("sci_no_games"))
            return
        duration_ms = int(max(0.0, hours) * 3600 * 1000)
        if mode == "played" and duration_ms <= 0:
            duration_ms = 60 * 1000
        payload = [science_game_from(game) for game in games]
        self._cancel = False
        self._busy = True
        worker = _FarmWorker(
            state=self.state,
            state_path=self.state_path,
            games=payload,
            duration_ms=duration_ms,
            batch_size=batch_size,
            delay=delay,
            jitter=jitter,
            extra_delay=extra_delay,
            mode=mode,
            cancel=lambda: self._cancel,
            harvest_first=True,
            preferred=self.preferred,
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self.progress)
        worker.status.connect(self.status)
        worker.harvested.connect(self._on_harvested)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(thread.quit)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_harvested(self, token: str, cookie: str, fingerprint: str, label: str) -> None:
        if token:
            self.state.token = token
        if cookie:
            self.state.cookie = cookie
        if fingerprint:
            self.state.fingerprint = fingerprint
        self.last_auth = self.last_auth
        self.harvested.emit(token, cookie, fingerprint, label)
        self.state_changed.emit()

    def _on_failed(self, message: str) -> None:
        self._busy = False
        self.failed.emit(message)
        self.state_changed.emit()

    def _on_finished(self, mode: str, ok: int, total: int) -> None:
        self._busy = False
        self.finished.emit(mode, ok, total)
        self.state_changed.emit()

    def _clear_thread(self) -> None:
        self._thread = None
        self._worker = None


class _FarmWorker(QObject):
    progress = Signal(int, int, int, str)
    finished = Signal(str, int, int)
    failed = Signal(str)
    status = Signal(str, dict)
    harvested = Signal(str, str, str, str)

    def __init__(
        self,
        *,
        state: ScienceState,
        state_path: Path,
        games: list[Any],
        duration_ms: int,
        batch_size: int,
        delay: float,
        jitter: float,
        extra_delay: tuple[float, float],
        mode: str,
        cancel,
        harvest_first: bool = True,
        preferred: RunningClient | None = None,
    ) -> None:
        super().__init__()
        self.state = state
        self.state_path = state_path
        self.games = games
        self.duration_ms = duration_ms
        self.batch_size = batch_size
        self.delay = delay
        self.jitter = jitter
        self.extra_delay = extra_delay
        self.mode = mode
        self.cancel = cancel
        self.harvest_first = harvest_first
        self.preferred = preferred

    @Slot()
    def run(self) -> None:
        try:
            if self.harvest_first:
                auth = harvest(self.preferred)
                if auth.token:
                    self.state.token = auth.token
                if auth.cookie:
                    self.state.cookie = auth.cookie
                if auth.fingerprint:
                    self.state.fingerprint = auth.fingerprint
                if auth.analytics_token:
                    self.state.analytics_token = auth.analytics_token
                    self.state.fetched_at = int(time.time())
                if auth.token or auth.cookie:
                    self.state.save(self.state_path)
                    who = auth.client or "disk"
                    self.status.emit("sci_id_ok", {"who": who})
                    self.harvested.emit(
                        self.state.token,
                        self.state.cookie,
                        self.state.fingerprint,
                        who,
                    )
            if not self.state.token:
                self.failed.emit(t("sci_no_token"))
                return
            ensure_analytics(self.state, self.state_path)
            session = ScienceSession.new()
            client = ScienceClient(self.state, session)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        total = len(self.games)

        def on_batch(request_no: int, sent_ok: int, status: int) -> None:
            if status == 204:
                detail = t("sci_ok_games", ok=sent_ok, total=total)
            elif status in (401, 403):
                detail = t("sci_denied", status=status)
            else:
                detail = t("sci_unexpected", status=status)
            self.progress.emit(request_no, sent_ok, status, detail)

        self.status.emit("sci_started", {"mode": self.mode, "n": total})
        ok = farm(
            client,
            self.games,
            self.duration_ms,
            batch_size=self.batch_size,
            delay=self.delay,
            jitter=self.jitter,
            extra_delay=self.extra_delay,
            cancel=self.cancel,
            on_batch=on_batch,
        )
        self.finished.emit(self.mode, ok, total)
