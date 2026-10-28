from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .paths import atomic_write, config_dir
from .winutil import dpapi_protect, dpapi_unprotect, is_win

log = logging.getLogger("kodyazar.secrets")

#: Values that never belong in a world-readable config file.
SENSITIVE_KEYS = frozenset(
    {
        "token",
        "cookie",
        "analytics_token",
        "super_properties",
        "client_uuid",
        "session_id",
    }
)

_KEYRING_SERVICE = "kodyazar-client"
_KEYRING_ACCOUNT = "science_state"


def secrets_path() -> Path:
    return config_dir() / "science_state.json"


def _keyring():
    """Return the ``keyring`` module when a usable backend exists."""
    if os.environ.get("KODYAZAR_NO_KEYRING"):
        return None
    if is_win():
        # Windows already has DPAPI protecting the whole payload.
        return None
    try:
        import keyring

        backend = keyring.get_keyring()
        module = type(backend).__module__
        if "fail" in module or "null" in module:
            return None
        return keyring
    except Exception:
        return None


def _read_file(target: Path) -> dict[str, Any]:
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


def _read_keyring() -> dict[str, Any]:
    kr = _keyring()
    if kr is None:
        return {}
    try:
        raw = kr.get_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT)
    except Exception as exc:  # noqa: BLE001 - backend trouble is not fatal
        log.warning("keyring read failed: %s", exc)
        return {}
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("keyring payload is not JSON; ignoring")
        return {}
    return data if isinstance(data, dict) else {}


def load_mapping(path: Path | None = None) -> dict[str, Any]:
    """Read the science state, preferring the OS secret store for secrets.

    An explicit ``path`` is treated as a portable import file and is read as-is
    (no keyring merge), which keeps export/import predictable.
    """
    if path is not None:
        return _read_file(path)
    data = _read_file(secrets_path())
    stored = _read_keyring()
    if stored:
        data = {**data, **stored}
    elif _keyring() is not None and _split_secrets(data)[0]:
        # One-time migration: move secrets from the plain file into the keyring.
        save_mapping(data)
    return data


def _split_secrets(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    secrets = {key: value for key, value in data.items() if key in SENSITIVE_KEYS and value}
    rest = {key: value for key, value in data.items() if key not in secrets}
    return secrets, rest


def save_mapping(data: dict[str, Any], path: Path | None = None) -> None:
    if path is not None:
        _write_plain(data, path)
        return

    target = secrets_path()
    secrets, rest = _split_secrets(data)
    if is_win():
        _write_encrypted(data, target)
        return

    kr = _keyring()
    if kr is not None and secrets:
        try:
            kr.set_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT, json.dumps(secrets))
        except Exception as exc:  # noqa: BLE001 - fall back to the file
            log.warning("keyring write failed, keeping plain file: %s", exc)
            _write_plain(data, target)
            return
        # Secrets live in the keyring now; the file keeps only non-sensitive values.
        _write_plain(rest, target)
        return

    # No keyring (disabled, missing backend, or Windows DPAPI below): the payload
    # is protected by filesystem permissions (0o600) only.
    _write_plain(data, target)


def _write_encrypted(data: dict[str, Any], target: Path) -> None:
    encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    protected = dpapi_protect(encoded)
    if protected:
        atomic_write(target, b"KY1\x00" + protected, mode=0o600)
        return
    _write_plain(data, target)


def _write_plain(data: dict[str, Any], target: Path) -> None:
    encoded = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    atomic_write(target, encoded, mode=0o600)
