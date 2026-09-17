from __future__ import annotations

import random
import time
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal, Slot

from .client_auth import RunningClient, harvest
from .discord_rest import DiscordRest, QuestTask, parse_quest, parse_quest_list
from .i18n import t


class QuestEngine(QObject):
    log = Signal(str, dict)
    quests = Signal(list)
    progress = Signal(str, int, int, bool)
    finished = Signal(int, int)
    failed = Signal(str)
    house = Signal(int, str)
    privacy = Signal(int, str)
    me = Signal(dict)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._cancel = False
        self._thread: QThread | None = None
        self._worker: _QuestWorker | None = None
        self._rest: DiscordRest | None = None
        self.preferred: RunningClient | None = None
        self.auto_enroll = True
        self.auto_claim = True

    @property
    def busy(self) -> bool:
        return self._busy

    def _client(self) -> DiscordRest:
        auth = harvest(self.preferred)
        if not auth.token:
            raise RuntimeError(t("quest_no_token"))
        rest = DiscordRest(auth.token, auth.cookie)
        self._rest = rest
        return rest

    def refresh(self) -> None:
        try:
            rest = self._client()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        status, me = rest.me()
        if status == 200 and isinstance(me, dict):
            self.me.emit(me)
        status, payload = rest.quests_me()
        if status != 200:
            message = payload.get("message") if isinstance(payload, dict) else str(payload)
            self.failed.emit(t("quest_list_fail", status=status, message=message))
            return
        items = parse_quest_list(payload)
        self.quests.emit(items)
        blocked = "quest_ready_ok"
        if isinstance(payload, dict):
            if payload.get("quest_enrollment_blocked_until"):
                blocked = "quest_enroll_block"
            if payload.get("quest_access_suspended_until"):
                blocked = "quest_suspended"
        self.log.emit("quest_ready", {"n": len(items), "state_key": blocked})

    def set_house(self, house_id: int) -> None:
        try:
            rest = self._client()
            status, data = rest.hypesquad_join(house_id)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        names = {1: "Bravery", 2: "Brilliance", 3: "Balance"}
        if status in (200, 204):
            self.house.emit(house_id, names.get(house_id, str(house_id)))
            self.log.emit("quest_house_ok", {"name": names.get(house_id)})
            status, me = rest.me()
            if status == 200 and isinstance(me, dict):
                self.me.emit(me)
        else:
            message = data.get("message") if isinstance(data, dict) else str(data)
            self.failed.emit(t("quest_house_fail", status=status, message=message))

    def leave_house(self) -> None:
        try:
            rest = self._client()
            status, data = rest.hypesquad_leave()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if status in (200, 204):
            self.house.emit(0, t("quest_left"))
            self.log.emit("quest_left_log", {})
        else:
            message = data.get("message") if isinstance(data, dict) else str(data)
            self.failed.emit(t("quest_leave_fail", status=status, message=message))

    def set_privacy(self, level: int) -> None:
        try:
            rest = self._client()
            status, data = rest.set_privacy(level)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        labels = {1: t("privacy_private_log"), 2: t("privacy_limited_log"), 3: t("privacy_public_log")}
        if status in (200, 204):
            self.privacy.emit(level, labels.get(level, str(level)))
            self.log.emit("quest_privacy_log", {"name": labels.get(level)})
        else:
            message = data.get("message") if isinstance(data, dict) else str(data)
            self.failed.emit(t("quest_privacy_fail", status=status, message=message))

    def stop(self) -> None:
        self._cancel = True

    def start(self, enroll: bool = True) -> None:
        if self._busy:
            self.failed.emit(t("quest_busy"))
            return
        try:
            rest = self._client()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self._cancel = False
        self._busy = True
        worker = _QuestWorker(
            rest,
            enroll=enroll and self.auto_enroll,
            claim=self.auto_claim,
            cancel=lambda: self._cancel,
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self.log)
        worker.quests.connect(self.quests)
        worker.progress.connect(self.progress)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(thread.quit)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _on_failed(self, message: str) -> None:
        self._busy = False
        self.failed.emit(message)

    def _on_finished(self, ok: int, total: int) -> None:
        self._busy = False
        self.finished.emit(ok, total)

    def _clear(self) -> None:
        self._thread = None
        self._worker = None


