# Contrato de hábitos, calendario y asignaturas

Congelado para `drakter/habitos-calendario`. Fuente: `backend/app/schemas/{habits,calendar,subjects}.py`, `backend/app/schemas/ddl_habits_calendar.sql`, `app/services/habits_calendar_support.py` y `app/tools/habits_calendar_toolspec.py`. Los hallazgos C-xx están en el dossier de auditoría.

## Reglas comunes

- Capas: `api/<m>.py` (rutas finas) → `services/<m>.py` (reglas, transacción, auditoría) → `repositories/<m>.py` (SQL parametrizado con `sqlite3`, sin reglas). `tools/<m>.py` (autodescubierto, `TOOLS: tuple[ToolSpec, ...]`) llama a servicios, nunca a repositorios ni SQL.
- Los servicios son síncronos, reciben `(conn, ctx, ...)` y usan `transaction(conn)`. Mutación y `record_audit` van en la misma transacción. Las rutas son `def` (no `async`), con `Depends(get_db)` y `Depends(rest_context)`.
- Errores con `AppError(code, message, status)`: `not_found` 404, `conflict` 409, `revision_mismatch` 412, `invalid_rrule` 422, `invalid_timezone` 422, `nonexistent_local_time` 422, `window_too_large` 422.
- PATCH: solo `model_fields_set`. `If-Match: <revision>` opcional, se pasa a `touch_entity`. Las salidas exponen `revision`, `archived_at`, `created_at` y `updated_at` de `entities`.
- Listas: `{"items": [...], "next_cursor": str|null}`, `limit` con `bounded_limit`, cursor con `encode_cursor`. Excluyen archivados salvo `include_archived=true`.
- `params` de auditoría: lista blanca de ids, fechas y estados. Nunca títulos, notas ni descripciones.
- Destructivo: el servicio llama a `request_confirmation(...)` dentro de una transacción y devuelve `ConfirmationRef`; la ruta responde 202 con ese cuerpo. El ejecutor real se registra con `@confirmed_action("<tool>")`, recibe los `args` guardados y audita con `result="success"`. No existe parámetro `force` ni ruta para saltárselo. Aprobar es de `POST /api/v1/confirmations/{id}/approve`, del pipeline común.
- Cada `router = APIRouter(prefix="/api/v1", tags=[...])`. `main.py` no se toca: lo registra el integrador.
- Texto de terceros (títulos, notas) es dato: nunca se interpreta ni se añade a instrucciones.

## Recurrencia y tiempo (`services/calendar_recurrence.py`)

```python
@dataclass(frozen=True)
class Rule: freq: str; interval: int; count: int | None; until: date | None
            byday: tuple[str, ...]; bymonthday: tuple[int, ...]
def parse_rrule(text: str) -> Rule                  # AppError invalid_rrule. FREQ=DAILY|WEEKLY|MONTHLY|YEARLY, INTERVAL, COUNT, UNTIL, BYDAY, BYMONTHDAY
def normalize_rrule(text: str) -> str               # forma canónica para guardar
def expand_dates(rule: Rule, dtstart: date, window_start: date, window_end_exclusive: date,
                 limit: int = 1000) -> list[date]   # DTSTART cuenta como primera ocurrencia; COUNT se cuenta desde DTSTART, no desde la ventana
def rule_matches(rule: Rule, dtstart: date, day: date) -> bool
def to_utc(local: datetime, tz: str, *, strict: bool) -> datetime
    # strict=True: hora inexistente -> AppError nonexistent_local_time; ambigua -> primera (fold=0)
    # strict=False (series): inexistente usa el desfase anterior al hueco; ambigua -> primera (RFC 5545 §3.3.5)
def utc_iso(value: datetime) -> str                 # 'AAAA-MM-DDTHH:MM:SSZ'
def to_display(utc: datetime, tz: str) -> str       # 'AAAA-MM-DDTHH:MM:SS' sin desfase
def today_in(tz: str) -> date
```
La serie se expande en lectura sobre hora local y solo en ventana acotada; nunca se materializa.

## Hábitos (`api/habits.py`)

`GET,POST /habits`; `GET,PATCH /habits/{id}`; `POST /habits/{id}/archive|unarchive`; `PUT /habits/{id}/records/{date}` (upsert: no hay duplicados por periodo); `GET /habits/{id}/records?from=&to=`; `GET /habits/{id}/history?from=&to=` (máx. 400 días, por defecto 30); `GET /habits/{id}/statistics?from=&to=`.

- Sin borrado definitivo: se archiva. `habit_records` nunca se borran.
- Cambiar `rrule`: cierra la versión vigente (`valid_until = efectiva`) y abre otra (`valid_from = efectiva`). Si la versión vigente empieza ese mismo día, se sustituye su `rrule`. Editar nunca toca registros.
- `dtstart` de cada versión: `valid_from`. Programado en un día = hay versión con `valid_from <= día < valid_until`, dentro de `start_date..end_date`, y `rule_matches`.
- Registrar en un día futuro (zona del hábito): `conflict`. Registrar un día no programado se permite.
- Estadísticas: `unrecorded` = programados pasados sin registro, sin contar hoy. `completion_rate = done/(scheduled-skipped)`. Racha: días programados consecutivos con `done`; `skipped` ni suma ni rompe; hoy sin registro no rompe.
- `goal_project_id` debe existir en `projects`. `goal_note` ↔ columna `target_note`. Recordatorios: se guarda la definición (`reminder_enabled` + `preferred_local_time`); la entrega queda fuera.

