"""Read-only system views for the agent: voice, Workspace summary, activity and confirmations.

They reuse the services the GUI reads (`list_activity`, `ActionService`, `build_today`,
`VoiceOrchestrator.status`), so the agent and the screens see the same thing. None of them
returns arguments, secrets or transcripts, and none can decide a confirmation.
"""

from __future__ import annotations

import asyncio
import sqlite3
from contextlib import closing
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Annotated, Any, Final, Literal
from zoneinfo import ZoneInfo, available_timezones

from pydantic import BaseModel, ConfigDict, Field

from app.audit.writer import list_activity
from app.database.connection import connect
from app.repositories.notifications_due import default_timezone
from app.services.today import build_today
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec
from app.core.text import strip_invisible

FALLBACK_TIMEZONE: Final = "Europe/Madrid"  # contracts/README.md §4
ACTIVITY_MAX: Final = 50
CONFIRMATIONS_MAX: Final = 20
TODAY_ITEMS_MAX: Final = 8
TEXT_MAX: Final = 160


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArgs(_Strict):
    pass


def _clip(text: str | None, limit: int = TEXT_MAX) -> str | None:
    if text is None:
        return None
    clean = " ".join(strip_invisible(text).split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


def _read_only(ctx: ToolContext) -> sqlite3.Connection:
    conn = connect(ctx.state.settings.db_path)
    conn.execute("PRAGMA query_only=ON")
    return conn


# ── get_voice_status ─────────────────────────────────────────────────────────


class VoiceStatus(BaseModel):
    installed: bool  # False: this backend runs without the voice process
    connected: bool
    mode: Literal["standby", "conversation"] | None = None
    tts: Literal["fish", "local"] | None = None  # engine that speaks now
    profile: str | None = None
    wake_enabled: bool | None = None
    latency_ms: dict[str, float] | None = None  # last turn's measured stages, no text
    note: str


async def get_voice_status(ctx: ToolContext, args: NoArgs) -> VoiceStatus:
    voice = getattr(ctx.state, "voice", None)
    if voice is None:
        return VoiceStatus(installed=False, connected=False, note="La voz no está instalada en este arranque.")
    try:
        status = await asyncio.wait_for(voice.status(), timeout=3.0)
    except Exception:  # noqa: BLE001 - a status query must not take the tool down
        return VoiceStatus(installed=True, connected=False, note="El proceso de voz no responde.")
    metrics = {
        str(k): float(v)
        for k, v in (status.metrics_last or {}).items()
        if isinstance(v, int | float) and not isinstance(v, bool)
    } or None
    if not status.connected:
        note = "El proceso de voz no está conectado: ahora solo hay texto."
    elif status.tts == "local":
        note = "La voz funciona con el motor local (Kokoro): Fish no está disponible ahora."
    else:
        note = "La voz funciona con Fish Audio."
    return VoiceStatus(
        installed=True,
        connected=status.connected,
        mode=status.mode,
        tts=status.tts,
        profile=status.profile,
        wake_enabled=status.wake_enabled,
        latency_ms=metrics,
        note=note,
    )


# ── get_workspace_summary ────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _timezones() -> frozenset[str]:
    return frozenset(available_timezones())


class WorkspaceSummaryArgs(_Strict):
    timezone: Annotated[str, Field(min_length=1, max_length=64)] | None = Field(
        default=None,
        description="Zona IANA (p. ej. Europe/Madrid). Por defecto, la del usuario.",
    )


class SummaryTask(BaseModel):
    id: str
    title: str
    priority: str
    due: str | None  # local date or 'AAAA-MM-DDTHH:MM'
    days_overdue: int
    project: str | None


class SummaryAgendaItem(BaseModel):
    id: str
    kind: str  # event, reminder, work_session, time_block, class…
    title: str
    start: str | None  # local 'AAAA-MM-DDTHH:MM'; None if all day
    end: str | None
    room: str | None


class SummaryHabit(BaseModel):
    id: str
    name: str
    preferred_time: str | None
    today: Literal["done", "skipped", "missed"] | None


class WorkspaceCounts(BaseModel):
    open_tasks: int
    overdue_tasks: int
    due_today: int
    active_projects: int
    active_habits: int
    habits_done_today: int
    events_today: int
    classes_today: int
    stored_resources: int


class WorkspaceSummary(BaseModel):
    date: date
    timezone: str
    counts: WorkspaceCounts
    overdue: list[SummaryTask]
    due_today: list[SummaryTask]
    agenda: list[SummaryAgendaItem]
    habits: list[SummaryHabit]
    truncated: bool  # some list kept only its first items; use the module tools for the rest
    unavailable: list[str]  # sections that could not be read


def _count(conn: sqlite3.Connection, sql: str) -> int:
    try:
        row = conn.execute(sql).fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0]) if row and row[0] is not None else 0


