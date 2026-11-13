"""Bases comunes de los modelos de dominio."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from ..common import Id, Instant

Metadata = dict[str, Any]
Title = Annotated[str, Field(min_length=1, max_length=300)]
Name = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(max_length=8000)]
TagName = Annotated[str, Field(min_length=1, max_length=64)]
Hash = str


class OutModel(BaseModel):
    """Salida: no valida extras (el servidor la construye)."""

    model_config = ConfigDict(extra="ignore")


class EntityCoreOut(OutModel):
    """Campos de `entities` que expone toda entidad de dominio (0001)."""

    id: Id
    created_at: Instant
    updated_at: Instant
    archived_at: Instant | None = None
    revision: int = Field(ge=1)


class EntityOut(EntityCoreOut):
    """Entidad que además expone `metadata` en la API (tareas, proyectos, eventos)."""

    metadata: Metadata = {}
