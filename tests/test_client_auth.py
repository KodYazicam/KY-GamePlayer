from __future__ import annotations

import base64
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ky_gameplayer import client_auth
from ky_gameplayer.client_auth import (
    ClientAuth,
    RunningClient,
    _chrome_key,
    _classify,
    _decode_user_id,
    _decrypt_cookie_value,
    _leveldb_dirs,
    _leveldb_files,
    _looks_like_token,
    _token_score,
    _user_data_from_cmd,
    harvest,
    harvest_cookie,
    harvest_disk_extras,
    harvest_fingerprint,
    harvest_firefox_cookie,
    harvest_token,
    known_browser_dirs,
    known_user_data_dirs,
    list_running_clients,
)


def _token(user_id: str = "123456789012345678") -> str:
    first = base64.b64encode(user_id.encode("ascii")).decode("ascii").rstrip("=")
    return f"{first}.abcdef.{'x' * 32}"


def _make_cookie_db(path: Path, *, encrypted_column: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        if encrypted_column:
            con.execute(
                "create table cookies(host_key text, name text, value text, encrypted_value blob)"
            )
            con.execute(
                "insert into cookies values(?,?,?,?)",
                (".discord.com", "__dcfduid", "discord-cookie", b""),
            )
            con.execute(
                "insert into cookies values(?,?,?,?)",
                ("discord.com", "locale", "tr-TR", b""),
            )
        else:
            con.execute("create table cookies(host_key text, name text, value text)")
            con.execute(
                "insert into cookies values(?,?,?)",
                ("discord.com", "__dcfduid", "plain-cookie"),
            )
        con.commit()
    finally:
        con.close()


def _make_firefox_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.execute("create table moz_cookies(host text, name text, value text)")
        con.execute(
            "insert into moz_cookies values(?,?,?)",
            (".discord.com", "__sdcfduid", "firefox-cookie"),
        )
        con.commit()
    finally:
        con.close()


class HelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home_patch = mock.patch.object(client_auth, "_home", return_value=self.root)
        self.home_patch.start()
        self.env_patch = mock.patch.dict(
            "os.environ",
            {
                "XDG_CONFIG_HOME": str(self.root / ".config"),
                "HOME": str(self.root),
                "USERPROFILE": str(self.root),
                "APPDATA": str(self.root / "AppData" / "Roaming"),
                "LOCALAPPDATA": str(self.root / "AppData" / "Local"),
            },
        )
        self.env_patch.start()
        # Exercise the Linux/XDG discovery branch even on the Windows smoke job.
        self.linux_patch = mock.patch.object(client_auth, "_win", return_value=False)
        self.linux_patch.start()

    def tearDown(self) -> None:
        self.linux_patch.stop()
        self.env_patch.stop()
        self.home_patch.stop()
        self.tmp.cleanup()

    def test_decode_user_id(self) -> None:
        self.assertEqual(_decode_user_id(_token()), "123456789012345678")
        self.assertEqual(_decode_user_id("not-a-token"), "")
        short = base64.b64encode(b"123").decode("ascii").rstrip("=")
        self.assertEqual(_decode_user_id(short + ".abc.def"), "")

    def test_token_score_prefers_context_mfa_and_user_id(self) -> None:
        now = 100.0
        self.assertGreater(
            _token_score(_token(), b"...token...", now),
            _token_score(_token(), b"nothing", now),
        )
        self.assertGreater(_token_score("mfa." + "a" * 90, b"", now), _token_score("x" * 90, b"", now))
        self.assertGreater(_token_score(_token(), b"", now), _token_score("x" * 90, b"", now))

    def test_looks_like_token(self) -> None:
        self.assertTrue(_looks_like_token(_token()))
        self.assertTrue(_looks_like_token("mfa." + "a" * 90))
        self.assertFalse(_looks_like_token("short"))
        self.assertFalse(_looks_like_token("x" * 90))

    def test_user_data_from_cmd(self) -> None:
        session = self.root / "sessionData"
        session.mkdir()
        self.assertEqual(
            _user_data_from_cmd(f'discord --user-data-dir="{self.root}" --foo'),
            session,
        )
        other = self.root / "other"
        other.mkdir()
        self.assertEqual(_user_data_from_cmd(f"discord --user-data-dir={other}"), other)
        missing = self.root / "missing"
        self.assertIsNone(_user_data_from_cmd(f"discord --user-data-dir={missing}"))
        self.assertIsNone(_user_data_from_cmd("discord"))

    def test_classify_process_names(self) -> None:
        self.assertEqual(_classify("Discord.exe"), "discord")
        self.assertEqual(_classify("VencordDesktop"), "vencord")
        self.assertIsNone(_classify("ky_gameplayer --token"))
        self.assertIsNone(_classify("discord --type=renderer"))
        self.assertIsNone(_classify("discord-token"))

    def test_known_user_data_dirs(self) -> None:
        (self.root / ".config" / "vesktop" / "sessionData").mkdir(parents=True)
        (self.root / ".config" / "discord").mkdir(parents=True)
        names = {name for name, _path in known_user_data_dirs()}
        self.assertIn("discord", names)
        self.assertIn("vesktop", names)

    def test_known_browser_dirs(self) -> None:
        chrome = self.root / ".config" / "google-chrome"
        (chrome / "Default").mkdir(parents=True)
        (chrome / "Profile 1").mkdir()
        firefox = self.root / ".mozilla" / "firefox" / "abc.default"
        firefox.mkdir(parents=True)
        (firefox / "cookies.sqlite").touch()
        names = {name for name, _path in known_browser_dirs()}
        self.assertIn("chrome", names)
        self.assertIn("chrome-Default", names)
        self.assertTrue(any(name.startswith("firefox-") for name in names))

    def test_leveldb_and_cookie_directories(self) -> None:
        ldb = self.root / "Local Storage" / "leveldb"
        ldb.mkdir(parents=True)
        (ldb / "000003.log").write_bytes(b"data")
        (ldb / "LOCK").write_bytes(b"")
        self.assertIn(ldb, _leveldb_dirs(self.root))
        self.assertEqual([p.name for p in _leveldb_files(ldb)], ["000003.log"])
        self.assertEqual(_leveldb_files(self.root / "missing"), [])

        cookie = self.root / "Network" / "Cookies"
        cookie.parent.mkdir(parents=True)
        cookie.touch()
        self.assertIn(cookie, client_auth._cookie_dbs(self.root))

    def test_harvest_token_reads_leveldb(self) -> None:
        uid = "123456789012345678"
        token = _token(uid)
        ldb = self.root / "Local Storage" / "leveldb"
        ldb.mkdir(parents=True)
        (ldb / "000003.log").write_bytes(
            b"key token " + token.encode() + b" __analytics__ " + b"a" * 32
        )
        found, analytics = harvest_token(self.root)
        self.assertEqual(found, token)
        self.assertEqual(analytics, "a" * 32)

    def test_harvest_cookie_from_sqlite(self) -> None:
        _make_cookie_db(self.root / "Network" / "Cookies")
        cookie = harvest_cookie(self.root)
        self.assertIn("__dcfduid=discord-cookie", cookie)
        self.assertIn("locale=tr-TR", cookie)

    def test_harvest_cookie_without_encrypted_column(self) -> None:
        _make_cookie_db(self.root / "Network" / "Cookies", encrypted_column=False)
        cookie = harvest_cookie(self.root)
        self.assertIn("__dcfduid=plain-cookie", cookie)

    def test_harvest_firefox_cookie(self) -> None:
        _make_firefox_db(self.root / "cookies.sqlite")
        cookie = harvest_firefox_cookie(self.root)
        self.assertIn("__sdcfduid=firefox-cookie", cookie)
        self.assertEqual(harvest_firefox_cookie(self.root / "missing"), "")

    def test_harvest_fingerprint(self) -> None:
        folder = self.root / "Local Storage" / "leveldb"
        folder.mkdir(parents=True)
        fingerprint = "AbCdEf0123456789+/="
        (folder / "000005.ldb").write_bytes(
            f'executable_fingerprint":"{fingerprint}"'.encode()
        )
        self.assertEqual(harvest_fingerprint(self.root), fingerprint)
        self.assertEqual(harvest_fingerprint(self.root / "missing"), "")

    def test_cookie_value_decryption_paths(self) -> None:
        self.assertEqual(_decrypt_cookie_value("plain", b"", None), "plain")
        self.assertEqual(_decrypt_cookie_value("", b"", None), "")
        self.assertEqual(_decrypt_cookie_value("", b"v20" + b"x" * 20, None), "")
        self.assertEqual(_decrypt_cookie_value("", b"v10" + b"x" * 20, None), "")

    def test_chrome_key(self) -> None:
        state = self.root / "Local State"
        key = b"0123456789abcdef0123456789abcdef"
        encoded = base64.b64encode(b"DPAPI" + key).decode()
        state.write_text(f'{{"os_crypt": {{"encrypted_key": "{encoded}"}}}}', encoding="utf-8")
        with mock.patch.object(client_auth, "_dpapi_unprotect", return_value=key):
            self.assertEqual(_chrome_key(self.root), key)
        state.write_text("{}", encoding="utf-8")
        self.assertIsNone(_chrome_key(self.root))

    def test_harvest_disk_extras(self) -> None:
        auth = ClientAuth()
        with (
            mock.patch.object(
                client_auth, "known_user_data_dirs", return_value=[("firefox-a", self.root)]
            ),
            mock.patch.object(client_auth, "known_browser_dirs", return_value=[]),
            mock.patch.object(client_auth, "harvest_firefox_cookie", return_value="cookie"),
            mock.patch.object(client_auth, "harvest_fingerprint", return_value="fp"),
        ):
            result = harvest_disk_extras(auth)
        self.assertEqual(result.cookie, "cookie")
        self.assertEqual(result.fingerprint, "fp")
        self.assertTrue(any("cookie" in note for note in result.notes))
        complete = ClientAuth(cookie="c", fingerprint="f")
        self.assertIs(harvest_disk_extras(complete), complete)

    def test_harvest_prefers_running_client(self) -> None:
        client = RunningClient(name="vesktop", pid=42, cmd="vesktop", user_data=self.root)
        with (
            mock.patch.object(client_auth, "list_running_clients", return_value=[client]),
            mock.patch.object(client_auth, "_roots_for_client", return_value=[("vesktop", self.root)]),
            mock.patch.object(client_auth, "harvest_token", return_value=(_token(), "analytics")),
            mock.patch.object(client_auth, "harvest_cookie", return_value="cookie"),
            mock.patch.object(client_auth, "harvest_fingerprint", return_value="fp"),
        ):
            auth = harvest()
        self.assertEqual(auth.token, _token())
        self.assertEqual(auth.analytics_token, "analytics")
        self.assertEqual(auth.cookie, "cookie")
        self.assertEqual(auth.fingerprint, "fp")
        self.assertEqual(auth.client, "vesktop")
        self.assertEqual(auth.pid, 42)

    def test_harvest_quick_skips_cookie_and_fingerprint(self) -> None:
        with (
            mock.patch.object(client_auth, "list_running_clients", return_value=[]),
            mock.patch.object(client_auth, "_roots_for_client", return_value=[("discord", self.root)]),
            mock.patch.object(client_auth, "harvest_token", return_value=(_token(), "")),
            mock.patch.object(client_auth, "harvest_cookie") as cookie,
            mock.patch.object(client_auth, "harvest_fingerprint") as fingerprint,
        ):
            auth = harvest(quick=True)
        self.assertEqual(auth.token, _token())
        cookie.assert_not_called()
        fingerprint.assert_not_called()


class ProcessTests(unittest.TestCase):
    def test_clients_from_processes_and_sorting(self) -> None:
        from types import SimpleNamespace

        from ky_gameplayer import ipc as ipc_mod

        process = SimpleNamespace(pid=7, name="Discord", cmdline="discord --flag", exe="/usr/bin/discord")
        with (
            mock.patch.object(client_auth, "list_processes", return_value=[process]),
            mock.patch.object(client_auth, "_pid_has_ipc", return_value=False),
            mock.patch.object(ipc_mod, "find_discord_ipc", return_value=None),
        ):
            clients = client_auth._clients_from_processes()
        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0].name, "discord")
        self.assertEqual(clients[0].pid, 7)

        a = RunningClient(name="vesktop", pid=2, cmd="", user_data=None, ipc=False)
        b = RunningClient(name="discord", pid=1, cmd="", user_data=None, ipc=True)
        with mock.patch.object(client_auth, "_clients_from_processes", return_value=[a, b]):
            ordered = list_running_clients()
        self.assertEqual(ordered, [b, a])

    def test_clients_from_processes_handles_scan_error(self) -> None:
        with mock.patch.object(client_auth, "_clients_from_processes", side_effect=RuntimeError):
            self.assertEqual(list_running_clients(), [])


class RootTests(unittest.TestCase):
    def test_roots_for_client(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            extra = root / "extra"
            extra.mkdir()
            client = RunningClient(name="discord", pid=1, cmd="", user_data=root)
            with (
                mock.patch.object(client_auth, "known_user_data_dirs", return_value=[("discord", extra)]),
                mock.patch.object(client_auth, "known_browser_dirs", return_value=[("chrome", root / "chrome")]),
            ):
                roots = client_auth._roots_for_client(client)
        self.assertEqual(roots[0], ("discord", root))
        self.assertIn(("discord", extra), roots)


if __name__ == "__main__":
    unittest.main()
