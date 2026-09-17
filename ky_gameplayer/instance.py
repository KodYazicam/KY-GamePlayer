from __future__ import annotations

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

LOCK_NAME = "kodyazar-client-lock"


def claim(app: QApplication) -> QLocalServer | None:
    probe = QLocalSocket()
    probe.connectToServer(LOCK_NAME)
    if probe.waitForConnected(150):
        probe.write(b"raise")
        probe.waitForBytesWritten(150)
        probe.disconnectFromServer()
        return None
    QLocalServer.removeServer(LOCK_NAME)
    server = QLocalServer(app)
    if not server.listen(LOCK_NAME):
        QLocalServer.removeServer(LOCK_NAME)
        if not server.listen(LOCK_NAME):
            return None
    return server


def wire(server: QLocalServer, on_raise) -> None:
    def _incoming() -> None:
        sock = server.nextPendingConnection()
        if sock is None:
            return
        sock.readyRead.connect(lambda: None)
        sock.disconnected.connect(sock.deleteLater)
        on_raise()

    server.newConnection.connect(_incoming)
