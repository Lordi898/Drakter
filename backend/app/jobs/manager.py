"""JobManager: trabajos largos del agente en carriles Hermes aparte (voz v2, V-24 a V-27).

- N=1 por carril y sin cola: con el carril ocupado, `jobs_full`.
- `amend` redirige el turno del trabajo (`steer`) o deja el texto en cola para su siguiente paso.
- Las confirmaciones no paran el trabajo: la herramienta devuelve `confirmation_required`, se
  cuenta en `pending_actions` y la confirmación sigue su TTL en pantalla, con `job_id`.
- Al terminar: `job.finished`, una notificación y `on_job_finished` (WP9 lo conecta a la frase
  `job_done`/`job_failed` en silencio). Nunca se inserta un mensaje de asistente en el chat.
- El resumen llega al agente de primer plano en el prefijo de su siguiente turno, dentro de un
  sobre de dato no confiable y una sola vez por trabajo (`turn_prefix`).

Montaje (WP9): `await install_jobs(app)` tras `wire_security` y `runtime.start()`, y
`await app.state.job_manager.stop()` antes de `runtime.stop()`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final
from uuid import UUID, uuid4

from drakter_contracts.common import format_instant
from drakter_contracts.events import (
    JobFinished,
    JobProgress,
    JobStarted,
    NotificationCreated,
)
from drakter_contracts.jobs import JobOut, JobState
from drakter_contracts.speech_markup import strip_tags

from app.integrations.hermes.events import (
    TERMINAL_EVENTS,
    MessageDelta,
    ToolStarted,
    TurnCancelled,
    TurnCompleted,
    TurnFailed,
)
from app.integrations.hermes.lanes import Lane, LaneBusy
from app.integrations.hermes.provider import TurnRequest
from app.jobs import repository as repo
from app.jobs.models import REASON_MAX, SUMMARY_MAX, Job, utc_now
from app.tools.envelope import untrusted_envelope

logger = logging.getLogger("drakter.jobs")

PROGRESS_EVERY_S: Final = 2.0
CANCEL_WAIT_S: Final = 8.0
STEER_WAIT_S: Final = 3.0
MAX_FOLLOWUPS: Final = 5  # turnos extra por textos en cola; evita un bucle sin fin
PREFIX_SUMMARY_MAX: Final = 1500


def default_lanes() -> list[Lane]:
    return [Lane("w1", "hermes-w1", "medium", 900)]


class JobError(Exception):
    """Fallo esperado. `code` ∈ `drakter_contracts.jobs.JOB_ERRORS`; `message` es seguro."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(slots=True)
class _Run:
    job: Job
    lane: Lane
    turn_id: UUID | None = None
    task: asyncio.Task[None] | None = None
    queued: list[str] = field(default_factory=list)
    cancel_requested: bool = False
    cancel_reason: str = "user"
    steer_waiter: asyncio.Future[bool] | None = None
    last_progress: float = 0.0
    progress_timer: asyncio.TimerHandle | None = None


def _short(job_id: UUID) -> str:
    return job_id.hex[:6]


def _job_prompt(job: Job) -> str:
    return (
        f"Trabajo en segundo plano «{job.title}». Hazlo de forma autónoma, sin preguntar al "
        "usuario, y termina con un resumen breve de lo hecho y de lo que quede pendiente.\n\n"
        f"{job.brief}"
    )


