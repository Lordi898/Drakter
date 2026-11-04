"""Modelos de dominio v1. Reexporta todo; la fuente de columnas y enumerados es backend/migrations/."""

from . import (
    activity, calendar, chat, confirmations, habits, improvement, memory, notifications, projects,
    relationships, settings, storage, subjects, system, tags, tasks,
)
from ._base import EntityOut, OutModel

MODULES = (
    tasks, projects, habits, calendar, subjects, storage, relationships, tags, chat, confirmations,
    activity, notifications, settings, memory, improvement, system,
)

__all__: list[str] = ["EntityOut", "OutModel", "MODULES"]
for _m in MODULES:
    for _n, _v in vars(_m).items():
        if not _n.startswith("_") and getattr(_v, "__module__", None) == _m.__name__:
            globals()[_n] = _v
            __all__.append(_n)