class _QuestWorker(QObject):
    log = Signal(str, dict)
    quests = Signal(list)
    progress = Signal(str, int, int, bool)
    finished = Signal(int, int)
    failed = Signal(str)

    def __init__(
        self,
        rest: DiscordRest,
        enroll: bool,
        cancel: Callable[[], bool],
        claim: bool = True,
    ) -> None:
        super().__init__()
        self.rest = rest
        self.enroll = enroll
        self.claim = claim
        self.cancel = cancel

    def _stream_key(self, quest_id: str) -> str:
        status, channels = self.rest.dm_channels()
        if status == 200 and isinstance(channels, list):
            for item in channels:
                if isinstance(item, dict) and item.get("id") and item.get("type") in (1, 3):
                    return f"call:{item['id']}:1"
        return f"call:{quest_id}:1"

    def _complete(self, task: QuestTask) -> bool:
        if task.completed:
            return True
        if self.enroll and not task.enrolled:
            status, data = self.rest.enroll(task.quest_id)
            self.log.emit("quest_enroll_log", {"name": task.name, "status": status})
            if status in (200, 201, 204) and isinstance(data, dict):
                parsed = parse_quest(data) or task
                task.enrolled = True
                task.progress = parsed.progress
                task.target = parsed.target or task.target
            elif status not in (200, 201, 204):
                message = data.get("message") if isinstance(data, dict) else str(data)
                self.log.emit("quest_enroll_fail", {"name": task.name, "message": message})
        current = float(task.progress)
        target = float(task.target or 0)
        if target <= 0:
            self.log.emit("quest_no_target", {"name": task.name})
            return False
        video = task.task_type.startswith("WATCH_VIDEO")
        stream_key = "" if video else self._stream_key(task.quest_id)
        while current < target and not self.cancel():
            if video:
                nxt = min(target, current + 1.0 + random.random())
                status, data = self.rest.video_progress(task.quest_id, nxt)
                if status in (200, 204) and isinstance(data, dict):
                    current = float(data.get("timestamp") or nxt)
                    if data.get("completed_at"):
                        current = target
                elif status in (200, 204):
                    current = nxt
                else:
                    self.log.emit("quest_video", {"status": status, "name": task.name})
                    time.sleep(2)
                    continue
                self.progress.emit(task.quest_id, int(current), int(target), current >= target)
                time.sleep(1.0 + random.random() * 0.5)
            else:
                status, data = self.rest.heartbeat(task.quest_id, stream_key, terminal=False)
                if status in (200, 204) and isinstance(data, dict):
                    progress_map = (data.get("progress") or {}).get(task.task_type) or {}
                    current = float(progress_map.get("value") or current)
                elif status not in (200, 204):
                    self.log.emit("quest_heartbeat", {"status": status, "name": task.name})
                    time.sleep(5)
                    continue
                self.progress.emit(task.quest_id, int(current), int(target), current >= target)
                time.sleep(20 + random.random() * 2)
        if current >= target:
            if video:
                self.rest.video_progress(task.quest_id, target)
            else:
                self.rest.heartbeat(task.quest_id, stream_key, terminal=True)
            self.progress.emit(task.quest_id, int(target), int(target), True)
            self.log.emit("quest_done_log", {"name": task.name})
            if self.claim:
                status, data = self.rest.claim_quest(task.quest_id)
                extra = data.get("message") if isinstance(data, dict) else ""
                self.log.emit("quest_claim", {"name": task.name, "status": status, "extra": extra})
            return True
        return False

    @Slot()
    def run(self) -> None:
        status, payload = self.rest.quests_me()
        if status != 200:
            message = payload.get("message") if isinstance(payload, dict) else str(payload)
            self.failed.emit(t("quest_list_fail", status=status, message=message))
            return
        items = parse_quest_list(payload)
        self.quests.emit(items)
        pending = [item for item in items if not item.completed and item.task_type != "UNKNOWN"]
        if self.enroll:
            for task in list(pending):
                if task.enrolled or self.cancel():
                    continue
                status, data = self.rest.enroll(task.quest_id)
                self.log.emit("quest_enroll_log", {"name": task.name, "status": status})
                if status in (200, 201, 204):
                    task.enrolled = True
                    if isinstance(data, dict):
                        parsed = parse_quest(data)
                        if parsed:
                            task.progress = parsed.progress
                            task.target = parsed.target or task.target
        pending = [item for item in pending if item.enrolled or self.enroll]
        if not pending:
            self.log.emit("quest_none", {})
            self.finished.emit(0, len(items))
            return
        ok = 0
        for task in pending:
            if self.cancel():
                break
            self.log.emit("quest_start", {"name": task.name, "type": task.task_type})
            if self._complete(task):
                ok += 1
        self.finished.emit(ok, len(pending))
