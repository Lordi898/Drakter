# Contrato de la base del backend

Interfaces congeladas de la base segura. Otro módulo solo puede depender de lo que aparece aquí.
Fuera de alcance: tablas de dominio, rutas de dominio, eventos WebSocket de negocio y Hermes.

## Arranque (D-14)

Único punto de entrada: `python -m app` desde `backend/`. Lo lanza Electron main y es su único cliente.

1. `app/__main__.py` pone `os.umask(0o077)` y aparta sus descriptores: stdin y stdout pasan a descriptores privados no heredables, fd 0 queda en `/dev/null` y fd 1 apunta a stderr. Ningún hijo hereda el canal y nada más puede escribir en él.
2. Lee por stdin **una línea** JSON `{"v":1,"ui":"<token>","approver":"<token>"}\n`, máximo 4 KiB. Cada token son 32 bytes en base64url sin relleno (43 caracteres) y deben ser distintos. Una línea inválida o EOF: mensaje genérico en stderr, código 2, sin eco de la entrada.
3. Enlaza y pone a escuchar en `127.0.0.1:0`. La dirección no es configurable y no hay `DRAKTER_HOST` ni `DRAKTER_PORT`. Un solo worker.
4. Tras completar el `lifespan` de arranque escribe en stdout **una línea** `{"v":1,"port":N}\n` y cierra ese canal. Si el arranque falla no la escribe y sale con código distinto de 0.
5. Mantiene stdin abierto. Al recibir EOF se apaga de forma ordenada (`timeout_graceful_shutdown=5`) y sale con 0. `SIGTERM` también apaga.

Las credenciales no pasan nunca por argv, entorno, disco ni logs. Ya no existe `session.json`.

- Uvicorn: `log_config=None`, `access_log=False`, `server_header=False`, `proxy_headers=False`, `ws="websockets-sansio"`, `ws_max_size=1048576`, `lifespan="on"`.
- `create_app(settings, *, credentials, port, on_ready) -> FastAPI` en `app/main.py`. No existe un `app` a nivel de módulo. Monta por autodescubrimiento todo `app/api/*.py` que exporte `router`, y nadie edita `main.py` para añadir rutas. Un módulo sin `router` es auxiliar y no se monta. Inicializa `app.state`: `settings`, `agent_runtime`, `agent_settings`, `event_hub`, `memory_service` y `reminders`. Un servicio de otro frente cuyo módulo no exista queda en `None`; un fallo al importarlo tumba el arranque. `docs_url`, `redoc_url` y `openapi_url` son `None`; `redirect_slashes=False`.
- Orden del `lifespan`: preparar directorios → `configure_logging` → `exclusive_instance` → `migrate` → `agent_runtime.start()` → `reminders.start()` → `on_ready()`. Al apagar, en orden inverso. Si `migrate` falla, el arranque falla.

## `app/core/config.py`

```python
BIND_HOST: Final = "127.0.0.1"

class Settings(BaseSettings):
    # env_prefix="DRAKTER_", extra="ignore", frozen=True
    # env_file = Path(user_config_dir("drakter")) / ".env"; respeta XDG_CONFIG_HOME
    data_dir: Path                          # por defecto user_data_dir("drakter")
    log_level: Literal["DEBUG","INFO","WARNING","ERROR"] = "INFO"
    # Propiedades: db_path = data_dir/"drakter.db", backups_dir = data_dir/"backups",
    #              logs_dir = data_dir/"logs"

def ensure_private_dir(path: Path) -> None: ...
def load_settings() -> Settings: ...
```

`python -m app` captura `ValidationError` de `load_settings`: imprime solo los nombres de los campos inválidos y sale con 1, sin valores.

`ensure_private_dir`: crea con 0700 y padres; si existe y es symlink, no es directorio o no es del usuario actual, lanza `ValueError`; si es del usuario, fuerza 0700.

## `app/core/logging.py`

```python
def configure_logging(level: str, logs_dir: Path) -> None: ...
def register_secret(value: str) -> None: ...
def redact(value: object) -> object: ...
class JsonFormatter(logging.Formatter): ...
```

