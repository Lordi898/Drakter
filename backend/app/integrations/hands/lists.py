"""HANDS_OFF, RISKY and RISKY_KEYS: the helper's `hands/helper/lists.py`, loaded by path.

One file for both barriers, so they cannot drift. It is plain data plus pure functions (standard library
only), loaded once at import time.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[4]
HELPER_DIR: Final = REPO_ROOT / "hands" / "helper"
_SOURCE: Final = HELPER_DIR / "lists.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("drakter_hands_lists", _SOURCE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_lists = _load()

HANDS_OFF: Final[dict[str, str]] = _lists.HANDS_OFF
RISKY_CLICK = _lists.RISKY_CLICK
RISKY_KEYS: Final[frozenset[str]] = _lists.RISKY_KEYS
hands_off_name = _lists.hands_off_name
is_risky_text = _lists.is_risky_text
risky_kind = _lists.risky_kind
is_risky_combo = _lists.is_risky_combo
normalize_combo = _lists.normalize_combo
secret_title = _lists.secret_title
fold = _lists.fold
match_score = _lists.match_score
