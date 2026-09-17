from __future__ import annotations

import json
import os
import socket
import struct
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

from PySide6.QtCore import QObject, Signal

from .i18n import t


OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4


def _win() -> bool:
    return sys.platform == "win32"


class IpcTransport(Protocol):
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def settimeout(self, value: float | None) -> None: ...
    def close(self) -> None: ...
    def shutdown(self) -> None: ...


class SocketTransport:
    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock

    def sendall(self, data: bytes) -> None:
        self._sock.sendall(data)

    def recv(self, size: int) -> bytes:
        return self._sock.recv(size)

    def settimeout(self, value: float | None) -> None:
        self._sock.settimeout(value)

    def close(self) -> None:
        self._sock.close()

    def shutdown(self) -> None:
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


class WinPipeTransport:
    def __init__(self, handle: int) -> None:
        import ctypes
        from ctypes import wintypes

        self._handle = handle
        self._timeout = 1000
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        self._kernel32.WriteFile.restype = wintypes.BOOL
        self._kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        self._kernel32.ReadFile.restype = wintypes.BOOL
        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL
        self._kernel32.SetNamedPipeHandleState.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._kernel32.SetNamedPipeHandleState.restype = wintypes.BOOL
        self._kernel32.PeekNamedPipe.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        self._kernel32.PeekNamedPipe.restype = wintypes.BOOL
        self._kernel32.Sleep.argtypes = [wintypes.DWORD]
        mode = wintypes.DWORD(0)
        self._kernel32.SetNamedPipeHandleState(self._handle, ctypes.byref(mode), None, None)

    def sendall(self, data: bytes) -> None:
        import ctypes
        from ctypes import wintypes

        offset = 0
        raw = bytes(data)
        while offset < len(raw):
            chunk = raw[offset:]
            buf = ctypes.create_string_buffer(chunk, len(chunk))
            written = wintypes.DWORD(0)
            ok = self._kernel32.WriteFile(self._handle, buf, len(chunk), ctypes.byref(written), None)
            if not ok or written.value == 0:
                raise OSError("named pipe write failed")
            offset += written.value

    def recv(self, size: int) -> bytes:
        import ctypes
        from ctypes import wintypes

        if size <= 0:
            return b""
        deadline = time.monotonic() + max(0.05, self._timeout / 1000)
        while time.monotonic() < deadline:
            avail = wintypes.DWORD(0)
            ok_peek = self._kernel32.PeekNamedPipe(self._handle, None, 0, None, ctypes.byref(avail), None)
            if not ok_peek:
                err = ctypes.get_last_error()
                if err in (109, 232, 233):
                    return b""
                raise OSError(err)
            if avail.value == 0:
                self._kernel32.Sleep(15)
                continue
            want = min(size, int(avail.value))
            buf = ctypes.create_string_buffer(want)
            read = wintypes.DWORD(0)
            ok = self._kernel32.ReadFile(self._handle, buf, want, ctypes.byref(read), None)
            if not ok:
                err = ctypes.get_last_error()
                if err in (109, 232, 233):
                    return b""
                raise OSError(err)
            return buf.raw[: read.value]
        raise TimeoutError("named pipe read timeout")

    def settimeout(self, value: float | None) -> None:
        self._timeout = int((value or 1) * 1000)

    def close(self) -> None:
        if self._handle:
            self._kernel32.CloseHandle(self._handle)
            self._handle = 0

    def shutdown(self) -> None:
        self.close()


