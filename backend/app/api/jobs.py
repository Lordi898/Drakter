"""REST de Drakter Jobs (§4.3): listar y cancelar. Se monta solo (`app/main.py`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from drakter_contracts.jobs import JobList, JobOut
from fastapi import APIRouter, Request

from app.core.errors import AppError

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

_STATUS = {"job_not_found": 404, "job_not_running": 409, "lane_unavailable": 503, "jobs_full": 409}


def _manager(request: Request) -> Any:
    manager = getattr(request.app.state, "job_manager", None)
    if manager is None:
        raise AppError("lane_unavailable", "El carril de trabajos no está disponible.", 503)
    return manager


@router.get("", response_model=JobList)
async def list_jobs(request: Request) -> JobList:
    jobs = await _manager(request).list_jobs()
    return JobList(items=[job.out() for job in jobs])


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: UUID, request: Request) -> JobOut:
    from app.jobs.manager import JobError

    try:
        job = await _manager(request).cancel(job_id)
    except JobError as exc:
        raise AppError(exc.code, exc.message, _STATUS.get(exc.code, 400)) from None
    return job.out()