- Una línea JSON por evento con `ts` (UTC ISO 8601), `level`, `logger`, `message` y los campos de `extra`. Salida a stderr y a `logs_dir/"backend.log"` (rotación 5 MiB, 3 copias, permisos 600, también las rotadas).
- Redacción en el formateador, sobre el texto final, incluidos `extra`, objetos no `str` y trazas de excepción, en tiempo lineal: primero se sustituyen los valores registrados, luego se trunca cada campo a 16 KiB y por último se aplican los patrones. Sustituye por `[REDACTED]`: valores registrados con `register_secret`; valores completos de claves que contengan `authorization`, `token`, `secret`, `password`, `api_key`, `api-key`, `apikey`, `cookie`, `credential` (sin distinguir mayúsculas, también anidadas, en listas de pares y con cualquier esquema, como `Basic`); `Bearer <x>`; `drakter.auth.<x>`; `sk-…`; y `<clave>=<valor>` o `"clave": "valor"` en texto libre con esas claves.
- `configure_logging` encamina también `uvicorn` y `uvicorn.error`, deja `uvicorn.access` sin handlers ni propagación (la línea de acceso incluye la consulta) y es idempotente: no duplica manejadores.

## `app/core/errors.py`

Los modelos `ErrorDetail`, `ErrorBody` y `ErrorEnvelope` vienen de `drakter_contracts.errors`.

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400,
                 details: list[ErrorDetail] | None = None): ...

def error_body_bytes(code: str, message: str, request_id: str,
                     details: list[ErrorDetail] | None = None) -> bytes: ...
def install_error_handlers(app: FastAPI) -> None: ...
```

- Todo error HTTP responde `{"error":{"code","message","request_id","details"}}` con `application/json`.
- Cubre `AppError`, `RequestValidationError` (422, código `validation_error`; `details` con `field`, `code` y `message`, jamás `input` ni `ctx`), `StarletteHTTPException` (`http_404`, `http_405`, …, con mensaje fijo, conservando sus cabeceras) y `Exception` (500, código `internal_error`, mensaje fijo, traza solo en el log).
- En validación, el mensaje se conserva para errores de plantilla de Pydantic y para `PydanticCustomError` sin `ctx`, cuyo texto escribimos nosotros. Un `PydanticCustomError` con `ctx`, cuyo texto puede interpolar lo recibido, y cualquier `ValueError` o `AssertionError` dan `Invalid value`.
- `request_id` sale de `request.scope["state"]["request_id"]`; si no está, `uuid4`. Nunca se toma de la petición del cliente.

## `app/core/bootstrap.py`

```python
class HandshakeError(Exception): ...
@dataclass(frozen=True, slots=True)
class Credentials:
    ui: SessionToken; approver: SessionToken

def take_standard_streams() -> tuple[int, int]: ...      # (control_in, control_out)
def read_credentials(fd: int) -> Credentials: ...
def announce_port(fd: int, port: int) -> None: ...
def watch_eof(fd: int, on_eof: Callable[[], None]) -> threading.Thread: ...
```

## `app/core/security.py`

```python
WS_SUBPROTOCOL: Final = "drakter.v1"
MAX_BODY_BYTES: Final = 1_048_576

class SessionToken:
    def __init__(self, value: str) -> None: ...         # registra con register_secret
    def matches(self, candidate: bytes) -> bool: ...    # hmac.compare_digest sobre bytes
    # __repr__ y __str__ nunca muestran el valor

class SecurityGuardMiddleware:                  # ASGI puro; http y websocket
    def __init__(self, app, *, credentials: Credentials, port: int): ...
