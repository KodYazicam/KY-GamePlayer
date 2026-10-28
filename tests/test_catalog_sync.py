from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from ky_gameplayer.catalog_sync import (
    CatalogError,
    diff_catalogs,
    download_catalog,
    effective_catalog_path,
    restore_backup,
    safe_minimum,
    sync,
    validate_games,
)

ROOT = Path(__file__).resolve().parents[1]


def payload(count: int, name_prefix: str = "Game") -> list[dict]:
    return [{"id": str(1000 + i), "name": f"{name_prefix} {i}"} for i in range(count)]


class ValidateTests(unittest.TestCase):
    def test_accepts_list_with_valid_rows(self) -> None:
        self.assertEqual(validate_games(payload(3), minimum=3), 3)

    def test_counts_only_rows_with_id_and_name(self) -> None:
        rows = payload(3) + [{"id": "9"}, {"name": "NoId"}, "junk"]
        self.assertEqual(validate_games(rows, minimum=3), 3)

    def test_rejects_non_list(self) -> None:
        with self.assertRaises(ValueError):
            validate_games({"id": "1"}, minimum=1)

    def test_rejects_below_minimum(self) -> None:
        with self.assertRaises(ValueError):
            validate_games(payload(3), minimum=10)

    def test_rejects_duplicate_ids(self) -> None:
        with self.assertRaises(CatalogError):
            validate_games(payload(3) + [payload(3)[0]], minimum=1)

    def test_skips_non_numeric_ids(self) -> None:
        rows = payload(3) + [{"id": "not-a-snowflake", "name": "Bad"}]
        self.assertEqual(validate_games(rows, minimum=3), 3)

    def test_sanitises_optional_fields(self) -> None:
        rows = [
            {
                "id": "1",
                "name": "One",
                "executables": ["junk", {"name": "one.exe"}],
                "third_party_skus": ["junk", {"distributor": "steam"}],
                "content_classification": "junk",
                "overlay_methods": "nope",
            }
        ]
        self.assertEqual(validate_games(rows, minimum=1), 1)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            sync(target, rows, minimum=1)
            cleaned = json.loads(target.read_text(encoding="utf-8"))[0]
        self.assertEqual(cleaned["executables"], [{"name": "one.exe"}])
        self.assertEqual(cleaned["third_party_skus"], [{"distributor": "steam"}])
        self.assertNotIn("content_classification", cleaned)
        self.assertEqual(cleaned["overlay_methods"], 0)


class DiffTests(unittest.TestCase):
    def test_counts_added_removed_and_changed(self) -> None:
        old = payload(3)
        new = payload(4)
        new[0]["name"] = "Renamed 0"
        diff = diff_catalogs(old, new)
        self.assertEqual((diff.current, diff.new), (3, 4))
        self.assertEqual(diff.added_count, 1)
        self.assertEqual(diff.removed_count, 0)
        self.assertEqual(diff.changed_count, 1)
        self.assertIn("Game 3", diff.added_examples)

    def test_examples_are_sorted_and_limited(self) -> None:
        old = payload(2)
        new = old + [{"id": "2000", "name": "Zulu"}, {"id": "2001", "name": "Alpha"}]
        diff = diff_catalogs(old, new, examples=1)
        self.assertEqual(diff.added_examples, ("Alpha",))

    def test_removed_examples_are_reported(self) -> None:
        old = payload(3)
        new = payload(1)
        diff = diff_catalogs(old, new)
        self.assertEqual(diff.removed_count, 2)
        self.assertEqual(diff.removed_examples, ("Game 1", "Game 2"))


