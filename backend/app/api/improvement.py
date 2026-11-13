"""Mounts the improvement REST surface (`/api/v1/improvement`) through router discovery.

The routes live in `app.services.improvement_api`. The security guard requires the
session token; approvals still need the confirmation gate on `app.state`.
"""

from __future__ import annotations

from app.services.improvement_api import router

__all__ = ["router"]
