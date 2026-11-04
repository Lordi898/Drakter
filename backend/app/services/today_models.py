"""Contrato de `GET /api/v1/today`. Congelado: backend y escritorio construyen sobre esto.

Reglas (todas en la zona horaria pedida; nunca se asume una por defecto):

- Hoy = [medianoche local, medianoche local siguiente), calculado con `zoneinfo`, así que
  un día puede durar 23 o 25 horas. La frontera se calcula, no se suman 24 h.
- Abierta = `pending`, `in_progress` u `on_hold`, sin `archived_at`.
- Vencida = abierta y (`due_at` < ahora, o `due_date` < hoy). Una tarea con hora que ya pasó
  hoy está vencida, no "de hoy".
- De hoy = abierta y (`due_date` == hoy, o ahora <= `due_at` < medianoche siguiente).
- Una tarea cae en una sola lista. Sin fecha no aparece.
- Proyecto activo = `status='active'`, sin `archived_at`.
- Progreso = `manual_progress` si existe; si no, % de tareas completadas entre las no canceladas
  ni archivadas del proyecto; sin tareas, `null` (no 0: no se inventa un dato).
- Cada sección informa por separado. Si su módulo no está migrado o falla, esa sección queda
  `unavailable` y las demás siguen. Nunca se rellena con datos de ejemplo.
- Títulos y nombres son datos de usuario o del agente: se devuelven tal cual y no se interpretan.
"""

from __future__ import annotations

from datetime import date
from typing import Final, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

SECTION_LIMIT: Final = 100

SectionStatus = Literal["ready", "unavailable"]
UnavailableReason = Literal["not_migrated", "module_missing", "failed"]
T = TypeVar("T")


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class Section(_Out, Generic[T]):
    status: SectionStatus
    reason: UnavailableReason | None = None
    items: list[T] = Field(default_factory=list)
    total: int = 0
    truncated: bool = False


class TodayTask(_Out):
    id: str
    title: str
    status: Literal["pending", "in_progress", "on_hold"]
    priority: Literal["low", "medium", "high", "urgent"]
    due_at: str | None  # instante UTC tal como está guardado
    due_date: date | None
    days_overdue: int  # días naturales locales; 0 si vence hoy o no está vencida
    project_id: str | None
    project_name: str | None
    parent_task_id: str | None


class TodayProject(_Out):
    id: str
    name: str
    priority: Literal["low", "medium", "high", "urgent"]
    target_date: date | None
    progress: int | None  # 0..100
    progress_source: Literal["manual", "calculated"] | None
    open_tasks: int
    overdue_tasks: int


class TodayAgendaEntry(_Out):
    occurrence_id: str
    source_type: str
    source_id: str
    title: str
    kind: str
    all_day: bool
    display_start: str | None  # 'AAAA-MM-DDTHH:MM:SS' en la zona pedida; null si es de día completo
    display_end: str | None
    room: str | None
    color: str | None


class TodayHabit(_Out):
    id: str
    name: str
    preferred_local_time: str | None
    today_status: Literal["done", "skipped", "missed"] | None


class TodayResponse(_Out):
    date: date
    timezone: str
    generated_at: str  # UTC, 'AAAA-MM-DDTHH:MM:SS.sssZ'
    overdue: Section[TodayTask]
    due_today: Section[TodayTask]
    projects: Section[TodayProject]
    agenda: Section[TodayAgendaEntry]
    habits: Section[TodayHabit]
