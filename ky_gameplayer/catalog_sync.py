"""Refresh the game catalog from Discord's detectables CDN.

The GUI and the CLI share this module. Downloads are size-capped, rows are
validated before anything is written, the previous catalog is kept as a
``.bak`` file and installs go through the atomic writer in :mod:`.paths`.

    python -m ky_gameplayer.catalog_sync --check   # report, write nothing
    python -m ky_gameplayer.catalog_sync           # download + install in the user config
    python -m ky_gameplayer.catalog_sync --restore # restore games.json.bak
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .paths import atomic_write, config_dir, resource

DETECTABLES_URL = "https://cdn.discordapp.com/detectables/games.json"
MIN_GAMES = 10_000
MAX_GAMES = 100_000
MAX_DOWNLOAD_BYTES = 40 * 1024 * 1024
SHRINK_FLOOR = 2_000
USER_AGENT = "KodYazar-Client catalog_sync (+https://github.com/KodYazicam/KY-GamePlayer)"

_ID_RE = re.compile(r"^[0-9]{1,20}$")
_LIST_FIELDS = ("aliases", "themes", "executables", "third_party_skus")
_DICT_LIST_FIELDS = ("executables", "third_party_skus")


class CatalogError(ValueError):
    """Raised when a downloaded or backup catalog is not safe to install."""


@dataclass(frozen=True)
class CatalogDiff:
    current: int
    new: int
    added_count: int
    removed_count: int
    changed_count: int
    added_examples: tuple[str, ...] = ()
    removed_examples: tuple[str, ...] = ()


def bundled_catalog_path() -> Path:
    return resource("games.json")


def user_catalog_path() -> Path:
    return config_dir() / "games.json"


def effective_catalog_path(user_path: Path | None = None) -> Path:
    """Prefer an installed user catalog; otherwise use the bundled one."""
    candidate = user_path or user_catalog_path()
    return candidate if candidate.exists() else bundled_catalog_path()


def backup_path(target: Path) -> Path:
    return target.with_name(target.name + ".bak")


def _clean_rows(payload: Any) -> list[dict]:
    if not isinstance(payload, list):
        raise CatalogError("detectables payload must be a JSON list")
    if len(payload) > MAX_GAMES * 2:
        raise CatalogError(f"catalog has more than {MAX_GAMES} games")
    seen: set[str] = set()
    rows: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        game_id = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not game_id or not name or not _ID_RE.match(game_id):
            continue
        if len(name) > 300:
            continue
        if game_id in seen:
            raise CatalogError(f"duplicate game id: {game_id}")
        seen.add(game_id)
        row = dict(item)
        row["id"] = game_id
        row["name"] = name
        for key in _LIST_FIELDS:
            if key in row and not isinstance(row[key], list):
                row.pop(key)
        for key in _DICT_LIST_FIELDS:
            if key in row:
                row[key] = [entry for entry in row[key] if isinstance(entry, dict)]
        if "content_classification" in row and not isinstance(row["content_classification"], dict):
            row.pop("content_classification")
        try:
            row["overlay_methods"] = int(row.get("overlay_methods") or 0)
        except (TypeError, ValueError):
            row["overlay_methods"] = 0
        rows.append(row)
    if len(rows) > MAX_GAMES:
        raise CatalogError(f"catalog has more than {MAX_GAMES} games")
    return rows


def validate_games(payload: Any, minimum: int = MIN_GAMES) -> int:
    """Return the number of usable rows; raise when the payload is not safe."""
    rows = _clean_rows(payload)
    if len(rows) < minimum:
        raise CatalogError(f"only {len(rows)} valid games (< {minimum}); refusing to write")
    return len(rows)


def safe_minimum(previous_count: int) -> int:
    """Do not accept a catalog that lost more than half of its entries."""
    if previous_count <= 0:
        return MIN_GAMES
    return max(1, previous_count // 2)


def _count_games(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    try:
        return len(_clean_rows(payload))
    except CatalogError:
        return 0


def diff_catalogs(
    old_rows: Iterable[dict],
    new_rows: Iterable[dict],
    examples: int = 5,
) -> CatalogDiff:
    old = {str(row.get("id")): row for row in old_rows if isinstance(row, dict)}
    new = {str(row.get("id")): row for row in new_rows if isinstance(row, dict)}
    added = [new[key] for key in new.keys() - old.keys()]
    removed = [old[key] for key in old.keys() - new.keys()]
    changed = sum(1 for key in old.keys() & new.keys() if old[key] != new[key])
    added.sort(key=lambda row: str(row.get("name") or "").casefold())
    removed.sort(key=lambda row: str(row.get("name") or "").casefold())
    return CatalogDiff(
        current=len(old),
        new=len(new),
        added_count=len(added),
        removed_count=len(removed),
        changed_count=changed,
        added_examples=tuple(str(row.get("name") or row.get("id")) for row in added[:examples]),
        removed_examples=tuple(str(row.get("name") or row.get("id")) for row in removed[:examples]),
    )


def download_catalog(
    url: str = DETECTABLES_URL,
    *,
    timeout: float = 60,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
) -> list[dict]:
    """Download and structurally validate the official catalog (no install)."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if int(response.status) != 200:
                raise CatalogError(f"HTTP {response.status}")
            length = response.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_bytes:
                raise CatalogError(f"catalog is larger than {max_bytes // (1024 * 1024)} MB")
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        code = exc.code
        exc.close()
        raise CatalogError(f"HTTP {code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CatalogError(str(exc)) from exc
    if len(raw) > max_bytes:
        raise CatalogError(f"catalog is larger than {max_bytes // (1024 * 1024)} MB")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CatalogError("catalog is not valid JSON") from exc
    return _clean_rows(payload)


def sync(
    target: Path,
    payload: list[dict],
    backup: bool = True,
    minimum: int = MIN_GAMES,
    previous_count: int | None = None,
    fallback: Path | None = None,
) -> tuple[int, int]:
    """Validate and write ``payload`` to ``target``.

    Returns ``(written, previous)``. The previous file is copied to
    ``<target>.bak`` before the new file replaces it.
    """
    rows = _clean_rows(payload)
    if len(rows) < minimum:
        raise CatalogError(f"only {len(rows)} valid games (< {minimum}); refusing to write")
    previous = previous_count if previous_count is not None else _count_games(target)
    if previous >= SHRINK_FLOOR and len(rows) < previous // 2:
        raise CatalogError("catalog shrank by more than half; refusing to write")
    if backup:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup_path(target))
        elif fallback is not None and fallback.exists() and not backup_path(target).exists():
            # The first update still gets a rollback target: the bundled catalog.
            shutil.copy2(fallback, backup_path(target))
    atomic_write(
        target,
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n",
    )
    return len(rows), previous


