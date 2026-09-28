"""Script hooks: let a local Python file build the ActivityConfig.

A hook is a plain ``.py`` file that defines ``build_activity(game)``
returning either an :class:`~ky_gameplayer.activity.ActivityConfig`, a
dict accepted by ``ActivityConfig.from_json``, or ``None`` (keep the
editor's current config). Load with :func:`load_hook`, call the returned
callable with the selected game.

Hooks are power-user territory: the file runs with this app's
permissions, so only point this at scripts you have read. The loader
refuses anything that is not a ``.py`` file and validates the result
shape before returning it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

from .activity import ActivityConfig

HOOK_FUNCTION = "build_activity"


def load_hook(path: str | Path) -> Callable[[Any], ActivityConfig | None]:
    """Import a hook file and return its ``build_activity`` callable."""
    file = Path(path)
    if file.suffix != ".py" or not file.is_file():
        raise ValueError(f"hook must be an existing .py file: {path}")
    module_name = f"kodyazar_hook_{file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import hook: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        raise ValueError(f"hook raised while importing: {exc}") from exc
    hook = getattr(module, HOOK_FUNCTION, None)
    if not callable(hook):
        raise ValueError(f"hook has no callable {HOOK_FUNCTION}(game): {path}")
    return hook


def run_hook(hook: Callable[[Any], Any], game: Any) -> ActivityConfig | None:
    """Call a hook and normalize its result to an ActivityConfig (or None)."""
    try:
        result = hook(game)
    except Exception as exc:
        raise ValueError(f"hook raised while running: {exc}") from exc
    if result is None:
        return None
    if isinstance(result, ActivityConfig):
        return result
    if isinstance(result, dict):
        return ActivityConfig.from_json(result)
    raise ValueError(f"hook returned {type(result).__name__}; expected ActivityConfig, dict, or None")
