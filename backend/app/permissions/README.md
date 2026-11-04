# Permisos, confirmaciones y auditoría

Modelo de amenaza: el modelo y Hermes no son confiables. La frontera es este código.

## Piezas

| Archivo | Qué hace |
|---|---|
| `permissions/engine.py` | `PermissionEngine.evaluate` → allow, confirm o deny. Gana la regla más exigente |
| `permissions/models.py` | `ActionSpec`, `ActionRegistry`, `ActorContext`, `Principal` |
| `permissions/credentials.py` | `ApprovalSigner` (token HMAC) y entrega del token de approver |
| `permissions/tool_gate.py` | Adaptadores `BackendToolGate`, `BackendAuditSink` y `tool_action_spec` |
| `permissions/setup.py` | `install_security`, `start_security`, `stop_security` |
| `services/actions.py` | `ActionService`: único camino de escritura confirmable |
| `audit/writer.py` | `write` (falla cerrado), `filter_params`, `list_events` |
| `tools/dispatcher.py` | `dispatch(tool, raw_args, ctx, actions=...)` para MCP, REST y DevProvider |
| `api/confirmations.py` | Rutas de la GUI y de Electron main |

## Conexión en `app/main.py`

```python
# tras crear la app e incluir routers
actions = install_security(app, settings, agent_grants_path=REPO / "agent/configuration/permissions.json", events=<EventSink>)
# registrar acciones aquí: actions.registry.register(...), o tool_action_spec(...) por cada ToolSpec
# en lifespan, después de migrate
await start_security(app, settings)
# al apagar
await stop_security(app, settings)
```

Requiere `drakter-contracts` en `pyproject.toml`. `start_security` aborta el arranque si falta el esquema.

## Rutas

| Método y ruta | Credencial |
|---|---|
| `GET /api/v1/confirmations?status=` | GUI |
| `GET /api/v1/confirmations/{id}` | GUI |
| `POST /api/v1/confirmations/{id}/approval-token` | approver |
| `POST /api/v1/confirmations/{id}/approve` `{params_hash, approval_token}` | approver |
| `POST /api/v1/confirmations/{id}/reject` | approver |

Approver significa: bearer de sesión, cabecera `X-Drakter-Approver` y **ninguna** cabecera `Origin`. La cabecera no está en la lista CORS, así que el renderer no puede enviarla. Electron main lee `runtime_dir/approver.json` (0600) una vez y lo borra.

Flujo de main: `approval-token` devuelve detalle y token → `dialog.showMessageBox` con el foco en Cancelar → `approve`.

## Reglas

- Lo no registrado no existe. El registro se cierra al arrancar.
- `permission` es `<dominio>.<operación>`. `permissions`, `audit` y `confirmations` no admiten escritura, ni con comodín.
- Confirman: riesgo `confirm`, `.delete`, `.execute`, `.admin`, 10 o más entidades en una llamada o acumuladas en el turno, y escrituras de turno contaminado. `bulk_threshold` se lee de `settings`, limitado a 2..100.
- `turn_id`, `session_id` y `tainted` los pone el backend, nunca los argumentos.
- Los campos fuera de `audit` no se guardan. Un campo con nombre de secreto no se puede auditar.
- Prohibido `INSERT OR REPLACE` y upsert sobre `pending_confirmations` y `audit_events`.

Comprobación: `tests/critical/check_confirmations.py`.
