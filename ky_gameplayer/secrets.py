from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import atomic_write, config_dir
from .winutil import dpapi_protect, dpapi_unprotect, is_win


def secrets_path() -> Path:
    return config_dir() / "science_state.json"


def load_mapping(path: Path | None = None) -> dict[str, Any]:
    target = path or secrets_path()
    if not target.exists():
        return {}
    raw = target.read_bytes()
    if raw.startswith(b"KY1\x00"):
        payload = dpapi_unprotect(raw[4:])
        if not payload:
            return {}
        raw = payload
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_mapping(data: dict[str, Any], path: Path | None = None) -> None:
    target = path or secrets_path()
    encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    if is_win():
        protected = dpapi_protect(encoded)
        if protected:
            atomic_write(target, b"KY1\x00" + protected, mode=0o600)
            return
    atomic_write(target, encoded, mode=0o600)
