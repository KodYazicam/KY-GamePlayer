from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RunningProcess:
    pid: int
    name: str
    cmdline: str
    exe: str


def _win() -> bool:
    return sys.platform == "win32"


def _basename(path: str) -> str:
    name = path.replace("\\", "/").rstrip("/").split("/")[-1]
    return name.casefold()


def _linux_processes() -> list[RunningProcess]:
    out: list[RunningProcess] = []
    proc = Path("/proc")
    if not proc.exists():
        return out
    self_pid = os.getpid()
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in (0, 1, self_pid):
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        cmdline = ""
        exe = ""
        try:
            raw = (entry / "cmdline").read_bytes().split(b"\x00")
            parts = [p.decode("utf-8", "ignore") for p in raw if p]
            cmdline = " ".join(parts)
        except OSError:
            pass
        try:
            exe = os.readlink(str(entry / "exe"))
        except OSError:
            pass
        out.append(RunningProcess(pid=pid, name=comm, cmdline=cmdline, exe=exe))
    return out


def _win_processes() -> list[RunningProcess]:
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    ProcessCommandLineInformation = 60
    INVALID_HANDLE = int(wintypes.HANDLE(-1).value)

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    ntdll.NtQueryInformationProcess.restype = ctypes.c_long

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if int(snap) in {0, INVALID_HANDLE, -1}:
        return []
    out: list[RunningProcess] = []
    self_pid = os.getpid()
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
    try:
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pid = int(entry.th32ProcessID)
            name = str(entry.szExeFile or "")
            if pid not in (0, 4, self_pid):
                exe = ""
                cmdline = ""
                handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
                if not handle:
                    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                if handle:
                    try:
                        size = wintypes.DWORD(32768)
                        buf = ctypes.create_unicode_buffer(32768)
                        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                            exe = buf.value
                        length = ctypes.c_ulong(0)
                        ntdll.NtQueryInformationProcess(
                            handle, ProcessCommandLineInformation, None, 0, ctypes.byref(length)
                        )
                        if length.value >= 16:
                            blob = (ctypes.c_ubyte * length.value)()
                            status = ntdll.NtQueryInformationProcess(
                                handle, ProcessCommandLineInformation, blob, length, ctypes.byref(length)
                            )
                            if status == 0:
                                raw = bytes(blob)
                                str_len = int.from_bytes(raw[0:2], "little")
                                if 0 < str_len <= length.value:
                                    tail = raw[16 : 16 + str_len]
                                    cmdline = tail.decode("utf-16-le", "ignore").strip("\x00")
                    finally:
                        kernel32.CloseHandle(handle)
                out.append(RunningProcess(pid=pid, name=name, cmdline=cmdline, exe=exe or name))
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return out


def _darwin_processes() -> list[RunningProcess]:
    import subprocess

    out: list[RunningProcess] = []
    self_pid = os.getpid()
    try:
        raw = subprocess.check_output(
            ["ps", "-ax", "-o", "pid=,comm=,args="],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return out
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid in (0, 1, self_pid):
            continue
        name = Path(parts[1]).name
        cmdline = parts[2] if len(parts) > 2 else parts[1]
        out.append(RunningProcess(pid=pid, name=name, cmdline=cmdline, exe=parts[1]))
    return out


def list_processes() -> list[RunningProcess]:
    if _win():
        try:
            return _win_processes()
        except Exception:
            return []
    if sys.platform == "darwin":
        return _darwin_processes()
    return _linux_processes()


def process_names(proc: RunningProcess) -> set[str]:
    names: set[str] = set()
    if proc.name:
        names.add(proc.name.casefold())
        names.add(_basename(proc.name))
    if proc.exe:
        names.add(_basename(proc.exe))
    if proc.cmdline:
        first = proc.cmdline.split()[0] if proc.cmdline.split() else ""
        if first:
            names.add(_basename(first))
        for token in proc.cmdline.replace("\\", "/").split():
            base = _basename(token)
            if base.endswith((".exe", ".bin", ".app", ".so")) or "." not in base:
                if 2 <= len(base) <= 80:
                    names.add(base)
    return {name for name in names if name}
