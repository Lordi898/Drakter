"""Lo único que hay que tocar si el sistema integrado usa otros nombres.

Los valores salen de backend/CONTRACT.md y del dossier (F04, F05, F07, F11, F17).
Las rutas de confirmaciones y herramientas no están congeladas en ninguna rama:
son la expectativa de este banco y hay que contrastarlas al integrar. Sobrescribe
con `--contract archivo.json`, cuyas claves de primer nivel reemplazan a estas.
"""

from __future__ import annotations

from typing import Any

CONTRACT: dict[str, Any] = {
    "env": {},
    "routes": {
        "auth_check": "/api/v1/auth/check",
        "confirmations": "/api/v1/confirmations",
        "confirmation_detail": "/api/v1/confirmations/{id}",
        "confirmation_approve": "/api/v1/confirmations/{id}/approve",
        "tool_call": "/api/v1/agent/tools/call",
        "vault_files": "/api/v1/vault/files",
        "vault_import": "/api/v1/vault/import",
        "vault_archive": "/api/v1/vault/archives/extract",
        "memory_search": "/api/v1/memory/search",
    },
    # Credenciales por principal dentro de session.json (dossier F05).
    "principals": {
        "gui_renderer": "token",
        "gui_approver": "approver_token",
        "agent": "agent_token",
    },
    "tables": {"pending_actions": "pending_actions", "audit_events": "audit_events"},
    # Herramientas que el banco usa como cebo.
    "tools": {"destructive": "delete_task", "not_allowed": "terminal"},
}
