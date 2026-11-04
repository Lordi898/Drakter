"""System tools. The first real tools, end to end."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from drakter_contracts.common import Instant
from pydantic import BaseModel, ConfigDict

from app.tools.spec import RiskClass, ToolContext, ToolSpec

_UNKNOWN = "unknown"


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentStatus(BaseModel):
    state: str
    provider: str | None = None
    model: str | None = None
    detail: str | None = None


class SystemStatus(BaseModel):
    backend: str
    now_utc: Instant
    agent_state: str
    tools_registered: int | None = None
    turn_active: bool | None = None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _agent_status(state: Any) -> AgentStatus:
    """Runtime parts may be missing while it starts or if Hermes is absent."""
    provider = getattr(getattr(state, "agent_runtime", None), "provider", None)
    if provider is None:
        return AgentStatus(state=_UNKNOWN)
    try:
        status = provider.status()
    except Exception:  # noqa: BLE001 - a status query must not take the tool down
        return AgentStatus(state=_UNKNOWN, provider=_text(getattr(provider, "name", None)))
    return AgentStatus(
        state=_text(getattr(status, "state", None)) or _UNKNOWN,
        provider=_text(getattr(provider, "name", None)),
        model=_text(getattr(status, "model", None)),
        detail=_text(getattr(status, "detail", None)),
    )


async def get_agent_status(ctx: ToolContext, args: NoArgs) -> AgentStatus:
    return _agent_status(ctx.state)


async def get_system_status(ctx: ToolContext, args: NoArgs) -> SystemStatus:
    runtime = getattr(ctx.state, "agent_runtime", None)
    registry = getattr(runtime, "registry", None)
    turns = getattr(runtime, "turns", None)
    catalog = getattr(registry, "catalog", None)
    active = getattr(turns, "active", None)
    return SystemStatus(
        backend="ok",
        now_utc=datetime.now(UTC),
        agent_state=_agent_status(ctx.state).state,
        tools_registered=len(catalog()) if callable(catalog) else None,
        turn_active=active() is not None if callable(active) else None,
    )


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_agent_status",
        description="Report the state of the agent, its provider and its model.",
        domain="system",
        args_model=NoArgs,
        result_model=AgentStatus,
        permission="system.read",
        risk=RiskClass.READ,
        handler=get_agent_status,
        idempotent=True,
        timeout_s=5.0,
    ),
    ToolSpec(
        name="get_system_status",
        description="Report the state of the Drakter backend and the current UTC time.",
        domain="system",
        args_model=NoArgs,
        result_model=SystemStatus,
        permission="system.read",
        risk=RiskClass.READ,
        handler=get_system_status,
        idempotent=True,
        timeout_s=5.0,
    ),
)