class JobManager:
    def __init__(
        self,
        db_path: Path,
        hub: Any,
        lanes: list[Lane] | None = None,
        *,
        runtime: Any | None = None,
    ) -> None:
        self._db = db_path
        self._hub = hub
        self.lanes = lanes if lanes is not None else default_lanes()
        self._runtime = runtime
        self._runs: dict[UUID, _Run] = {}
        self._unannounced: list[Job] = []  # terminados que el primer plano aún no ha visto
        self._admit = asyncio.Lock()
        self.loop: asyncio.AbstractEventLoop | None = None  # the backend's; set in start()
        # (JobOut) -> None. WP9: speak.phrase{job_done|job_failed, when_silent}.
        self.on_job_finished: Callable[[JobOut], Any] | None = None

    # Ciclo de vida

    async def start(self) -> None:
        self.loop = asyncio.get_running_loop()
        orphans = await asyncio.to_thread(repo.fail_orphans, self._db, utc_now(), "backend_restart")
        if orphans:
            logger.warning(
                "jobs left running by a previous run",
                extra={"event": "jobs_orphaned", "count": orphans},
            )
        if self._runtime is None:
            return
        for lane in self.lanes:
            await lane.start(self._runtime, self.observe_tool_outcome)

    async def stop(self) -> None:
        for run in list(self._runs.values()):
            with contextlib.suppress(Exception):
                await self._cancel_run(run, reason="shutdown")
        for lane in self.lanes:
            await lane.stop()

    # Operaciones (herramientas y REST)

    async def start_job(self, title: str, brief: str, parent_session_id: UUID | None) -> Job:
        async with self._admit:
            lane = next((ln for ln in self.lanes if ln.ready() and not ln.busy), None)
            if lane is None:
                if any(ln.ready() for ln in self.lanes):
                    raise JobError(
                        "jobs_full", "Ya hay un trabajo en curso; espere a que termine o cancélelo."
                    )
                raise JobError("lane_unavailable", "El carril de trabajos no está disponible ahora mismo.")
            session_id = await lane.create_session()
            tainted = self._parent_tainted(parent_session_id)
            if tainted:
                lane.mark_tainted(session_id)
            now = utc_now()
            job = Job(
                id=uuid4(), session_id=session_id, lane=lane.name, title=title, brief=brief,
                parent_session_id=parent_session_id, tainted=tainted, created_at=now, started_at=now,
            )  # fmt: skip
            await asyncio.to_thread(repo.insert, self._db, job)
            run = _Run(job=job, lane=lane)
            lane.current_job_id = job.id
            self._runs[job.id] = run
        self._publish(
            "job.started",
            JobStarted(job_id=job.id, title=job.title, lane=lane.name, created_at=job.created_at),
            job,
        )
        run.task = asyncio.create_task(self._run(run), name=f"job-{_short(job.id)}")
        return job

    async def amend(self, job_id: UUID, text: str) -> tuple[bool, str]:
        run = await self._running(job_id)
        turn_id = run.turn_id
        if turn_id is not None and run.lane.can_steer:
            loop = asyncio.get_running_loop()
            run.steer_waiter = loop.create_future()
            try:
                answer = await run.lane.steer(turn_id, text)
                if answer is None:
                    with contextlib.suppress(TimeoutError):
                        answer = await asyncio.wait_for(asyncio.shield(run.steer_waiter), STEER_WAIT_S)
            except Exception as exc:  # noqa: BLE001 - steering is best effort; the text is queued
                logger.warning(
                    "job steer failed",
                    extra={"event": "job_steer_failed", "kind": type(exc).__name__},
                )
                answer = False
            finally:
                run.steer_waiter = None
            if answer:
                return True, "redirected"
        run.queued.append(text)
        return True, "queued"

    async def cancel(self, job_id: UUID, *, reason: str = "user") -> Job:
        run = await self._running(job_id)
        await self._cancel_run(run, reason=reason)
        return run.job

    async def get(self, job_id: UUID) -> Job | None:
        run = self._runs.get(job_id)
        if run is not None:
            return run.job
        return await asyncio.to_thread(repo.get, self._db, job_id)

    async def list_jobs(self, limit: int = 50) -> list[Job]:
        rows = await asyncio.to_thread(repo.recent, self._db, limit)
        return [self._runs[j.id].job if j.id in self._runs else j for j in rows]

    async def status(self, job_id: UUID | None = None) -> list[Job]:
        if job_id is not None:
            job = await self.get(job_id)
            if job is None:
                raise JobError("job_not_found", "Ese trabajo no existe.")
            return [job]
        jobs = await self.list_jobs(limit=10)
        return [j for j in jobs if j.running] + [j for j in jobs if not j.running][:5]

    async def _running(self, job_id: UUID) -> _Run:
        run = self._runs.get(job_id)
        if run is not None and run.job.running:
            return run
        if run is None and await asyncio.to_thread(repo.get, self._db, job_id) is None:
            raise JobError("job_not_found", "Ese trabajo no existe.")
        raise JobError("job_not_running", "Ese trabajo ya ha terminado.")

    # Prefijo del turno de primer plano (V-27)

    def turn_prefix(self, session_id: UUID, source: str) -> str | None:
        """Firma de `AgentRuntime.add_turn_prefix`. Solo va al `turn_prompt`: ni BD ni chat."""
        lines: list[str] = []
        running = [r.job for r in self._runs.values() if r.job.running]
        if running:
            items = "; ".join(
                f"#{_short(j.id)} '{j.title}' {j.state.value} {j.elapsed_s()} s" for j in running
            )
            lines.append(f"Trabajos en curso: {items}")
        finished, self._unannounced = self._unannounced, []
        if finished:
            lines.append("Trabajos terminados desde su último turno:")
            for job in finished:
                pending = (
                    f", {job.pending_actions} acciones pendientes de confirmar en pantalla"
                    if job.pending_actions
                    else ""
                )
                lines.append(f"- #{_short(job.id)} '{job.title}' {job.state.value}{pending}")
                if job.summary:
                    summary = job.summary[:PREFIX_SUMMARY_MAX]
                    envelope = untrusted_envelope(
                        "job_summary", str(job.id), summary, truncated=len(job.summary) > len(summary)
                    )
                    lines.append(json.dumps(envelope, ensure_ascii=False))
                if job.tainted:
                    self._taint_parent(session_id)
        return "\n".join(lines) if lines else None

    def _parent_tainted(self, session_id: UUID | None) -> bool:
        turns = getattr(self._runtime, "turns", None)
        return bool(session_id and turns is not None and turns.is_tainted(session_id))

    def _taint_parent(self, session_id: UUID) -> None:
        turns = getattr(self._runtime, "turns", None)
        if turns is not None:
            turns.mark_tainted(session_id)

    # Observador de herramientas del carril

    def observe_tool_outcome(self, name: str, ctx: Any, outcome: Any) -> None:
        """Cuenta las confirmaciones pedidas desde un trabajo. El aviso
        `confirmation.requested` (con `job_id`) lo emite una sola vez `ActionService`."""
        if outcome.model_dump().get("status") != "confirmation_required":
            return
        job_id = getattr(ctx, "job_id", None)
        run = self._runs.get(job_id) if job_id is not None else None
        if run is not None:
            run.job.pending_actions += 1

    # Ejecución

    async def _run(self, run: _Run) -> None:
        job = run.job
        text = _job_prompt(job)
        terminal: Any = None
        try:
            for _ in range(MAX_FOLLOWUPS + 1):
                run.turn_id = uuid4()
                terminal = await self._consume(run, TurnRequest(job.session_id, run.turn_id, text))
                pending = getattr(terminal, "pending_steer", None)
                if isinstance(pending, str) and pending.strip():
                    run.queued.append(pending)
                if not (isinstance(terminal, TurnCompleted) and run.queued) or run.cancel_requested:
                    break
                text, run.queued = "\n\n".join(run.queued), []
        except LaneBusy:
            terminal = None
        except Exception as exc:  # noqa: BLE001 - a broken lane ends the job, not the backend
            logger.warning("job crashed", extra={"event": "job_crashed", "kind": type(exc).__name__})
            terminal = None
        finally:
            if run.progress_timer is not None:
                run.progress_timer.cancel()
            if run.lane.current_job_id == job.id:
                run.lane.current_job_id = None
        job.tainted = job.tainted or run.lane.is_tainted(job.session_id)
        if run.cancel_requested or isinstance(terminal, TurnCancelled):
            await self._finish(run, JobState.CANCELLED, run.cancel_reason, None)
        elif isinstance(terminal, TurnCompleted):
            await self._finish(run, JobState.COMPLETED, None, terminal.text)
        elif isinstance(terminal, TurnFailed):
            await self._finish(run, JobState.FAILED, terminal.code.value, None)
        else:
            await self._finish(run, JobState.FAILED, "lane_error", None)

    async def _consume(self, run: _Run, request: TurnRequest) -> Any:
        text: list[str] = []
        # aclosing: the lane frees its tracker only when the stream is closed.
        async with contextlib.aclosing(run.lane.stream_turn(request)) as stream:
            async for event in stream:
                if isinstance(event, TERMINAL_EVENTS):
                    if isinstance(event, TurnCompleted) and not event.text and text:
                        return event.model_copy(update={"text": "".join(text)})
                    return event
                if isinstance(event, MessageDelta):
                    text.append(event.text)
                elif isinstance(event, ToolStarted):
                    run.job.tool_calls += 1
                    run.job.last_tool = event.tool[:64]
                    self._progress(run)
                elif getattr(event, "type", None) == "steered":  # evento `Steered` de WP6
                    waiter = run.steer_waiter
                    if waiter is not None and not waiter.done():
                        waiter.set_result(bool(getattr(event, "accepted", False)))
        return None

    def _progress(self, run: _Run) -> None:
        """`job.progress` como máximo cada 2 s; el último cambio nunca se pierde."""
        if run.progress_timer is not None:
            return
        wait = run.last_progress + PROGRESS_EVERY_S - time.monotonic()
        if wait > 0:
            run.progress_timer = asyncio.get_running_loop().call_later(wait, self._emit_progress, run)
        else:
            self._emit_progress(run)

    def _emit_progress(self, run: _Run) -> None:
        run.progress_timer = None
        job = run.job
        if not job.running:
            return
        run.last_progress = time.monotonic()
        self._publish(
            "job.progress",
            JobProgress(
                job_id=job.id, elapsed_s=job.elapsed_s(), tool_calls=job.tool_calls, last_tool=job.last_tool
            ),
            job,
        )
        task = asyncio.ensure_future(asyncio.to_thread(repo.update, self._db, job))
        task.add_done_callback(lambda done: done.cancelled() or done.exception())

    async def _cancel_run(self, run: _Run, *, reason: str) -> None:
        run.cancel_requested, run.cancel_reason = True, reason
        if run.turn_id is not None:
            with contextlib.suppress(Exception):
                await run.lane.cancel(run.turn_id)
        task = run.task
        if task is not None and not task.done():
            await asyncio.wait({task}, timeout=CANCEL_WAIT_S)
        # Si el runner no responde, el trabajo se da por cancelado igualmente; el carril
        # sigue ocupado hasta que el turno acabe de verdad.
        await self._finish(run, JobState.CANCELLED, reason, None)

    async def _finish(self, run: _Run, state: JobState, reason: str | None, text: str | None) -> None:
        job = run.job
        if not job.running:
            return
        job.state = state
        job.reason = reason[:REASON_MAX] if reason else None
        job.summary = (strip_tags(text).strip()[:SUMMARY_MAX] or None) if text else None
        job.finished_at = utc_now()
        self._runs.pop(job.id, None)
        try:
            await asyncio.to_thread(repo.update, self._db, job)
        except Exception as exc:  # noqa: BLE001 - the event still reaches the GUI
            logger.error(
                "job not persisted",
                extra={"event": "job_persist_failed", "kind": type(exc).__name__},
            )
        logger.info(
            "job finished",
            extra={"event": "job_finished", "job_id": str(job.id), "state": state.value},
        )
        self._publish(
            "job.finished",
            JobFinished(
                job_id=job.id, state=state.value, reason=job.reason,
                pending_actions=job.pending_actions, finished_at=job.finished_at,
            ),  # fmt: skip
            job,
        )
        if state is JobState.CANCELLED:
            return
        self._unannounced.append(job)
        await self._notify(job)
        callback = self.on_job_finished
        if callback is not None:
            try:
                result = callback(job.out())
                if asyncio.iscoroutine(result):
                    await result
            except Exception:  # noqa: BLE001
                logger.exception("on_job_finished failed", extra={"event": "job_callback_failed"})

    async def _notify(self, job: Job) -> None:
        from app.database.connection import connect
        from app.repositories import notifications as notifications_repo
        from app.repositories.notifications import NewNotification

        ok = job.state is JobState.COMPLETED
        title = f"{'Trabajo terminado' if ok else 'El trabajo ha fallado'}: {job.title}"
        if ok and job.pending_actions:
            title += f" ({job.pending_actions} por confirmar)"
        item = NewNotification(
            dedupe_key=f"job:{job.id}", kind="job", title=title[:200],
            severity="success" if ok else "error",
        )  # fmt: skip

        def insert() -> list[Any]:
            conn = connect(self._db)
            try:
                return notifications_repo.insert_new(conn, [item], format_instant(utc_now()))
            finally:
                conn.close()

        try:
            rows = await asyncio.to_thread(insert)
        except Exception as exc:  # noqa: BLE001 - a lost notification must not lose the job
            logger.warning(
                "job notification not stored",
                extra={"event": "job_notify_failed", "kind": type(exc).__name__},
            )
            return
        for row in rows:
            self._publish(
                "notification.created",
                NotificationCreated(
                    notification_id=row.id, kind=row.kind, title=row.title, severity=row.severity
                ),
                job,
            )

    def _publish(self, event_type: str, payload: Any, job: Job) -> None:
        try:
            self._hub.publish(event_type, payload, correlation_id=str(job.id))
        except Exception:  # noqa: BLE001
            logger.exception("job event not published", extra={"event": "job_publish_failed"})


async def install_jobs(app: Any, lanes: list[Lane] | None = None) -> JobManager:
    """Crea el JobManager, lo deja en `app.state.job_manager` y en el `tool_state` del runtime
    (lo leen las herramientas `jobs_*`), registra su prefijo de turno y arranca los carriles."""
    runtime = getattr(app.state, "agent_runtime", None)
    manager = JobManager(app.state.settings.db_path, app.state.event_hub, lanes, runtime=runtime)
    app.state.job_manager = manager
    if runtime is not None:
        runtime.tool_state.job_manager = manager
        add_prefix = getattr(runtime, "add_turn_prefix", None)
        if callable(add_prefix):
            add_prefix(manager.turn_prefix)
    await manager.start()
    return manager