class SyncTests(unittest.TestCase):
    def test_writes_validated_payload_and_backs_up_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(5, "Old")), encoding="utf-8")

            written, previous = sync(target, payload(7, "New"), minimum=7)
            self.assertEqual((written, previous), (7, 5))

            on_disk = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(len(on_disk), 7)
            self.assertEqual(on_disk[0]["name"], "New 0")

            backup = target.with_name("games.json.bak")
            backed_up = json.loads(backup.read_text(encoding="utf-8"))
            self.assertEqual(backed_up[0]["name"], "Old 0")

    def test_sync_without_existing_target_has_no_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            written, previous = sync(target, payload(4), minimum=4)
            self.assertEqual((written, previous), (4, 0))
            self.assertFalse(target.with_name("games.json.bak").exists())

    def test_sync_refuses_bad_payload_and_keeps_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(5, "Old")), encoding="utf-8")
            with self.assertRaises(ValueError):
                sync(target, [{"id": "1", "name": "x"}], minimum=10)
            self.assertEqual(len(json.loads(target.read_text(encoding="utf-8"))), 5)
            self.assertFalse(target.with_name("games.json.bak").exists())

    def test_shrink_guard_keeps_target_and_does_not_back_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(4000, "Old")), encoding="utf-8")
            with self.assertRaises(CatalogError):
                sync(target, payload(1000, "New"), minimum=1, previous_count=4000)
            self.assertEqual(len(json.loads(target.read_text(encoding="utf-8"))), 4000)
            self.assertFalse(target.with_name("games.json.bak").exists())

    def test_shrink_guard_uses_on_disk_count_when_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(4000, "Old")), encoding="utf-8")
            with self.assertRaises(CatalogError):
                sync(target, payload(1000, "New"), minimum=1)

    def test_first_install_seeds_backup_from_bundled_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            target = base / "user" / "games.json"
            fallback = base / "bundled.json"
            fallback.write_text(json.dumps(payload(3, "Bundled")), encoding="utf-8")
            sync(target, payload(4, "New"), minimum=4, fallback=fallback)
            backup = target.with_name("games.json.bak")
            self.assertTrue(backup.exists())
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8"))[0]["name"], "Bundled 0")

    def test_install_filters_invalid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            rows = payload(4) + [{"id": "x", "name": "Bad"}, {"id": "9"}]
            written, previous = sync(target, rows, minimum=4)
            self.assertEqual((written, previous), (4, 0))
            self.assertEqual(len(json.loads(target.read_text(encoding="utf-8"))), 4)

    def test_restore_returns_to_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(5, "Old")), encoding="utf-8")
            sync(target, payload(7, "New"), minimum=7)

            written, previous = restore_backup(target)
            self.assertEqual((written, previous), (5, 7))
            restored = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(restored[0]["name"], "Old 0")

    def test_restore_without_backup_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            target.write_text(json.dumps(payload(2)), encoding="utf-8")
            with self.assertRaises(CatalogError):
                restore_backup(target)


class EffectivePathTests(unittest.TestCase):
    def test_prefers_user_catalog_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            user = base / "user.json"
            bundled = base / "bundled.json"
            bundled.write_text("[]", encoding="utf-8")
            user.write_text("[]", encoding="utf-8")
            with mock.patch("ky_gameplayer.catalog_sync.bundled_catalog_path", return_value=bundled):
                self.assertEqual(effective_catalog_path(user), user)

    def test_falls_back_to_bundled_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundled = base / "bundled.json"
            bundled.write_text("[]", encoding="utf-8")
            with mock.patch("ky_gameplayer.catalog_sync.bundled_catalog_path", return_value=bundled):
                self.assertEqual(effective_catalog_path(base / "missing.json"), bundled)

    def test_safe_minimum_never_accepts_less_than_half(self) -> None:
        self.assertEqual(safe_minimum(24_000), 12_000)
        self.assertEqual(safe_minimum(0), 10_000)


class _CatalogHandler(BaseHTTPRequestHandler):
    status = 200
    body = b"[]"

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self.send_response(self.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_args) -> None:
        return


@contextmanager
def catalog_server(body: bytes, status: int = 200):
    handler = type("Handler", (_CatalogHandler,), {"body": body, "status": status})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/games.json"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class DownloadTests(unittest.TestCase):
    def test_downloads_and_cleans_catalog(self) -> None:
        body = json.dumps(payload(3) + [{"id": "x", "name": "Bad"}]).encode()
        with catalog_server(body) as url:
            rows = download_catalog(url, timeout=5)
        self.assertEqual(len(rows), 3)

    def test_rejects_http_error(self) -> None:
        with catalog_server(b"nope", status=500) as url:
            with self.assertRaises(CatalogError):
                download_catalog(url, timeout=5)

    def test_rejects_invalid_json(self) -> None:
        with catalog_server(b"not json") as url:
            with self.assertRaises(CatalogError):
                download_catalog(url, timeout=5)

    def test_rejects_oversized_body(self) -> None:
        with catalog_server(b"[" + b" " * 100 + b"]") as url:
            with self.assertRaises(CatalogError):
                download_catalog(url, timeout=5, max_bytes=16)


class CliSmokeTests(unittest.TestCase):
    def test_help_runs_without_qt(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ky_gameplayer.catalog_sync", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("detectables", result.stdout)
        self.assertIn("--check", result.stdout)

    def test_restore_runs_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "games.json"
            backup = target.with_name("games.json.bak")
            target.write_text(json.dumps(payload(2, "New")), encoding="utf-8")
            backup.write_text(json.dumps(payload(3, "Old")), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "ky_gameplayer.catalog_sync", "--restore", "--path", str(target)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("restored 3 games", result.stdout)


if __name__ == "__main__":
    unittest.main()
