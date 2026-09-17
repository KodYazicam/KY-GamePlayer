from __future__ import annotations

import sys
from pathlib import Path


def is_win() -> bool:
    return sys.platform == "win32"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def enable_dpi() -> None:
    return


def invalid_handle() -> int:
    return 0xFFFFFFFFFFFFFFFF if sys.maxsize > 2**32 else 0xFFFFFFFF


def read_shared(path: Path, limit: int = 16_000_000) -> bytes | None:
    if not path.exists() or not path.is_file():
        return None
    if not is_win():
        try:
            data = path.read_bytes()
        except OSError:
            return None
        return data[:limit]
    import ctypes
    from ctypes import wintypes

    GENERIC_READ = 0x80000000
    FILE_SHARE = 0x00000007
    OPEN_EXISTING = 3
    FILE_ATTRIBUTE_NORMAL = 0x80
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
    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel32.GetFileSizeEx.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.CreateFileW(
        str(path), GENERIC_READ, FILE_SHARE, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
    )
    if not handle or int(handle) in {0, invalid_handle(), -1}:
        try:
            return path.read_bytes()[:limit]
        except OSError:
            return None
    try:
        size = ctypes.c_longlong(0)
        if kernel32.GetFileSizeEx(handle, ctypes.byref(size)):
            n = min(int(size.value), limit)
        else:
            n = min(path.stat().st_size, limit)
        if n <= 0:
            return b""
        buf = ctypes.create_string_buffer(n)
        got = wintypes.DWORD(0)
        ok = kernel32.ReadFile(handle, buf, n, ctypes.byref(got), None)
        if not ok:
            return None
        return buf.raw[: got.value]
    finally:
        kernel32.CloseHandle(handle)


def dpapi_unprotect(blob: bytes) -> bytes | None:
    if not is_win() or not blob:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        buf = ctypes.create_string_buffer(blob)
        inp = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out = DATA_BLOB()
        if not crypt32.CryptUnprotectData(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
            return None
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            kernel32.LocalFree(out.pbData)
    except Exception:
        return None


def dpapi_protect(raw: bytes) -> bytes | None:
    if not is_win() or not raw:
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPCWSTR,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL
        buf = ctypes.create_string_buffer(raw)
        inp = DATA_BLOB(len(raw), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out = DATA_BLOB()
        if not crypt32.CryptProtectData(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
            return None
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            kernel32.LocalFree(out.pbData)
    except Exception:
        return None


def copy_shared(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = read_shared(src)
    if data is None:
        try:
            dest.write_bytes(src.read_bytes())
            return True
        except OSError:
            return False
    try:
        dest.write_bytes(data)
        return True
    except OSError:
        return False