```

`SecurityGuardMiddleware` es la capa más externa y no hay CORS. Por este orden:

1. Asigna `scope["state"]["request_id"] = str(uuid4())`; `lifespan` pasa sin más.
2. Exige que `scope["client"]` sea `127.0.0.1` (403 `forbidden_client`).
3. Exige exactamente una cabecera `Host`, igual a `127.0.0.1:<port>`. `localhost` ya no vale. Si no: 403 `forbidden_host`. Una petición sin `Host` o con dos la corta antes h11 con un 400 sin envelope; el guardia es la segunda barrera.
4. Cualquier cabecera `Origin`, sea cual sea su valor: 403 `forbidden_origin`.
5. Exige `Authorization: Bearer <token>` en http y websocket, una sola vez. Sin token válido: 401 `unauthorized` con `WWW-Authenticate: Bearer`. No hay token por consulta, cookie ni subprotocolo. Tampoco hay ruta pública ni excepción de preflight: `/health` exige token.
6. Aplica la matriz. Un token válido con el rol equivocado da 403 `permission_denied`.

| Ruta | `ui` | `approver` | otro o ninguno |
|---|---|---|---|
| `POST`/cualquier método en `/api/v1/confirmations/{id}/approve` y `/reject` | no | sí | 401 |
| Métodos que no son `GET`/`HEAD` en `/api/v1/storage-locations/**` y `/api/v1/permissions/**` | no | sí | 401 |
| Todo lo demás, incluidos `/health`, `/api/v1/**` y `WS /api/v1/events` | sí | no | 401 |

El token `agent` no existe en este puerto y da 401: `/mcp` es un listener aparte de otro módulo.

7. Límite de cuerpo: `Content-Length` mayor que `MAX_BODY_BYTES` o cuerpo en streaming que lo supera, 413 `file_too_large`.

En websocket, cualquier rechazo se hace antes de aceptar: se consume `websocket.connect` y se envía `websocket.close` con código 1008, de modo que el cliente recibe un rechazo del handshake. El guardia nunca registra cabeceras, consulta ni token. Registra `event`, `method`, `path` sin consulta y truncado a 256 caracteres, `status` y `request_id`.

## `app/api/`

- `health.py`: `GET /health` (`ui`) → `{"status":"ok"}`; hace `SELECT 1` con `connect` sin `create`, así una base desaparecida da 503. Si falla → `AppError("service_unavailable", ..., 503)`, sin detalles.
- `auth.py`: `GET /api/v1/auth/check` (`ui`) → `{"authenticated": true}`.
- `events.py`: `WS /api/v1/events?after_seq&boot_id`, único WebSocket, servidor→cliente sobre `app.state.event_hub` (`app/events/`, de `drakter/agente-hermes`). Si el cliente ofreció `drakter.v1`, acepta con ese subprotocolo; cualquier mensaje entrante cierra con 1003. Detalle en `app/integrations/hermes/CONTRACT.md`.

## `app/database/`

```python
# connection.py
def connect(db_path: Path, *, create: bool = False, migrating: bool = False) -> sqlite3.Connection: ...

# schema.py (migrator.py los reexporta; rompe el ciclo con backup.py)
SCHEMA_VERSION_TABLE: Final = "schema_version"
MIGRATIONS_DIR: Final = Path(__file__).resolve().parents[2] / "migrations"
class MigrationError(Exception): ...
def current_version(conn: sqlite3.Connection) -> int: ...

# migrator.py
@dataclass(frozen=True)
class MigrationResult:
    from_version: int; to_version: int; applied: tuple[str, ...]; backup: Path | None
def migrate(db_path: Path, backups_dir: Path, migrations_dir: Path = MIGRATIONS_DIR) -> MigrationResult: ...

# backup.py
class BackupError(Exception): ...
def create_backup(db_path: Path, backups_dir: Path, label: str) -> Path: ...
def verify_backup(backup_path: Path) -> None: ...
def verify_copy(backup_path: Path) -> None: ...  # como verify_backup sin exigir schema_version; solo copias propias pre-migrate y pre-restore
def restore_backup(db_path: Path, backups_dir: Path, backup_path: Path,
                   migrations_dir: Path = MIGRATIONS_DIR) -> Path: ...  # devuelve la copia previa o la cuarentena

# lock.py
class DatabaseInUse(Exception): ...
@contextmanager
def exclusive_instance(db_path: Path) -> Iterator[None]: ...  # flock no bloqueante sobre <db>.lock, 0600

# cli.py: python -m app.database.cli status|migrate|backup|restore <archivo>
```

- `connect`: sin `create=True`, una base inexistente lanza `FileNotFoundError` y no se crea: solo `migrate` y `create_backup`/`restore_backup` cuando corresponda la crean. Al crear usa `os.open` con `O_CREAT|O_EXCL|O_NOFOLLOW` y 0600; sobre una base existente no abre descriptor propio (cerrarlo cancelaría los bloqueos POSIX de SQLite) y usa `lstat` más comparación de inodo tras abrir. Fuerza 0600, rechaza con `ValueError` symlink o propietario ajeno, y aplica `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`, y por `setconfig` `SQLITE_DBCONFIG_DEFENSIVE` y `SQLITE_DBCONFIG_ENABLE_FKEY`, con `isolation_level=None` (transacciones explícitas). Verifica que WAL, el modo defensivo y `foreign_keys` han quedado activos. Un autorizador deniega por SQL escribir `foreign_keys`, `defer_foreign_keys`, `ignore_check_constraints` y `writable_schema`; solo el migrador, con `migrating=True`, queda sin él para desactivar las FK. El autorizador frena SQL, no código Python que llame a `setconfig` o `set_authorizer`. Los `-wal` y `-shm` también quedan en 0600 cuando existan.
- Migraciones: archivos `NNNN_nombre.sql` en `migrations/`, numerados de 1 en 1 sin huecos. `schema_version(version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)`, con SHA-256 y hora UTC ISO 8601.
- `migrate`: valida los archivos antes de tocar nada. Falla con `MigrationError` si hay huecos, duplicados, un checksum aplicado que cambió, una migración aplicada que falta o una base más nueva que el código. Sin pendientes no crea copia y es idempotente. Con pendientes y datos existentes, crea y verifica una copia y solo entonces aplica todo dentro de una transacción `BEGIN IMMEDIATE`, comprobando dentro del bloqueo la versión actual. Migra con `PRAGMA foreign_keys=OFF`, fijado fuera de la transacción y restaurado siempre al terminar, para que reconstruir una tabla con `DROP TABLE` no dispare cascadas. Un `DELETE` de migración tampoco cascada: si deja huérfanos, `foreign_key_check` aborta. Trocea con `sqlite3.complete_statement`, ejecuta sentencia a sentencia (nunca `executescript`) y rechaza sentencias de control de transacción, `PRAGMA`, `ATTACH` y `DETACH` en los archivos. Antes del `COMMIT` ejecuta `foreign_key_check` e `integrity_check`. Cualquier fallo hace `ROLLBACK` y lanza `MigrationError` citando la copia.
- Copias: API `sqlite3.Connection.backup`, en `journal_mode=DELETE`, archivo `drakter-<AAAAmmddTHHMMSSffffffZ>-<label>.db` en `backups_dir` (0700) con permisos 0600, escritas en temporal y publicadas con `os.replace` tras `integrity_check`, junto a `<archivo>.sha256` (0600) con su SHA-256. `label` solo admite `[a-z0-9-]`. `verify_backup` exige sidecar y hash correctos, `integrity_check` y `schema_version` presente.
- `restore_backup`: toma `exclusive_instance` durante toda la operación (si el backend está vivo, `BackupError` sin tocar nada: el backend es el único escritor). Exige que `backup_path` resuelto esté dentro de `backups_dir`, sea archivo regular y no symlink; lo abre en solo lectura (`mode=ro`), lo verifica, y comprueba antes de tocar la base viva que cada fila de `schema_version` coincide en versión y checksum con `migrations_dir` y que su versión no supera la del código. Después crea una copia con label `pre-restore` y vuelca con la API de backup sobre la base viva, sin sustituir archivos. Si la base viva está dañada y no admite copia, la mueve con `-wal` y `-shm` a `backups_dir/quarantine-<fecha>/` (0700), nunca la borra, y restaura sobre una base nueva. Tras restaurar, comprueba `integrity_check` y permisos.
- El backend mantiene `exclusive_instance` toda su vida: lo toma en `lifespan` antes de `migrate` y lo suelta al apagar. Si no puede, el arranque falla.
