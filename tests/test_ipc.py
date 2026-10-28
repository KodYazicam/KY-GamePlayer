from __future__ import annotations

import json
import socket
import sys
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

try:  # PySide6 is optional for the Qt-free test suite
    from PySide6.QtCore import Qt
except ImportError as exc:  # pragma: no cover - CI unit matrix
    raise unittest.SkipTest("PySide6 not installed") from exc

from ky_gameplayer import ipc as ipc_mod
from ky_gameplayer.ipc import (
    OP_CLOSE,
    OP_FRAME,
    OP_PING,
    OP_PONG,
    DiscordIpc,
    discord_ipc_available,
    find_discord_ipc,
)


def _frame(opcode: int, payload: dict | None) -> bytes:
    body = json.dumps(payload or {}).encode("utf-8")
    return struct.pack("<II", opcode, len(body)) + body


class FakeTransport:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = list(chunks)
        self.pending = b""
        self.sent: list[bytes] = []
        self.closed = False
        self.on_empty = None

    def sendall(self, data: bytes) -> None:
        self.sent.append(bytes(data))

    def recv(self, size: int) -> bytes:
        if not self.pending:
            if not self.chunks:
                if self.on_empty is not None:
                    self.on_empty()
                raise socket.timeout
            self.pending = self.chunks.pop(0)
        data, self.pending = self.pending[:size], self.pending[size:]
        return data

    def settimeout(self, value: float | None) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    def shutdown(self) -> None:
        self.closed = True


def _ops(transport: FakeTransport) -> list[int]:
    ops: list[int] = []
    for packet in transport.sent:
        if len(packet) >= 8:
            ops.append(struct.unpack("<II", packet[:8])[0])
    return ops


class IpcPresenceTests(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "AF_UNIX sockets are not used on Windows")
    def test_unix_socket_is_detected_without_connecting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "discord-ipc-0"
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(path))
            try:
                with mock.patch.object(ipc_mod, "_win", return_value=False), mock.patch.object(
                    ipc_mod, "discord_ipc_candidates", return_value=[str(path)]
                ):
                    self.assertEqual(find_discord_ipc(), str(path))
                    self.assertTrue(discord_ipc_available())
            finally:
                server.close()

    def test_missing_socket_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = str(Path(tmp) / "discord-ipc-0")
            with mock.patch.object(ipc_mod, "_win", return_value=False), mock.patch.object(
                ipc_mod, "discord_ipc_candidates", return_value=[missing]
            ):
                self.assertIsNone(find_discord_ipc())
                self.assertFalse(discord_ipc_available())


class IpcLoopTests(unittest.TestCase):
    def _run(self, frames: list[bytes]) -> tuple[DiscordIpc, FakeTransport, list, list, list]:
        client = DiscordIpc()
        transport = FakeTransport(frames)
        client._sock = transport
        client._running = True
        client._generation = 0
        ready: list[dict] = []
        failed: list[str] = []
        frames_seen: list[dict] = []
        client.ready.connect(lambda data: ready.append(data), Qt.ConnectionType.DirectConnection)
        client.failed.connect(lambda message: failed.append(message), Qt.ConnectionType.DirectConnection)
        client.frame.connect(lambda data: frames_seen.append(data), Qt.ConnectionType.DirectConnection)
        transport.on_empty = lambda: setattr(client, "_running", False)
        thread = threading.Thread(target=client._loop, args=(0,), daemon=True)
        thread.start()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        return client, transport, ready, failed, frames_seen

    def test_ready_and_frame_are_parsed(self) -> None:
        ready_payload = {"evt": "READY", "data": {"user": {"username": "demo"}}}
        frame_payload = {"cmd": "SET_ACTIVITY", "evt": None, "nonce": "n1"}
        _client, _transport, ready, failed, frames_seen = self._run(
            [_frame(OP_FRAME, ready_payload) + _frame(OP_FRAME, frame_payload)]
        )
        self.assertEqual(ready[0]["user"]["username"], "demo")
        self.assertEqual(frames_seen[0]["nonce"], "n1")
        self.assertEqual(failed, [])

    def test_partial_reads_are_reassembled(self) -> None:
        packet = _frame(OP_FRAME, {"evt": "READY", "data": {"user": {"username": "split"}}})
        chunks = [packet[:3], packet[3:9], packet[9:]]
        _client, _transport, ready, failed, _frames = self._run(chunks)
        self.assertEqual(ready, [{"user": {"username": "split"}}])
        self.assertEqual(failed, [])

    def test_ping_is_answered_with_pong(self) -> None:
        _client, transport, _ready, failed, _frames = self._run(
            [_frame(OP_PING, {"nonce": "abc"})]
        )
        self.assertEqual(_ops(transport), [OP_PONG])
        self.assertEqual(failed, [])

    def test_close_frame_reports_reason(self) -> None:
        _client, _transport, _ready, failed, _frames = self._run(
            [_frame(OP_CLOSE, {"message": "discord closed"})]
        )
        self.assertEqual(len(failed), 1)
        self.assertIn("discord closed", failed[0])

    def test_oversized_frame_is_rejected(self) -> None:
        header = struct.pack("<II", OP_FRAME, 32 * 1024 * 1024)
        _client, _transport, _ready, failed, _frames = self._run([header])
        self.assertEqual(len(failed), 1)


class IpcLifecycleTests(unittest.TestCase):
    def test_connect_is_asynchronous(self) -> None:
        client = DiscordIpc()
        waited = threading.Event()
        failed: list[str] = []
        client.failed.connect(
            lambda message: (failed.append(message), waited.set()),
            Qt.ConnectionType.DirectConnection,
        )
        with mock.patch.object(ipc_mod, "open_discord_ipc", return_value=None):
            started = time.monotonic()
            client.connect("123")
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 0.1, "connect() must not block the caller")
            self.assertTrue(waited.wait(1.0))
        self.assertTrue(failed)
        self.assertFalse(client.connecting)

    def test_disconnect_cancels_an_in_flight_open(self) -> None:
        client = DiscordIpc()
        transport = FakeTransport([])

        def slow_open(timeout: float = 0.4):
            time.sleep(0.3)
            return "/tmp/discord-ipc-0", transport

        with mock.patch.object(ipc_mod, "open_discord_ipc", side_effect=slow_open):
            client.connect("123")
            time.sleep(0.05)
            started = time.monotonic()
            client.disconnect(reason="", emit=False)
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 0.1, "disconnect() must not wait for the open timeout")
            time.sleep(0.4)
        self.assertTrue(transport.closed)
        self.assertEqual(transport.sent, [])
        self.assertFalse(client.connecting)
        self.assertFalse(client.connected)


if __name__ == "__main__":
    unittest.main()
