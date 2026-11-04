"""Límites y tipos de la búsqueda global. La forma de salida es la del contrato."""

from __future__ import annotations

from typing import Final, Literal, get_args

SearchEntityType = Literal["task", "project", "habit", "calendar_event", "subject", "resource"]

ALL_ENTITY_TYPES: Final[tuple[SearchEntityType, ...]] = get_args(SearchEntityType)
MAX_QUERY_CHARS: Final = 200
DEFAULT_LIMIT: Final = 50
MAX_LIMIT: Final = 100
MAX_CURSOR_CHARS: Final = 128