def restore_backup(target: Path | None = None) -> tuple[int, int]:
    """Restore ``<target>.bak`` over ``target``. Returns ``(written, previous)``."""
    destination = target or user_catalog_path()
    backup = backup_path(destination)
    if not backup.exists():
        raise CatalogError("no catalog backup found")
    try:
        payload = json.loads(backup.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError("catalog backup is not readable") from exc
    rows = _clean_rows(payload)
    if not rows:
        raise CatalogError("catalog backup has no valid games")
    previous = _count_games(destination)
    atomic_write(
        destination,
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n",
    )
    return len(rows), previous


def catalog_timestamp(path: Path) -> str | None:
    try:
        moment = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return None
    return moment.strftime("%d.%m.%Y %H:%M")


def _cli_target(value: Path | None) -> Path:
    return value if value is not None else user_catalog_path()


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
        help="games.json to write (default: the user config catalog)",
    )
    parser.add_argument("--check", action="store_true", help="report counts only; write nothing")
    parser.add_argument("--no-backup", action="store_true", help="do not keep games.json.bak")
    parser.add_argument("--restore", action="store_true", help="restore games.json.bak and exit")
    args = parser.parse_args(argv)

    target = _cli_target(args.path)
    if args.restore:
        try:
            written, previous = restore_backup(target)
        except CatalogError as exc:
            print(f"restore failed: {exc}", file=sys.stderr)
            return 1
        print(f"restored {written} games to {target} (was {previous})")
        return 0

    local = _count_games(target)
    try:
        payload = download_catalog(args.url)
        valid = validate_games(payload)
    except CatalogError as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        if args.check:
            print(f"local: {local} games", file=sys.stderr)
        return 1

    if args.check:
        print(f"cdn: {valid} games; local: {local} games; nothing written")
        return 0

    try:
        written, previous = sync(
            target,
            payload,
            backup=not args.no_backup,
            minimum=safe_minimum(local),
            previous_count=local,
        )
    except CatalogError as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {written} games to {target} (was {previous})")
    if not args.no_backup and previous:
        print(f"backup: {backup_path(target)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
