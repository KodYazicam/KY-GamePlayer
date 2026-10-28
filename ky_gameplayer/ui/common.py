from __future__ import annotations



from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
)

from ..activity import (
    ActivityConfig,
)
from ..games import Game
from ..ipc import DiscordIpc


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
