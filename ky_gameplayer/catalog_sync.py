"""Refresh the game catalog from Discord's detectables CDN.

Roadmap 1.1: ``python -m ky_gameplayer.catalog_sync`` so ``games.json`` can
refresh without a git pull. Katalog yenileme: git pull olmadan games.json
guncelle.

    python -m ky_gameplayer.catalog_sync --check   # rapor ver, yazma
    python -m ky_gameplayer.catalog_sync           # yedek alip yaz

The old file is kept at ``games.json.bak`` before anything is written, and a
payload that does not look like Discord's detectables list is refused.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .httputil import http_request
from .paths import app_root, atomic_write

DETECTABLES_URL = "https://cdn.discordapp.com/detectables/games.json"
MIN_GAMES = 10_000
USER_AGENT = "KodYazar-Client catalog_sync"


def validate_games(payload: Any, minimum: int = MIN_GAMES) -> int:
    """Return the number of usable rows; raise ValueError when the payload
    does not look like a detectables dump worth writing."""
    if not isinstance(payload, list):
        raise ValueError("detectables payload must be a JSON list")
    valid = 0
    for item in payload:
        if not isinstance(item, dict):
            continue
        if not str(item.get("id", "")).strip() or not str(item.get("name", "")).strip():
            continue
        valid += 1
    if valid < minimum:
        raise ValueError(f"only {valid} valid games (< {minimum}); refusing to write")
    return valid


def _count_games(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, list):
        return 0
    return sum(1 for item in payload if isinstance(item, dict) and item.get("id") and item.get("name"))


def sync(
    target: Path, payload: list[dict], backup: bool = True, minimum: int = MIN_GAMES
) -> tuple[int, int]:
    """Write `payload` to `target` (after validating it). Returns
    (written, previous). The previous file is copied to `<target>.bak`."""
    written = validate_games(payload, minimum=minimum)
    previous = _count_games(target)
    if backup and target.exists():
        shutil.copy2(target, target.with_name(target.name + ".bak"))
    atomic_write(
        target, json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    )
    return written, previous


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m ky_gameplayer.catalog_sync",
        description="Refresh games.json from Discord's detectables CDN.",
    )
    parser.add_argument("--url", default=DETECTABLES_URL, help="detectables JSON URL")
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="games.json to write (default: the app's catalog next to the package)",
    )
    parser.add_argument("--check", action="store_true", help="report counts only; write nothing")
    parser.add_argument("--no-backup", action="store_true", help="do not keep games.json.bak")
    args = parser.parse_args(argv)

    target = args.path if args.path is not None else app_root() / "games.json"
    status, payload, _headers = http_request(
        "GET", args.url, headers={"User-Agent": USER_AGENT}, timeout=60
    )
    if status != 200 or payload is None:
        message = payload.get("message", "") if isinstance(payload, dict) else ""
        print(f"download failed: HTTP {status} {message}".strip(), file=sys.stderr)
        return 1
    try:
        valid = validate_games(payload)
    except ValueError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print(f"cdn: {valid} games; local: {_count_games(target)} games; nothing written")
        return 0

    written, previous = sync(target, payload, backup=not args.no_backup)
    print(f"wrote {written} games to {target} (was {previous})")
    if not args.no_backup and previous:
        print(f"backup: {target}.bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
