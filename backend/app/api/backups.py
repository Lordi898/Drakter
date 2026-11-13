"""Monta la API de copias (`/api/v1/backups`) por el autodescubrimiento de routers.

Las rutas viven en `app.services.backup_api`. Borrar pasa por `ActionService`
(`app.services.backup_actions`); restaurar no tiene ruta: ver ese módulo.
"""

from __future__ import annotations

from app.services.backup_api import router

__all__ = ["router"]
