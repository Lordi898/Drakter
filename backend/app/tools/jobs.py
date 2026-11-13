"""Herramientas `jobs_*` del agente de primer plano (voz v2, §4.5). Los trabajadores no las ven.

Finas: validan con los modelos del contrato, llaman al `JobManager` y traducen sus errores.
Ninguna devuelve texto libre (`returns_untrusted=False`); el registro las audita.

Todas son READ o WRITE sin confirmación propia. Con la sesión contaminada, `effective_risk`
(`tools/gate.py`) eleva las WRITE (`jobs_start`, `jobs_amend`, `jobs_cancel`) a CONFIRM: el
usuario aprueba en pantalla y el trabajo arranca (o se cancela) con la aprobación (V-26).
"""

from __future__ import annotations

import asyncio
from typing import Any, Final

from drakter_contracts.jobs import (
    JobsAmendArgs,
    JobsAmendResult,
    JobsCancelArgs,
    JobsCancelResult,
    JobsStartArgs,
    JobsStartResult,
    JobsStatusArgs,
    JobsStatusResult,
)

from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

_DOMAIN: Final = "jobs"
_ERR_START: Final = ("jobs_full", "lane_unavailable")
_ERR_RUNNING: Final = ("job_not_found", "job_not_running")


def _manager(ctx: ToolContext) -> Any:
    manager = getattr(ctx.state, "job_manager", None)
    if manager is None:
        raise ToolError("lane_unavailable", "El carril de trabajos no está disponible ahora mismo.")
    return manager


async def _call(manager: Any, coro: Any) -> Any:
    """Runs on the manager's loop. An approved call (`tool_action_spec`) arrives on a worker
    thread with its own `asyncio.run`: the job must not live on that throwaway loop."""
    from app.jobs.manager import JobError

    loop = getattr(manager, "loop", None)
    try:
        if loop is not None and loop is not asyncio.get_running_loop():
            return await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop))
        return await coro
    except JobError as exc:
        raise ToolError(exc.code, exc.message) from None


async def _start(ctx: ToolContext, args: JobsStartArgs) -> JobsStartResult:
    manager = _manager(ctx)
    job = await _call(manager, manager.start_job(args.title, args.brief, ctx.session_id))
    return JobsStartResult(job_id=job.id)


async def _status(ctx: ToolContext, args: JobsStatusArgs) -> JobsStatusResult:
    manager = _manager(ctx)
    jobs = await _call(manager, manager.status(args.job_id))
    return JobsStatusResult(jobs=[job.status_item() for job in jobs])


async def _amend(ctx: ToolContext, args: JobsAmendArgs) -> JobsAmendResult:
    manager = _manager(ctx)
    accepted, mode = await _call(manager, manager.amend(args.job_id, args.text))
    return JobsAmendResult(accepted=accepted, mode=mode)


async def _cancel(ctx: ToolContext, args: JobsCancelArgs) -> JobsCancelResult:
    manager = _manager(ctx)
    job = await _call(manager, manager.cancel(args.job_id))
    return JobsCancelResult(job_id=job.id)


TOOLS: Final = (
    ToolSpec(
        name="jobs_start",
        description=(
            "Lanza un trabajo largo en segundo plano con un título corto y un encargo completo y "
            "autosuficiente; usted sigue atendiendo al usuario. Al terminar, Drakter avisa solo "
            "(frase hablada y notificación) y el resumen le llega a usted en el turno siguiente: "
            "no hace falta que el usuario pregunte. Solo hay un carril: si está ocupado, devuelve "
            "jobs_full."
        ),
        domain=_DOMAIN,
        args_model=JobsStartArgs,
        result_model=JobsStartResult,
        permission="jobs.write",
        risk=RiskClass.WRITE,
        handler=_start,
        errors=_ERR_START,
        timeout_s=10.0,
        audit={"title": "log", "brief": "hash"},
    ),
    ToolSpec(
        name="jobs_status",
        description=(
            "Estado de los trabajos en segundo plano (o de uno, con job_id): título, estado, "
            "tiempo, herramientas usadas y acciones pendientes de confirmar."
        ),
        domain=_DOMAIN,
        args_model=JobsStatusArgs,
        result_model=JobsStatusResult,
        permission="jobs.read",
        risk=RiskClass.READ,
        handler=_status,
        errors=("job_not_found",),
        idempotent=True,
        timeout_s=5.0,
        audit={"job_id": "log"},
    ),
    ToolSpec(
        name="jobs_amend",
        description=(
            "Añade una corrección o un dato a un trabajo en curso: lo redirige si está pensando "
            "o lo deja en cola para su siguiente paso."
        ),
        domain=_DOMAIN,
        args_model=JobsAmendArgs,
        result_model=JobsAmendResult,
        permission="jobs.write",
        risk=RiskClass.WRITE,
        handler=_amend,
        errors=_ERR_RUNNING,
        timeout_s=10.0,
        audit={"job_id": "log", "text": "hash"},
    ),
    ToolSpec(
        name="jobs_cancel",
        description="Cancela un trabajo en curso. Lo que ya hizo no se deshace.",
        domain=_DOMAIN,
        args_model=JobsCancelArgs,
        result_model=JobsCancelResult,
        permission="jobs.write",
        risk=RiskClass.WRITE,
        handler=_cancel,
        errors=_ERR_RUNNING,
        idempotent=True,
        timeout_s=10.0,
        audit={"job_id": "log"},
    ),
)