Herramientas (`tools/habits.py`): `create_habit`, `get_habit`, `update_habit`, `archive_habit`, `list_habits`, `register_habit_completion`, `get_habit_history`, `get_habit_statistics`.

## Calendario (`api/calendar.py`)

`GET,POST /calendar/events`; `GET,PATCH,DELETE /calendar/events/{id}`; `GET,POST /calendar/events/{id}/exceptions`; `GET,POST /calendar/time-blocks`; `GET,PATCH,DELETE /calendar/time-blocks/{id}`; `GET /calendar/agenda?from=&to=&timezone=&types=`; `GET /calendar/availability?local_start=&local_end=&timezone=`; `GET /calendar/free-slots?from=&to=&timezone=&min_minutes=`; `GET /calendar/overlaps?from=&to=&timezone=`.

- `POST` y `PATCH` guardan `local_*` + `timezone`, derivan `*_utc` con `to_utc(strict=True)`, y responden `EventWriteResult`/`TimeBlockWriteResult`. Los solapes **avisan, no bloquean**.
- `services/calendar.py` expone al resto: `agenda(conn, from_date, to_date, tz, types=None, limit=2000) -> AgendaResponse`. Ventana máxima 370 días (`window_too_large`). `to` es exclusivo.
- La agenda combina eventos (expandidos, con excepciones), bloques y clases (`subjects_service.project_class_sessions`). Excluye archivados, y `cancelled` salvo que se filtre por estado. Un evento recurrente con `starts_at_utc`/`ends_at_utc` conserva en la fila los de su primera ocurrencia.
- Duración de cada ocurrencia: la de hora local de la serie. `occurrence_id = f"{source_id}:{occurrence_local_start}"`.
- Solapes: dos ocurrencias con hora se pisan si `a.start < b.end and b.start < a.end` en UTC. Día completo y `reminder` no cuentan. `cancelled`, `skipped` y `done` tampoco.
- Para una serie nueva, los conflictos se buscan en sus primeras 50 ocurrencias en 180 días.
- `task_id` debe existir en `tasks`.
- `DELETE` de evento y bloque: confirmación (`delete_event`, `delete_time_block`). Una excepción `cancelled` no pide confirmación: es reversible y afecta a una sola ocurrencia.
- Cambiar el rango temporal de una serie con excepciones: `conflict`.

Herramientas (`tools/calendar.py`): `create_event`, `get_event`, `update_event`, `delete_event`, `create_event_exception`, `create_time_block`, `update_time_block`, `move_time_block`, `delete_time_block`, `get_schedule`, `check_availability`.

## Asignaturas (`api/subjects.py`)

`GET,POST /subjects`; `GET,PATCH,DELETE /subjects/{id}`; `POST /subjects/{id}/archive|unarchive`; `GET,POST /subjects/{id}/sessions`; `GET,PATCH,DELETE /class-sessions/{id}`; `POST /class-sessions/{id}/exceptions`; `GET /timetable?on=`; `GET /subjects/{id}/resources`.

- `services/subjects.py` expone `project_class_sessions(conn, from_date, to_date, tz) -> list[AgendaItem]`, con la misma regla de excepciones (`occurrence_local_start = 'AAAA-MM-DDTHH:MM:SS'`), `kind="class"`, `color` de la asignatura y título = nombre. Sin filas copiadas: ROADMAP «sin duplicar sesiones».
- `DELETE /subjects/{id}` y `/class-sessions/{id}`: confirmación (`delete_subject`, `delete_class_session`). Con sesiones o tareas vinculadas (`tasks.subject_id`), `conflict` con el recuento en el mensaje; primero hay que archivar o borrar sesiones.
- `GET /subjects/{id}/resources`: devuelve `{"items": []}` hasta que exista el módulo de relaciones; se declara en el informe.
- Validar que las clases no se pisan entre sí: aviso `conflicts` en la respuesta de creación.

Herramientas (`tools/subjects.py`): `create_subject`, `get_subject`, `update_subject`, `list_subjects`, `create_class_session`, `update_class_session`, `delete_class_session`, `create_schedule_exception`, `get_timetable`, `get_subject_resources`.

## Herramientas

Contrato: `git show drakter/agente-hermes:backend/app/integrations/hermes/CONTRACT.md` §1. Se importa todo de `app.tools.habits_calendar_toolspec` (adaptador). Cada herramienta: `ToolSpec(name, description, domain, args_model, result_model, permission="<dominio>.read|write", risk, handler=service_handler(name, servicio), errors=(...), audit={...})`.

- `args_model` con `extra="forbid"` definido en el propio archivo si no vale un schema; `result_model` siempre `BaseModel` (envuelve listas en un modelo con `items`).
- El servicio envuelto tiene firma `(conn, ctx, args) -> result_model`.
- `risk`: lectura `RiskClass.READ`; `create/update/register/archive/move` `RiskClass.WRITE`; `delete_*` `RiskClass.CONFIRM` con `summarize` obligatorio y `permission` `<dominio>.write`.
- La confirmación de CONFIRM la impone `ToolGate` antes del handler, así que el handler de `delete_*` llama al ejecutor registrado con `@confirmed_action`, nunca a `request_confirmation`. Las rutas REST sí usan `request_confirmation`.
- `audit`: `"log"` solo para ids, fechas y estados; títulos, notas y descripciones `"omit"`.
- No hay herramienta de aprobar. `returns_untrusted=False`: datos propios del usuario; el contenido libre sigue siendo dato.
