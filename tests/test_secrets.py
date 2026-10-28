from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ky_gameplayer import secrets


class FakeKeyring:
    """Minimal stand-in for the ``keyring`` module."""

    def __init__(self, fail: bool = False) -> None:
        self.store: dict[tuple[str, str], str] = {}
        self.fail = fail
        self.writes = 0

    def get_password(self, service: str, account: str) -> str | None:
        if self.fail:
            raise RuntimeError("backend unavailable")
        return self.store.get((service, account))

    def set_password(self, service: str, account: str, value: str) -> None:
        self.writes += 1
        if self.fail:
            raise RuntimeError("backend unavailable")
        self.store[(service, account)] = value


class SecretsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "science_state.json"
        self.keyring = FakeKeyring()
        self.patches = [
            mock.patch.object(secrets, "secrets_path", return_value=self.path),
            mock.patch.object(secrets, "is_win", return_value=False),
            mock.patch.object(secrets, "_keyring", return_value=self.keyring),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self) -> None:
        for patch in self.patches:
            patch.stop()
        self.tmp.cleanup()

    def test_secrets_go_to_keyring_not_disk(self) -> None:
        secrets.save_mapping({"token": "tok", "cookie": "c", "fingerprint": "fp"})

        on_disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("token", on_disk)
        self.assertNotIn("cookie", on_disk)
        self.assertEqual(on_disk["fingerprint"], "fp")
        if os.name != "nt":  # Windows ignores POSIX mode bits
            self.assertEqual(oct(self.path.stat().st_mode & 0o777), "0o600")

        stored = json.loads(self.keyring.store[(secrets._KEYRING_SERVICE, secrets._KEYRING_ACCOUNT)])
        self.assertEqual(stored, {"token": "tok", "cookie": "c"})

    def test_load_merges_file_and_keyring(self) -> None:
        secrets.save_mapping({"token": "tok", "cookie": "c", "fingerprint": "fp"})
        loaded = secrets.load_mapping()
        self.assertEqual(loaded["token"], "tok")
        self.assertEqual(loaded["cookie"], "c")
        self.assertEqual(loaded["fingerprint"], "fp")

    def test_legacy_plaintext_file_is_migrated_on_load(self) -> None:
        legacy = {"token": "old", "cookie": "old-cookie", "fetched_at": 5}
        self.path.write_text(json.dumps(legacy), encoding="utf-8")

        loaded = secrets.load_mapping()

        self.assertEqual(loaded["token"], "old")
        on_disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertNotIn("token", on_disk)
        self.assertNotIn("cookie", on_disk)
        self.assertEqual(on_disk["fetched_at"], 5)

    def test_keyring_failure_falls_back_to_plain_file(self) -> None:
        broken = FakeKeyring(fail=True)
        with mock.patch.object(secrets, "_keyring", return_value=broken):
            secrets.save_mapping({"token": "tok"})
        self.assertEqual(json.loads(self.path.read_text(encoding="utf-8"))["token"], "tok")

    def test_explicit_path_never_touches_keyring(self) -> None:
        portable = Path(self.tmp.name) / "portable.json"
        secrets.save_mapping({"token": "tok"}, portable)
        self.assertEqual(json.loads(portable.read_text(encoding="utf-8"))["token"], "tok")
        self.assertEqual(self.keyring.writes, 0)
        self.assertEqual(secrets.load_mapping(portable)["token"], "tok")
        self.assertEqual(self.keyring.store, {})


class KeyringDetectionTests(unittest.TestCase):
    def test_explicit_disable_wins(self) -> None:
        with mock.patch.dict(os.environ, {"KODYAZAR_NO_KEYRING": "1"}):
            self.assertIsNone(secrets._keyring())

    def test_windows_keeps_dpapi(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(secrets, "is_win", return_value=True):
                self.assertIsNone(secrets._keyring())