def _summary_task(task: Any) -> SummaryTask:
    due = task.due_date.isoformat() if task.due_date else (task.due_at[:16] if task.due_at else None)
    return SummaryTask(
        id=task.id,
        title=_clip(task.title) or "",
        priority=task.priority,
        due=due,
        days_overdue=task.days_overdue,
        project=_clip(task.project_name, 80),
    )


def _is_class(entry: Any) -> bool:
    return "class" in entry.source_type or entry.kind == "class"


def _workspace_summary(ctx: ToolContext, args: WorkspaceSummaryArgs) -> WorkspaceSummary:
    with closing(_read_only(ctx)) as conn:
        zone = args.timezone or default_timezone(conn) or FALLBACK_TIMEZONE
        if zone not in _timezones():
            raise ToolError("invalid_timezone", "Zona horaria no válida: usa un nombre IANA como Europe/Madrid.")
        today = build_today(conn, zone, datetime.now(UTC))
        counts = WorkspaceCounts(
            open_tasks=_count(
                conn,
                "SELECT count(*) FROM tasks t JOIN entities e ON e.id = t.id "
                "WHERE t.status IN ('pending','in_progress','on_hold') AND e.archived_at IS NULL",
            ),
            overdue_tasks=today.overdue.total,
            due_today=today.due_today.total,
            active_projects=_count(
                conn,
                "SELECT count(*) FROM projects p JOIN entities e ON e.id = p.id "
                "WHERE p.status IN ('planned','active') AND e.archived_at IS NULL",
            ),
            active_habits=_count(
                conn,
                "SELECT count(*) FROM habits h JOIN entities e ON e.id = h.id "
                "WHERE h.status = 'active' AND e.archived_at IS NULL",
            ),
            habits_done_today=sum(1 for h in today.habits.items if h.today_status == "done"),
            events_today=sum(1 for a in today.agenda.items if not _is_class(a)),
            classes_today=sum(1 for a in today.agenda.items if _is_class(a)),
            stored_resources=_count(
                conn,
                "SELECT count(*) FROM resources r JOIN entities e ON e.id = r.id WHERE e.archived_at IS NULL",
            ),
        )
    sections = {
        "overdue": today.overdue,
        "due_today": today.due_today,
        "agenda": today.agenda,
        "habits": today.habits,
        "projects": today.projects,
    }
    truncated = any(
        s.truncated or len(s.items) > TODAY_ITEMS_MAX for s in sections.values() if s is not today.projects
    )
    return WorkspaceSummary(
        date=today.date,
        timezone=zone,
        counts=counts,
        overdue=[_summary_task(t) for t in today.overdue.items[:TODAY_ITEMS_MAX]],
        due_today=[_summary_task(t) for t in today.due_today.items[:TODAY_ITEMS_MAX]],
        agenda=[
            SummaryAgendaItem(
                id=a.source_id,
                kind="class" if _is_class(a) else a.kind,
                title=_clip(a.title) or "",
                start=a.display_start,
                end=a.display_end,
                room=_clip(a.room, 60),
            )
            for a in today.agenda.items[:TODAY_ITEMS_MAX]
        ],
        habits=[
            SummaryHabit(id=h.id, name=_clip(h.name) or "", preferred_time=h.preferred_local_time, today=h.today_status)
            for h in today.habits.items[:TODAY_ITEMS_MAX]
        ],
        truncated=truncated,
        unavailable=[name for name, s in sections.items() if s.status != "ready"],
    )


# ── get_activity_log ─────────────────────────────────────────────────────────


class ActivityLogArgs(_Strict):
    actor: Literal["user", "agent", "automation", "system"] | None = None
    result: Literal["success", "denied", "failed", "confirmation_required"] | None = None
    limit: Annotated[int, Field(ge=1, le=ACTIVITY_MAX)] = 20
    cursor: Annotated[str, Field(max_length=128)] | None = Field(
        default=None, description="`next_cursor` de la página anterior."
    )


class ActivityItem(BaseModel):
    occurred_at: str
    actor: str
    origin: str
    action: str
    tool: str | None
    entity_type: str | None
    entity_id: str | None
    affected_count: int | None
    result: str
    error_code: str | None
    tainted: bool


