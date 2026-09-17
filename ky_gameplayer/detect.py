from __future__ import annotations

from dataclasses import dataclass

from .games import Game, GameCatalog
from .processes import RunningProcess, list_processes, process_names


@dataclass(slots=True)
class DetectedGame:
    game: Game
    process: RunningProcess
    matched: str


def _basename(path: str) -> str:
    name = path.replace("\\", "/").rstrip("/").split("/")[-1]
    return name.casefold()


class ProcessIndex:
    def __init__(self, catalog: GameCatalog) -> None:
        self.by_exe: dict[str, list[Game]] = {}
        for game in catalog.games:
            for exe in game.executables:
                if exe.get("is_launcher"):
                    continue
                name = str(exe.get("name") or "")
                if not name:
                    continue
                key = _basename(name)
                if key.startswith(">"):
                    key = key[1:]
                if not key:
                    continue
                self.by_exe.setdefault(key, []).append(game)
                if key.endswith(".exe"):
                    self.by_exe.setdefault(key[:-4], []).append(game)

    def scan(self, processes: list[RunningProcess] | None = None) -> list[DetectedGame]:
        processes = processes if processes is not None else list_processes()
        found: dict[str, DetectedGame] = {}
        for proc in processes:
            names = process_names(proc)
            low_cmd = (proc.cmdline or "").casefold()
            if "proton" in low_cmd or "wine" in low_cmd or "waitforexitandrun" in low_cmd:
                for token in (proc.cmdline or "").replace("\\", "/").split():
                    base = _basename(token)
                    if base.endswith(".exe"):
                        names.add(base)
                        names.add(base[:-4])
            for name in names:
                games = self.by_exe.get(name)
                if not games:
                    continue
                for game in games:
                    current = found.get(game.id)
                    if current is None or proc.pid < current.process.pid:
                        found[game.id] = DetectedGame(game=game, process=proc, matched=name)
        return sorted(found.values(), key=lambda item: item.game.name.casefold())
