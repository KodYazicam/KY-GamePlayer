"""Logging setup: bounded files, secret redaction and level control.

Discord credentials must never reach a log file. Messages are redacted before
they are formatted and again before a diagnostics report is assembled, so a
failure in one path cannot leak a token.
"""

from __future__ import annotations

import logging
import platform
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .brand import APP_NAME
from .paths import log_dir

MAX_BYTES = 2_000_000
BACKUP_COUNT = 3
FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

_AUTH_RE = re.compile(r"(?i)\b(authorization)\b(\s*:\s*)(?:Bearer\s+)?[^\s,;\"'}]+")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
_TOKEN_RE = re.compile(
    r"\b(?:mfa\.[A-Za-z0-9_-]{80,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{25,})"
)
_SECRET_PAIR_RE = re.compile(
    r"(?i)\b(token|access_token|refresh_token|cookie|authorization|password|secret|"
    r"fingerprint|analytics_token)\b(\s*[=:]\s*)([\"']?)[^\s,;\"'}]+"
)

_log_path: Path | None = None


def redact(text: str) -> str:
    """Mask token-shaped strings and ``key=value`` credentials."""
    if not text:
        return text
    text = _AUTH_RE.sub(r"\1\2[redacted]", text)
    text = _BEARER_RE.sub("Bearer [redacted]", text)
    text = _TOKEN_RE.sub("[redacted]", text)
    text = _SECRET_PAIR_RE.sub(r"\1\2\3[redacted]", text)
    return text


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(
    path: Path | None = None,
    level: int | str = logging.INFO,
    *,
    console: bool = True,
) -> Path:
    """Install rotating, redacting handlers on the root logger."""
    global _log_path
    target = path or (log_dir() / "kodyazar.log")
    target.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass

    formatter = RedactingFormatter(FORMAT)
    file_handler = RotatingFileHandler(
        target,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    handlers: list[logging.Handler] = [file_handler]
    if console:
        handlers.append(logging.StreamHandler(sys.stderr))
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.setLevel(level)
        root.addHandler(handler)
    root.setLevel(level)
    _log_path = target
    logging.getLogger("kodyazar").info(
        "session start app=%s version=%s python=%s platform=%s",
        APP_NAME,
        _version(),
        platform.python_version(),
        platform.platform(),
    )
    return target


def current_log_path() -> Path | None:
    return _log_path


def apply_level(level: int | str) -> None:
    """Apply a configured level to the root logger *and* its handlers."""
    root = logging.getLogger()
    try:
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        root.setLevel(level)
        for handler in root.handlers:
            handler.setLevel(level)
    except (TypeError, ValueError):
        return


def _version() -> str:
    from . import __version__

    return __version__
