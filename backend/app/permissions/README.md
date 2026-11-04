# Permisos, confirmaciones y auditoría

Modelo de amenaza: el modelo y Hermes no son confiables. La frontera es este código.

## Piezas

| Archivo | Qué hace |
|---|---|
| `permissions/engine.py` | `PermissionEngine.evaluate` → allow, confirm o deny. Gana la regla más exigente |
| `permissions/models.py` | `ActionSpec`, `ActionRegistry`, `ActorContext`, `Principal` |
| `permissions/tool_gate.py` | Adaptadores `BackendToolGate`, `BackendAuditSink` y `tool_action_spec` |
| `permissions/setup.py` | `install_security`, `start_security`, `stop_security` |
| `services/actions.py` | `ActionService`: único camino de escritura confirmable |
| `audit/writer.py` | `write` (falla cerrado), `filter_params`, `list_events` |
| `tools/dispatcher.py` | `dispatch(tool, raw_args, ctx, actions=...)` para MCP, REST y DevProvider |
| `api/confirmations.py` | Rutas de la GUI y de Electron main |
| `api/activity.py` | `GET /api/v1/activity`, lectura de auditoría con cursor |

## Conexión en `app/main.py`

Los routers entran por autodescubrimiento. Falta enlazar el servicio en `_install_services` y en `lifespan`:

```python
# _install_services
actions = install_security(app, settings, agent_grants_path=REPO / "agent/configuration/permissions.json", events=<EventSink>)
# registrar aquí: actions.registry.register(...), o tool_action_spec(...) por cada ToolSpec
# lifespan, después de migrate y antes de on_ready()
await start_security(app)
# al apagar
await stop_security(app)
```

Sin esto, las rutas responden 503 `confirmation_unavailable`. `start_security` aborta el arranque si falta el esquema.

## Rutas

| Método y ruta | Rol |
|---|---|
| `GET /api/v1/confirmations?status=&limit=&cursor=` | `ui` |
| `GET /api/v1/confirmations/{id}` | `ui` |
| `POST /api/v1/confirmations/{id}/approve` `{params_hash}` | `approver` |
| `POST /api/v1/confirmations/{id}/reject` | `approver` |
| `GET /api/v1/activity` | `ui` |

La matriz la aplica `SecurityGuardMiddleware`. El token `approver` solo vive en Electron main y llega por stdin.

Flujo de main: `GET` del detalle con `ui` → `dialog.showMessageBox` con el foco en Cancelar → `approve` con `approver`.

Un solo uso: la transición atómica a `approved` y `executing` con estado, `args_hash` y caducidad en el `WHERE`. `pending_confirmations.args_hash` es el nombre de la columna; en la API solo existe `params_hash`.

## Reglas

- Lo no registrado no existe. El registro se cierra al arrancar.
- `permission` es `<dominio>.<operación>`. `permissions`, `audit` y `confirmations` no admiten escritura, ni con comodín.
- Confirman: riesgo `confirm`, `.delete`, `.execute`, `.admin`, 10 o más entidades en una llamada o acumuladas en el turno, y escrituras de turno contaminado. `bulk_threshold` se lee de `settings`, limitado a 2..100.
- `turn_id`, `session_id` y `tainted` los pone el backend, nunca los argumentos.
- Los campos fuera de `audit` no se guardan. Un campo con nombre de secreto no se puede auditar.
- Prohibido `INSERT OR REPLACE` y upsert sobre `pending_confirmations` y `audit_events`.

Comprobación: `tests/critical/check_confirmations.py`.