def discord_ipc_candidates() -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    if _win():
        for index in range(10):
            path = rf"\\.\pipe\discord-ipc-{index}"
            if path not in seen:
                seen.add(path)
                paths.append(path)
        return paths
    bases: list[Path] = []
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        root = Path(runtime)
        bases.extend(
            [
                root,
                root / "app" / "com.discordapp.Discord",
                root / "app" / "com.discordapp.DiscordCanary",
                root / "app" / "com.discordapp.DiscordPTB",
                root / "app" / "dev.vencord.Vesktop",
                root / "snap.discord",
                root / "snap.discord-canary",
            ]
        )
    tmp = os.environ.get("TMPDIR") or "/tmp"
    bases.append(Path(tmp))
    bases.append(Path("/tmp"))
    if sys.platform == "darwin":
        bases.extend(
            [
                Path.home() / "Library" / "Application Support" / "discord",
                Path("/var/tmp"),
            ]
        )
    for base in bases:
        for index in range(10):
            path = str(base / f"discord-ipc-{index}")
            if path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def _try_unix(path: str, timeout: float) -> SocketTransport | None:
    af_unix = getattr(socket, "AF_UNIX", None)
    if af_unix is None:
        return None
    sock = None
    try:
        sock = socket.socket(af_unix, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect(path)
        sock.settimeout(1)
        return SocketTransport(sock)
    except Exception:
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass
        return None


def _try_win_pipe(path: str, timeout: float) -> WinPipeTransport | None:
    import ctypes
    from ctypes import wintypes

    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
    ERROR_PIPE_BUSY = 231
    INVALID = wintypes.HANDLE(-1).value
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.WaitNamedPipeW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    deadline = time.monotonic() + max(0.2, timeout)
    while time.monotonic() < deadline:
        handle = kernel32.CreateFileW(
            path,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if handle and int(handle) not in {0, int(INVALID), -1}:
            return WinPipeTransport(int(handle))
        err = ctypes.get_last_error()
        if err == ERROR_PIPE_BUSY:
            kernel32.WaitNamedPipeW(path, 200)
            continue
        break
    return None


def _win_pipe_present() -> bool:
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
        kernel32.WaitNamedPipeW.restype = wintypes.BOOL
        for path in discord_ipc_candidates():
            if kernel32.WaitNamedPipeW(path, 0):
                return True
            if ctypes.get_last_error() == 231:
                return True
    except Exception:
        return False
    return False


def open_discord_ipc(timeout: float = 0.4) -> tuple[str, IpcTransport] | None:
    if _win():
        try:
            for path in discord_ipc_candidates():
                transport = _try_win_pipe(path, timeout)
                if transport is not None:
                    return path, transport
        except Exception:
            return None
        return None
    for path in discord_ipc_candidates():
        transport = _try_unix(path, timeout)
        if transport is not None:
            return path, transport
    return None


def find_discord_ipc() -> str | None:
    if _win():
        if _win_pipe_present():
            for path in discord_ipc_candidates():
                return path
        return None
    opened = open_discord_ipc()
    if opened is None:
        return None
    path, transport = opened
    try:
        transport.close()
    except OSError:
        pass
    return path


class DiscordIpc(QObject):
    ready = Signal(dict)
    closed = Signal(str)
    failed = Signal(str)
    frame = Signal(dict)
    status = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._sock: IpcTransport | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._client_id = ""
        self._lock = threading.Lock()
        self._generation = 0

    @property
    def client_id(self) -> str:
        return self._client_id

    @property
    def connected(self) -> bool:
        return self._sock is not None and self._running

    def connect(self, client_id: str) -> None:
        self.disconnect(reason="", emit=False)
        opened = open_discord_ipc(timeout=1.0)
        if opened is None:
            self.failed.emit(t("ipc_missing"))
            return
        path, sock = opened
        self._client_id = str(client_id)
        generation = self._generation
        try:
            sock.settimeout(1)
        except OSError:
            pass
        self._sock = sock
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, args=(generation,), name="discord-ipc", daemon=True
        )
        self._thread.start()
        self.status.emit(t("ipc_socket", path=path))
        self._send(OP_HANDSHAKE, {"v": 1, "client_id": self._client_id})

    def disconnect(self, reason: str = "disconnected", emit: bool = True) -> None:
        was = self._sock is not None or self._running
        self._generation += 1
        self._running = False
        with self._lock:
            sock = self._sock
            self._sock = None
        if sock is not None:
            try:
                sock.shutdown()
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self._thread = None
        if emit and was and reason:
            self.closed.emit(reason)

    def set_activity(self, pid: int, activity: dict[str, Any] | None) -> str:
        if not self.connected:
            self.failed.emit(t("ipc_not_connected"))
            return ""
        nonce = uuid.uuid4().hex
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": int(pid), "activity": activity},
            "nonce": nonce,
        }
        self._send(OP_FRAME, payload)
        return nonce

    def _send(self, opcode: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        packet = struct.pack("<II", opcode, len(data)) + data
        with self._lock:
            sock = self._sock
            if sock is None:
                return
            try:
                sock.sendall(packet)
            except OSError as exc:
                self.failed.emit(t("ipc_write_fail", exc=exc))
                self._running = False

    def _recv_exact(self, sock: IpcTransport, size: int) -> bytes | None:
        buf = bytearray()
        while len(buf) < size and self._running:
            try:
                chunk = sock.recv(size - len(buf))
            except socket.timeout:
                continue
            except TimeoutError:
                continue
            except OSError:
                return None
            if not chunk:
                return None
            buf.extend(chunk)
        if len(buf) != size:
            return None
        return bytes(buf)

    def _loop(self, generation: int) -> None:
        last_ping = time.monotonic()
        fatal = ""
        ready_at = time.monotonic()
        saw_ready = False
        while self._running:
            sock = self._sock
            if sock is None:
                break
            now = time.monotonic()
            if not saw_ready and now - ready_at > 8:
                fatal = t("ipc_ready_timeout")
                break
            if now - last_ping > 45:
                self._send(OP_PING, {"nonce": uuid.uuid4().hex})
                last_ping = now
            header = self._recv_exact(sock, 8)
            if header is None:
                break
            opcode, length = struct.unpack("<II", header)
            if length > 16 * 1024 * 1024:
                fatal = t("ipc_bad_size")
                break
            body = self._recv_exact(sock, length) if length else b"{}"
            if body is None:
                break
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except json.JSONDecodeError:
                continue
            if opcode == OP_PING:
                self._send(OP_PONG, payload if isinstance(payload, dict) else {})
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_CLOSE:
                message = ""
                if isinstance(payload, dict):
                    message = str(payload.get("message") or payload.get("data") or payload)
                fatal = t("ipc_closed", message=message)
                break
            if opcode != OP_FRAME or not isinstance(payload, dict):
                continue
            if payload.get("evt") == "READY":
                saw_ready = True
                data = payload.get("data") or {}
                self.ready.emit(data if isinstance(data, dict) else payload)
                continue
            self.frame.emit(payload)
        self._running = False
        with self._lock:
            sock = self._sock
            self._sock = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        if generation != self._generation:
            return
        if fatal:
            self.failed.emit(fatal)
        else:
            self.closed.emit("ipc-loop-end")
