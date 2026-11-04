"""Tools of the agent: common registry and MCP bridge. Contract in integrations/hermes."""

from drakter_contracts.tools import (
    ToolConfirmationRequired,
    ToolFailed,
    ToolOk,
    ToolOutcome,
    UntrustedEnvelope,
)

from app.tools.envelope import tool_confirmation, tool_failure, tool_ok, untrusted_envelope
from app.tools.gate import (
    AuditSink,
    DefaultToolGate,
    GateDecision,
    LogAuditSink,
    ToolAuditEvent,
    ToolGate,
    effective_risk,
)
from app.tools.mcp_bridge import (
    AGENT_TOOLS_PATH,
    MCP_SERVER_NAME,
    AgentToolsServer,
    build_agent_tools_app,
)
from app.tools.permissions import DEFAULT_PERMISSIONS_PATH, PermissionPolicy
from app.tools.registry import (
    ToolLoadError,
    ToolObserver,
    ToolRegistrationError,
    ToolRegistry,
    load_builtin_tools,
)
from app.tools.spec import AuditPolicy, RiskClass, ToolContext, ToolError, ToolHandler, ToolSpec
from app.tools.turns import ActiveTurn, TurnBusyError, TurnTracker

__all__ = [
    "AGENT_TOOLS_PATH",
    "DEFAULT_PERMISSIONS_PATH",
    "MCP_SERVER_NAME",
    "ActiveTurn",
    "AgentToolsServer",
    "AuditPolicy",
    "AuditSink",
    "DefaultToolGate",
    "GateDecision",
    "LogAuditSink",
    "PermissionPolicy",
    "RiskClass",
    "ToolAuditEvent",
    "ToolContext",
    "ToolError",
    "ToolConfirmationRequired",
    "ToolFailed",
    "ToolGate",
    "ToolHandler",
    "ToolLoadError",
    "ToolObserver",
    "ToolOk",
    "ToolOutcome",
    "ToolRegistrationError",
    "ToolRegistry",
    "ToolSpec",
    "TurnBusyError",
    "TurnTracker",
    "UntrustedEnvelope",
    "build_agent_tools_app",
    "effective_risk",
    "load_builtin_tools",
    "tool_confirmation",
    "tool_failure",
    "tool_ok",
    "untrusted_envelope",
]
