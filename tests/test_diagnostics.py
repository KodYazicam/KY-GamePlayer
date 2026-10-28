from __future__ import annotations

import logging
import tempfile
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ky_gameplayer import __version__
from ky_gameplayer.diagnostics import build_report, tail
from ky_gameplayer.logging_setup import (
    BACKUP_COUNT,
    MAX_BYTES,
    RedactingFormatter,
    apply_level,
    redact,
    setup_logging,
)


def _user_token() -> str:
    return "A" * 24 + "." + "B" * 6 + "." + "C" * 27


class RedactionTests(unittest.TestCase):
    def test_user_and_mfa_tokens_are_masked(self) -> None:
        token = _user_token()
        mfa = "mfa." + "Z" * 90
        text = f"token={token} fallback {mfa}"
        cleaned = redact(text)
        self.assertNotIn(token, cleaned)
        self.assertNotIn(mfa, cleaned)
        self.assertEqual(cleaned.count("[redacted]"), 2)

    def test_key_value_and_bearer_secrets_are_masked(self) -> None:
        cleaned = redact(
            "cookie=abc123def456 Authorization: Bearer abcdef0123456789 "
            'fingerprint="deadbeef" password: hunter2'
        )
        for secret in ("abc123def456", "abcdef0123456789", "deadbeef", "hunter2"):
            self.assertNotIn(secret, cleaned)
        self.assertIn("Authorization: [redacted]", cleaned)

    def test_plain_text_is_unchanged(self) -> None:
        self.assertEqual(redact("connected to Discord in 42 ms"), "connected to Discord in 42 ms")
        self.assertEqual(redact(""), "")

    def test_formatter_masks_record_arguments(self) -> None:
        token = _user_token()
        record = logging.LogRecord(
            "kodyazar.test", logging.INFO, __file__, 1, "harvested %s", (token,), None
        )
        text = RedactingFormatter("%(message)s").format(record)
        self.assertNotIn(token, text)


class HandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "app.log"
        self.root = logging.getLogger()
        self._old_handlers = list(self.root.handlers)
        self._old_level = self.root.level

    def tearDown(self) -> None:
        for handler in list(self.root.handlers):
            if handler not in self._old_handlers:
                self.root.removeHandler(handler)
                handler.close()
        for handler in self._old_handlers:
            if handler not in self.root.handlers:
                self.root.addHandler(handler)
        self.root.setLevel(self._old_level)

    def test_rotation_is_bounded(self) -> None:
        setup_logging(self.path, logging.INFO, console=False)
        handlers = [h for h in self.root.handlers if isinstance(h, RotatingFileHandler)]
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0].maxBytes, MAX_BYTES)
        self.assertEqual(handlers[0].backupCount, BACKUP_COUNT)
        self.assertLessEqual(MAX_BYTES * (BACKUP_COUNT + 1), 8_000_000)

    def test_file_output_is_redacted_and_level_applies_to_handlers(self) -> None:
        setup_logging(self.path, logging.INFO, console=False)
        token = _user_token()
        logging.getLogger("kodyazar.test").warning("harvest token=%s cookie=secretcookie", token)
        for handler in self.root.handlers:
            handler.flush()
        content = self.path.read_text(encoding="utf-8")
        self.assertNotIn(token, content)
        self.assertNotIn("secretcookie", content)

        apply_level("DEBUG")
        self.assertEqual(self.root.level, logging.DEBUG)
        self.assertTrue(all(handler.level == logging.DEBUG for handler in self.root.handlers))

    def test_report_has_version_and_no_secrets(self) -> None:
        token = _user_token()
        self.path.write_text(
            f"2026 INFO cookie={token}\n2026 INFO connected\n", encoding="utf-8"
        )
        report = build_report(
            log_path=self.path,
            catalog_size=24500,
            settings={
                "theme_mode": "light",
                "log_level": "INFO",
                "token": token,
                "cookie": "should-not-appear",
            },
            recent=[f"[12:00] token={token}", "[12:01] connected"],
            ipc_available=True,
        )
        self.assertIn(f"version: {__version__}", report)
        self.assertIn("catalog: 24500 games", report)
        self.assertIn("theme_mode: light", report)
        self.assertIn("discord ipc: available", report)
        self.assertNotIn(token, report)
        self.assertNotIn("should-not-appear", report)

    def test_tail_handles_missing_file(self) -> None:
        self.assertEqual(tail(Path(self.tmp.name) / "missing.log"), [])
        self.assertEqual(tail(None), [])


if __name__ == "__main__":
    unittest.main()
