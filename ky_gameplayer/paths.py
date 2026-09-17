from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        for candidate in (exe_dir, meipass, meipass.parent, exe_dir / "_internal"):
            if (candidate / "games.json").exists() or (candidate / "assets" / "icon.png").exists():
                return candidate
        return exe_dir
    return Path(__file__).resolve().parent.parent


def resource(name: str) -> Path:
    root = app_root()
    path = root / name
    if path.exists():
        return path
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir / name, exe_dir / "_internal" / name, Path(getattr(sys, "_MEIPASS", exe_dir)) / name):
            if candidate.exists():
                return candidate
    return path


def _win() -> bool:
    return sys.platform == "win32"


def config_dir() -> Path:
    if _win():
        root = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return root / "kodyazar"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "kodyazar"
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "kodyazar"


def cache_dir() -> Path:
    if _win():
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return root / "kodyazar"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "kodyazar"
    root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return root / "kodyazar"


def log_dir() -> Path:
    path = cache_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write(path: Path, data: str | bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = data if isinstance(data, bytes) else data.encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        try:
            os.chmod(path, mode)
        except OSError:
            pass
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except TypeError:
            if tmp.exists():
                tmp.unlink()
        raise