class ActivityLogPage(BaseModel):
    items: list[ActivityItem]
    next_cursor: str | None


def _activity(ctx: ToolContext, args: ActivityLogArgs) -> ActivityLogPage:
    with closing(_read_only(ctx)) as conn:
        try:
            page = list_activity(conn, actor=args.actor, result=args.result, limit=args.limit, cursor=args.cursor)
        except ValueError:
            raise ToolError("invalid_cursor", "El cursor no es válido: vuelve a pedir la primera página.") from None
    return ActivityLogPage(
        items=[
            # Only the fixed columns: the redacted arguments and their hash stay out.
            ActivityItem(
                occurred_at=row["occurred_at"],
                actor=row["actor_type"],
                origin=row["origin"],
                action=row["action"],
                tool=row["tool_name"],
                entity_type=row["entity_type"],
                entity_id=row["entity_id"],
                affected_count=row["affected_count"],
                result=row["result"],
                error_code=row["error_code"],
                tainted=bool(row["tainted"]),
            )
            for row in page["items"]
        ],
        next_cursor=page["next_cursor"],
    )


# ── get_pending_confirmations ────────────────────────────────────────────────


class PendingConfirmation(BaseModel):
    id: str
    tool: str
    summary: str
    affected_count: int | None
    risk: str
    requested_by: str  # actor that asked: agent, user…
    created_at: str
    expires_at: str
    seconds_left: int


class PendingConfirmationList(BaseModel):
    items: list[PendingConfirmation]
    total_listed: int
    note: str


def _seconds_left(expires_at: str, now: datetime) -> int:
    try:
        moment = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return 0
    return max(0, int((moment - now).total_seconds()))


def _pending(ctx: ToolContext, args: NoArgs) -> PendingConfirmationList:
    actions = getattr(ctx.state, "actions", None)
    if actions is None:
        raise ToolError("confirmation_unavailable", "Las confirmaciones no están disponibles ahora.", retryable=True)
    with closing(actions.open()) as conn:
        actions.expire_due(conn)
        page = actions.list_confirmations(conn, "pending", limit=CONFIRMATIONS_MAX)
    now = datetime.now(UTC)
    items = [
        PendingConfirmation(
            id=row["id"],
            tool=row["tool_name"],
            summary=_clip(row["summary"], 240) or "",
            affected_count=row["affected_count"],
            risk=row["risk"],
            requested_by=row["actor_type"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            seconds_left=_seconds_left(row["expires_at"], now),
        )
        for row in page["items"]
    ]
    return PendingConfirmationList(
        items=items,
        total_listed=len(items),
        note="Solo el usuario las aprueba o rechaza, en el aviso de la pantalla. Tú no puedes decidirlas.",
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_voice_status",
        description="Estado de la voz: modo, motores activos y disponibilidad. No devuelve audio ni transcripciones.",
        domain="system",
        args_model=NoArgs,
        result_model=VoiceStatus,
        permission="system.read",
        risk=RiskClass.READ,
        handler=get_voice_status,
        idempotent=True,
        timeout_s=5.0,
    ),
    ToolSpec(
        name="get_workspace_summary",
        description="Resumen del Workspace: recuentos y elementos de hoy (tareas, hábitos, eventos, clases).",
        domain="system",
        args_model=WorkspaceSummaryArgs,
        result_model=WorkspaceSummary,
        permission="system.read",
        risk=RiskClass.READ,
        handler=_workspace_summary,
        errors=("validation_error", "invalid_timezone"),
        idempotent=True,
        timeout_s=15.0,
    ),
    ToolSpec(
        name="get_activity_log",
        description=(
            "Actividad reciente del agente y del usuario, en una vista de solo lectura sin secretos "
            "ni argumentos. No es la auditoría cruda."
        ),
        domain="system",
        args_model=ActivityLogArgs,
        result_model=ActivityLogPage,
        permission="system.read",
        risk=RiskClass.READ,
        handler=_activity,
        errors=("validation_error", "invalid_cursor"),
        idempotent=True,
        timeout_s=15.0,
    ),
    ToolSpec(
        name="get_pending_confirmations",
        description="Lista las confirmaciones pendientes (resumen y caducidad). Solo se aprueban o rechazan desde la GUI.",
        domain="system",
        args_model=NoArgs,
        result_model=PendingConfirmationList,
        permission="system.read",
        risk=RiskClass.READ,
        handler=_pending,
        errors=("confirmation_unavailable",),
        idempotent=True,
        timeout_s=5.0,
    ),
)
