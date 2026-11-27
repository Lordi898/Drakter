"""`get_self_profile`: what Drakter is, what it can do right now, and the machine it runs on.

Everything is read from the running backend (registry, permissions, subsystems, hardware
tracker); nothing comes from the model or from memory. The hardware part is re-probed when
stale, so on another computer it describes that computer.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
import tomllib
from datetime import UTC, datetime
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict

from app.integrations.hermes.settings import HERMES_COMMIT
from app.services.awareness import STARTED_AT, STARTED_MONOTONIC
from app.services.hardware import HardwareChange, HardwareProfile, LiveResources, live
from app.tools.spec import RiskClass, ToolContext, ToolSpec
from app.tools.system import AgentStatus, _agent_status

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
# What the configuration enforces (home.py disables Hermes' own toolsets; the gate does the rest).
LIMITS: Final = (
    "Sin acceso a internet: no navega ni descarga.",
    "Sin terminal ni ejecución de programas.",
    "Archivos solo dentro de las carpetas permitidas del almacén.",
    "Sin servicios externos (correo, calendarios en la nube, mensajería).",
    "No aprueba confirmaciones: las decide el usuario en la pantalla.",
    "No cambia sus permisos, sus reglas de seguridad ni la auditoría.",
    "Solo actúa cuando el usuario le habla o le encarga un trabajo en segundo plano.",
)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Subsystems(BaseModel):
    voice_installed: bool
    voice_connected: bool | None
    memory_backend: str | None
    memory_available: bool | None
    jobs_running: int | None
    pending_confirmations: int | None


class KnownMachineView(BaseModel):
    label: str
    first_seen_at: str
    last_seen_at: str
    current: bool


class HardwareView(BaseModel):
    profile: HardwareProfile | None
    now: LiveResources
    on_this_machine_since: str | None
    latest_change: HardwareChange | None
    known_machines: list[KnownMachineView]


class SelfProfile(BaseModel):
    name: str
    version: str | None
    code_commit: str | None
    hermes_commit: str
    agent: AgentStatus
    backend_started_at: str
    backend_uptime_s: int
    tools_available: int
    tool_domains: list[str]
    limits: list[str]
    subsystems: Subsystems
    hardware: HardwareView


@lru_cache(maxsize=1)
def _version() -> str | None:
    try:
        return metadata.version("drakter-backend")
    except metadata.PackageNotFoundError:
        pass
    try:  # a checkout run with `uv run`/venv does not install the project itself
        with (REPO_ROOT / "backend" / "pyproject.toml").open("rb") as handle:
            return str(tomllib.load(handle)["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return None


@lru_cache(maxsize=1)
def _commit() -> str | None:
    """The code's commit when it runs from a checkout; a package has no .git and says None."""
    if not (REPO_ROOT / ".git").exists():
        return None
    try:
        out = subprocess.run(  # noqa: S603, S607 - fixed arguments, no shell
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False,
        )  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return None
    commit = out.stdout.strip()
    return commit if out.returncode == 0 and commit else None


async def _subsystems(state: Any) -> Subsystems:
    voice = getattr(state, "voice", None)
    connected = None
    if voice is not None:
        try:
            connected = bool(voice.snapshot().connected)
        except Exception:  # noqa: BLE001
            connected = None
    memory = getattr(state, "memory_service", None)
    backend = available = None
    if memory is not None:
        try:
            status = memory.status()
            backend, available = status.backend, status.available
        except Exception:  # noqa: BLE001
            pass
    jobs = None
    manager = getattr(state, "job_manager", None)
    if manager is not None:
        try:
            jobs = sum(1 for job in await manager.status() if job.running)
        except Exception:  # noqa: BLE001
            jobs = None
    pending = None
    actions = getattr(state, "actions", None)
    if actions is not None:
        pending = await asyncio.to_thread(_count_pending, actions)
    return Subsystems(
        voice_installed=voice is not None,
        voice_connected=connected,
        memory_backend=backend,
        memory_available=available,
        jobs_running=jobs,
        pending_confirmations=pending,
    )


def _count_pending(actions: Any) -> int | None:
    try:
        conn = actions.open()
        try:
            row = conn.execute(
                "SELECT count(*) FROM pending_confirmations WHERE status = 'pending' AND expires_at > ?",
                (datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),),
            ).fetchone()
            return int(row[0])
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        return None


def _hardware(state: Any) -> HardwareView:
    awareness = getattr(state, "awareness", None)
    tracker = getattr(awareness, "tracker", None)
    if tracker is None:
        return HardwareView(profile=None, now=live(None), on_this_machine_since=None, latest_change=None, known_machines=[])
    if tracker.profile is None:
        tracker.refresh()  # first call before the startup probe ended: worth the wait
    else:
        tracker.refresh_if_stale()
    profile = tracker.profile
    key = profile.machine_key if profile else None
    machines = [
        KnownMachineView(label=m.label, first_seen_at=m.first_seen_at, last_seen_at=m.last_seen_at, current=m.machine_key == key)
        for m in tracker.machines
    ]
    since = next((m.first_seen_at for m in machines if m.current), None)
    return HardwareView(
        profile=profile,
        now=live(tracker.data_dir),
        on_this_machine_since=since,
        latest_change=tracker.change,
        known_machines=machines,
    )


async def get_self_profile(ctx: ToolContext, args: NoArgs) -> SelfProfile:
    state = ctx.state
    registry = getattr(getattr(state, "agent_runtime", None), "registry", None)
    specs = registry.catalog() if registry is not None else ()
    permissions = getattr(registry, "permissions", None)
    usable = [s for s in specs if permissions is None or permissions.allows(s.permission)]
    hardware = await asyncio.to_thread(_hardware, state)
    return SelfProfile(
        name="Drakter",
        version=_version(),
        code_commit=await asyncio.to_thread(_commit),
        hermes_commit=HERMES_COMMIT[:12],
        agent=_agent_status(state),
        backend_started_at=STARTED_AT.isoformat(timespec="seconds").replace("+00:00", "Z"),
        backend_uptime_s=int(time.monotonic() - STARTED_MONOTONIC),
        tools_available=len(usable),
        tool_domains=sorted({s.domain for s in usable}),
        limits=list(LIMITS),
        subsystems=await _subsystems(state),
        hardware=hardware,
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_self_profile",
        description=(
            "Quién es Drakter ahora: versión, modelo, herramientas y límites, subsistemas (voz, "
            "memoria, trabajos) y el equipo en el que corre (CPU, RAM, GPU, sistema, batería, "
            "recursos libres y cambios de equipo detectados)."
        ),
        domain="system",
        args_model=NoArgs,
        result_model=SelfProfile,
        permission="system.read",
        risk=RiskClass.READ,
        handler=get_self_profile,
        idempotent=True,
        timeout_s=10.0,
    ),
)
