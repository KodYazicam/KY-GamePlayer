from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

try:  # PySide6 is optional for the Qt-free test suite
    from PySide6.QtCore import Qt
except ImportError as exc:  # pragma: no cover - CI unit matrix
    raise unittest.SkipTest("PySide6 not installed") from exc

from ky_gameplayer import quest_engine as quest_mod
from ky_gameplayer import science_worker as science_mod
from ky_gameplayer.quest_engine import QuestEngine, _QuestWorker
from ky_gameplayer.science_worker import ScienceEngine


def _quest_payload(target: int = 20, value: int = 0, completed_at: str | None = None) -> dict:
    user_status: dict = {
        "enrolledAt": "now",
        "progress": {"PLAY_ON_DESKTOP": {"value": value}},
    }
    if completed_at:
        user_status["completedAt"] = completed_at
    return {
        "quests": [
            {
                "id": "q1",
                "config": {
                    "messages": {"questName": "Play a game"},
                    "taskConfig": {"tasks": {"PLAY_ON_DESKTOP": {"target": target}}},
                    "application": {"id": "app", "icon": "hash"},
                },
                "userStatus": user_status,
            }
        ]
    }


class FakeRest:
    def __init__(self, target: int = 20, step: int = 5) -> None:
        self.target = target
        self.step = step
        self.value = 0
        self.heartbeats = 0
        self.terminals = 0
        self.claims: list[str] = []
        self.enrolled: list[str] = []

    def me(self):
        return 200, {"id": "1", "username": "demo"}

    def quests_me(self):
        return 200, _quest_payload(self.target, self.value)

    def dm_channels(self):
        return 200, []

    def enroll(self, quest_id: str):
        self.enrolled.append(quest_id)
        return 200, {"userStatus": {"enrolledAt": "now", "progress": {"PLAY_ON_DESKTOP": {"value": 0}}}}

    def heartbeat(self, quest_id: str, stream_key: str, terminal: bool = False):
        self.heartbeats += 1
        if terminal:
            self.terminals += 1
            self.value = self.target
            return 200, {}
        self.value = min(self.target, self.value + self.step)
        return 200, {"progress": {"PLAY_ON_DESKTOP": {"value": self.value}}}

    def claim_quest(self, quest_id: str):
        self.claims.append(quest_id)
        return 200, {}


class QuestWorkerTests(unittest.TestCase):
    def _worker(self, rest: FakeRest, *, enroll: bool = False, cancel=lambda: False) -> _QuestWorker:
        return _QuestWorker(rest, None, enroll=enroll, claim=True, cancel=cancel)

    def test_progress_claim_and_finish(self) -> None:
        rest = FakeRest(target=20, step=5)
        worker = self._worker(rest)
        progress: list[tuple] = []
        finished: list[tuple[int, int]] = []
        worker.progress.connect(lambda *args: progress.append(args), Qt.ConnectionType.DirectConnection)
        worker.finished.connect(lambda ok, total: finished.append((ok, total)), Qt.ConnectionType.DirectConnection)
        with mock.patch.object(quest_mod.time, "sleep", lambda *_: None):
            worker.run()
        self.assertEqual(rest.terminals, 1)
        self.assertEqual(rest.claims, ["q1"])
        self.assertEqual(finished, [(1, 1)])
        self.assertTrue(progress)
        self.assertEqual(progress[-1][1:3], (20, 20))

    def test_cancel_stops_the_loop(self) -> None:
        rest = FakeRest(target=1000, step=1)
        state = {"cancel": False}
        worker = self._worker(rest, cancel=lambda: state["cancel"])
        finished: list[tuple[int, int]] = []
        worker.finished.connect(lambda ok, total: finished.append((ok, total)), Qt.ConnectionType.DirectConnection)
        worker.progress.connect(lambda *_: state.update(cancel=True), Qt.ConnectionType.DirectConnection)
        with mock.patch.object(quest_mod.time, "sleep", lambda *_: None):
            worker.run()
        self.assertLessEqual(rest.heartbeats, 2)
        self.assertEqual(rest.claims, [])
        self.assertEqual(finished, [(0, 1)])

    def test_missing_token_is_reported(self) -> None:
        worker = _QuestWorker(None, None, enroll=False, claim=True, cancel=lambda: False)
        failed: list[str] = []
        worker.failed.connect(lambda message: failed.append(message), Qt.ConnectionType.DirectConnection)
        with mock.patch.object(quest_mod, "harvest", return_value=mock.Mock(token="", cookie="")):
            worker.run()
        self.assertEqual(len(failed), 1)

    def test_worker_uses_harvested_token(self) -> None:
        worker = _QuestWorker(None, None, enroll=False, claim=True, cancel=lambda: False)
        auth = mock.Mock(token="tok", cookie="cookie")
        with mock.patch.object(quest_mod, "harvest", return_value=auth), mock.patch.object(
            quest_mod, "DiscordRest", return_value=FakeRest(target=0)
        ) as rest_cls:
            worker.run()
        rest_cls.assert_called_once_with("tok", "cookie")


class QuestEngineAsyncTests(unittest.TestCase):
    def test_refresh_returns_immediately(self) -> None:
        engine = QuestEngine()
        rest = FakeRest()
        waited = threading.Event()
        quests: list[list] = []

        def slow_client():
            time.sleep(0.2)
            return rest

        engine._client = slow_client  # type: ignore[method-assign]
        engine.quests.connect(
            lambda items: (quests.append(items), waited.set()),
            Qt.ConnectionType.DirectConnection,
        )
        started = time.monotonic()
        engine.refresh()
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.1, "refresh() must not block the GUI thread")
        self.assertTrue(waited.wait(2.0))
        self.assertEqual(len(quests[0]), 1)

    def test_second_refresh_is_coalesced(self) -> None:
        engine = QuestEngine()
        calls: list[int] = []
        release = threading.Event()

        def slow_client():
            calls.append(1)
            release.wait(1.0)
            return FakeRest()

        engine._client = slow_client  # type: ignore[method-assign]
        engine.refresh()
        engine.refresh()
        time.sleep(0.05)
        release.set()
        time.sleep(0.2)
        self.assertEqual(len(calls), 1)


class ScienceEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = mock.patch.dict(os.environ, {"KODYAZAR_NO_KEYRING": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.engine = ScienceEngine(Path(self.tmp.name) / "science_state.json")

    def test_harvest_result_updates_last_auth(self) -> None:
        self.engine._on_harvested("tok", "cookie", "fp", "Vesktop")
        assert self.engine.last_auth is not None
        self.assertEqual(self.engine.last_auth.token, "tok")
        self.assertEqual(self.engine.last_auth.cookie, "cookie")
        self.assertEqual(self.engine.last_auth.fingerprint, "fp")
        self.assertEqual(self.engine.last_auth.client, "Vesktop")

    def test_analytics_refresh_is_off_thread(self) -> None:
        self.engine.state.token = "tok"
        done = threading.Event()

        def slow_ensure(*_args, **_kwargs):
            time.sleep(0.2)
            done.set()

        with mock.patch.object(science_mod, "ensure_analytics", slow_ensure):
            started = time.monotonic()
            self.engine.refresh_analytics()
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 0.1, "refresh_analytics() must not block")
            self.assertTrue(done.wait(2.0))


if __name__ == "__main__":
    unittest.main()
