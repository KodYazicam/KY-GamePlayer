"""Redacted diagnostics report for bug reports.

Nothing in the report is machine-specific beyond the OS/Python versions and the
safe settings listed below. Tokens, cookies, fingerprints and user paths are
removed by :func:`ky_gameplayer.logging_setup.redact`.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .brand import APP_NAME
from .logging_setup import redact

SAFE_SETTINGS = (
    "theme_mode",
    "lang",
    "log_level",
    "auto_reconnect",
    "harvest_enabled",
    "idle_clear",
    "idle_seconds",
    "random_interval",
    "random_norepeat",
    "cycle_interval",
)


def _qt_version() -> str:
    try:
        from PySide6.QtCore import qVersion

        return str(qVersion())
    except Exception:  # pragma: no cover - PySide6 is optional in the core suite
        return "unavailable"


def _safe_settings(settings: dict[str, Any] | None) -> list[str]:
    if not isinstance(settings, dict):
        return []
    lines: list[str] = []
    for key in SAFE_SETTINGS:
        if key not in settings:
            continue
        value = settings[key]
        if isinstance(value, (str, int, float, bool)) or value is None:
            lines.append(f"  {key}: {value}")
    return lines


def tail(path: Path | None, lines: int = 80) -> list[str]:
    if path is None:
        return []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.readlines()
    except OSError:
        return []
    return [line.rstrip("\n") for line in content[-lines:]]


def build_report(
    *,
    log_path: Path | None = None,
    catalog_size: int | None = None,
    settings: dict[str, Any] | None = None,
    recent: Iterable[str] | None = None,
    ipc_available: bool | None = None,
) -> str:
    """Build a copy-pasteable report with all secrets removed."""
    lines = [
        f"{APP_NAME} diagnostics",
        f"version: {__version__}",
        f"python: {sys.version.split()[0]}",
        f"qt: {_qt_version()}",
        f"os: {platform.system()} {platform.release()} ({platform.machine()})",
    ]
    if catalog_size is not None:
        lines.append(f"catalog: {catalog_size} games")
    if ipc_available is not None:
        lines.append(f"discord ipc: {'available' if ipc_available else 'not running'}")
    settings_lines = _safe_settings(settings)
    if settings_lines:
        lines.append("settings:")
        lines.extend(settings_lines)
    recent_lines = [str(line) for line in (recent or []) if str(line).strip()]
    if recent_lines:
        lines.append("recent events:")
        lines.extend(f"  {line}" for line in recent_lines[-40:])
    log_lines = tail(log_path)
    if log_lines:
        lines.append("log tail:")
        lines.extend(f"  {line}" for line in log_lines[-60:])
    return redact("\n".join(lines))
