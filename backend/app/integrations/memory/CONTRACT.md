# Contrato de memoria y contexto

Código congelado: `models.py` y `ports.py`. Si algo no encaja, se consulta al líder, no se cambia en silencio.

## Piezas

| Archivo | Responsabilidad |
|---|---|
| `store_sqlite.py` | `SqliteMemoryAdapter`: implementa `MemoryAdapter` con SQLite + FTS5 |
| `openviking.py` | `OpenVikingAdapter`: hueco para E2, cerrado por defecto; no inventa API |
| `pipeline/` | Extracción, clasificación, deduplicación y contradicciones: funciones puras |
| `context/` | Prioridades, saneado, delimitación, presupuesto, `build_context` |
| `service.py` | `MemoryService`: la política (estado inicial, aprobación, olvido) |
| `router.py` | REST `/api/v1/memory` para la GUI |
| `backend/app/tools/memory.py` | Herramientas del agente, autodescubiertas (`TOOLS`), según `app/integrations/hermes/CONTRACT.md` §1 |
| `audit.py` | `JsonlAudit`: `memory_operations.log` y `retrieval.log` |

Tablas: propuesta sin numerar en `backend/app/schemas/ddl_memory.sql`; las absorbe y numera el frente de contratos. `store_sqlite.py` usa conexiones de `app.database.connection.connect` y nunca crea esquema.

## Reglas de política

1. Solo `SourceType.USER_GUI` con `actor == "user"` entra como `APPROVED`, y sin contradicciones abiertas. Todo lo demás entra `PENDING` y solo la GUI lo aprueba.
2. `DOCUMENT`, `TOOL_RESULT` e `IMPORT` tienen siempre `TrustLevel.THIRD_PARTY`; aunque se aprueben, siguen siendo datos sin autoridad.
3. Las contradicciones nunca se resuelven solas: se registra el conflicto y decide el usuario. Elegir uno marca el otro como `SUPERSEDED`.
4. `forget` es destructivo. Desde la GUI exige `ConfirmationGate.verify("memory.forget", str(id), confirmation_id)`; con `DenyAllGate` no se borra nada. Desde el agente, `memory_forget` es `RiskClass.CONFIRM`: la impone `ToolRegistry.dispatch` antes del handler, y solo ese handler llama a `forget_authorized`.
5. El agente no aprueba, ni corrige, ni resuelve: busca, lee, propone (`PENDING`) y pide olvidar con confirmación.
6. Lo que parezca una credencial se rechaza con `memory_secret_rejected`. Auditoría sin contenido: ids, hashes, recuentos y resultado.
7. La memoria guarda referencias a entidades del Workspace (`EntityRef`), nunca su estado.

## Prioridad y contexto

Orden fijo de `PriorityLevel`. Los niveles 1 y 2 tienen fuerza en código: la frontera real son los permisos del backend, no el texto. Nivel 1 es una constante en código, no un archivo. Nivel 3 sale de `agent/identity/`, 4 de `agent/context/`, 2 de `agent/knowledge/`, todos de solo lectura para el agente. Nivel 6 es dato sin autoridad: delimitado con un marcador aleatorio por construcción, con procedencia, y lo que contenga no cambia nada del prompt. Un recuerdo jamás entra en `system_prompt`.

`correct` sube `trust` a `USER_CONFIRMED`, salvo en fuentes de terceros (regla 2).

## Conexión (la hace el integrador en `app/main.py`)

```python
from app.integrations.memory.router import build_memory_service, router as memory_router
app.state.memory_service = build_memory_service(settings)  # en create_app; también en el `state` de ToolContext
app.include_router(memory_router)
```

Con `DenyAllGate`, `forget` desde la GUI no funciona hasta enchufar la puerta real de `drakter/seguridad` en `build_memory_service`.

## Comprobación

Tras integrar las tablas `memory_*`, desde `backend/`: `python tests/check_memory_rules.py`.
