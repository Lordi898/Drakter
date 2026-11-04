"""Contrato de la búsqueda global: REST `GET /api/v1/search` y servicio."""

from __future__ import annotations

from typing import Final, Literal, get_args

from pydantic import BaseModel

SearchEntityType = Literal["task", "project", "habit", "calendar_event", "subject", "resource"]
Trust = Literal["workspace", "untrusted"]

ALL_ENTITY_TYPES: Final[tuple[SearchEntityType, ...]] = get_args(SearchEntityType)
MAX_QUERY_CHARS: Final = 200
MAX_LIMIT: Final = 50
MAX_OFFSET: Final = 10_000


class SnippetPart(BaseModel):
    """Trozo de texto plano. La coincidencia va como dato, nunca como marcado."""

    text: str
    match: bool = False


class SearchItem(BaseModel):
    entity_type: SearchEntityType
    entity_id: str
    title: str
    snippet: list[SnippetPart]
    # Lo que viene de un recurso es dato no confiable, también título y extracto.
    trust: Trust


class SearchPage(BaseModel):
    items: list[SearchItem]
    total: int
