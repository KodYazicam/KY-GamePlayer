"""Off-thread helpers for the Qt UI layer.

Discord REST calls, credential harvesting and process scans are blocking. Running
them inside a widget slot freezes the whole window until the call returns, which
is what ``TaskRunner`` exists to prevent: work runs on a daemon thread and the
result is delivered back on the GUI thread through a queued signal.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Thread
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal

log = logging.getLogger("kodyazar.ui")


class TaskRunner(QObject):
    """Run blocking callables off the GUI thread.

    Callbacks run on the thread that owns the runner (the GUI thread for widgets).
    A failing job calls ``on_error`` with the exception; a failing callback is
    logged instead of taking the event loop down.
    """

    _done = Signal(int, object)
    _failed = Signal(int, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._seq = 0
        self._jobs: dict[int, tuple[Callable[[Any], None] | None, Callable[[BaseException], None] | None]] = {}
        self._done.connect(self._dispatch_done, Qt.ConnectionType.QueuedConnection)
        self._failed.connect(self._dispatch_failed, Qt.ConnectionType.QueuedConnection)

    def submit(
        self,
        work: Callable[[], Any],
        *,
        on_done: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
        name: str = "task",
    ) -> int:
        """Start ``work`` on a daemon thread and return a job token."""
        self._seq += 1
        token = self._seq
        self._jobs[token] = (on_done, on_error)

        def runner() -> None:
            try:
                result = work()
            except BaseException as exc:  # noqa: BLE001 - forwarded to the UI
                self._failed.emit(token, exc)
                return
            self._done.emit(token, result)

        Thread(target=runner, name=f"ky-{name}", daemon=True).start()
        return token

    def cancel_all(self) -> None:
        """Forget pending callbacks; running threads finish on their own."""
        self._jobs.clear()

    @property
    def pending(self) -> int:
        return len(self._jobs)

    def _dispatch_done(self, token: int, result: Any) -> None:
        handlers = self._jobs.pop(token, None)
        if not handlers or handlers[0] is None:
            return
        try:
            handlers[0](result)
        except Exception:  # noqa: BLE001 - a bad callback must not kill the UI
            log.exception("async callback failed (token=%s)", token)

    def _dispatch_failed(self, token: int, exc: BaseException) -> None:
        handlers = self._jobs.pop(token, None)
        if not handlers or handlers[1] is None:
            log.warning("background task failed without handler: %s", exc)
            return
        try:
            handlers[1](exc)
        except Exception:  # noqa: BLE001
            log.exception("async error handler failed (token=%s)", token)
