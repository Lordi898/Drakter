"""Drakter Jobs: trabajos en segundo plano (plan de voz v2 §4.3 y §4.5).

`JobOut` es la respuesta REST de `/api/v1/jobs`; `Jobs*Args`/`Jobs*Result` son las herramientas
`jobs_*` del agente de primer plano (los trabajadores no las ven). Ninguna devuelve texto libre.
Tabla `jobs`: `backend/migrations/0014_jobs.sql`. No existe el estado `waiting_confirmation`:
un trabajo con confirmaciones pendientes termina `completed` con `pending_actions > 0`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Literal

from pydantic import BaseModel, Field

from .common import ContractModel, Id, Instant


class JobState(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobOut(BaseModel):
    job_id: Id
    title: str
    state: JobState
    reason: str | None = None
    pending_actions: int = 0
    created_at: Instant
    finished_at: Instant | None = None
    elapsed_s: int = 0
    tool_calls: int = 0
    last_tool: str | None = None


class JobList(BaseModel):
    items: list[JobOut]


# Herramientas (backend/app/tools/jobs.py)
class JobsStartArgs(ContractModel):
    title: Annotated[str, Field(min_length=3, max_length=80)]
    brief: Annotated[str, Field(min_length=20, max_length=4000)]


class JobsStartResult(BaseModel):
    job_id: Id
    state: Literal["running"] = "running"


class JobsStatusArgs(ContractModel):
    job_id: Id | None = None


class JobStatusItem(BaseModel):
    job_id: Id
    title: str
    state: JobState
    elapsed_s: int
    tool_calls: int
    last_tool: str | None = None
    pending_actions: int = 0


class JobsStatusResult(BaseModel):
    jobs: list[JobStatusItem]


class JobsAmendArgs(ContractModel):
    job_id: Id
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class JobsAmendResult(BaseModel):
    accepted: bool
    mode: Literal["redirected", "queued"]


class JobsCancelArgs(ContractModel):
    job_id: Id


class JobsCancelResult(BaseModel):
    job_id: Id
    state: Literal["cancelled"] = "cancelled"


JOB_ERRORS: Final = ("jobs_full", "lane_unavailable", "job_not_found", "job_not_running")
