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
        # The peer must send the b"raise" token before the window moves, so a
        # local process that merely opened a connection to the lock socket
        # gets nothing. The payload is read on the readyRead signal rather
        # than by blocking the event loop, and buffered, so a token that
        # arrives in pieces still validates once it is whole.
        buffer = bytearray()

        def _read() -> None:
            buffer.extend(sock.readAll())
            if bytes(buffer) == b"raise":
                on_raise()

        sock.readyRead.connect(_read)
        sock.disconnected.connect(sock.deleteLater)

    server.newConnection.connect(_incoming)
