# Contrato de la base del backend

Interfaces congeladas de la base segura. Otro módulo solo puede depender de lo que aparece aquí.
Fuera de alcance: tablas de dominio, rutas de dominio, eventos WebSocket de negocio y Hermes.

## Arranque

- Único punto de entrada: `python -m app` desde `backend/`. `app/__main__.py` pone `os.umask(0o077)`, carga la configuración, abre, enlaza y pone a escuchar él mismo el socket en `127.0.0.1:<port>` y se lo pasa a Uvicorn con `server.run(sockets=[sock])`. Si el puerto está ocupado, sale con código distinto de 0 sin tocar el archivo de sesión.
- La dirección no es configurable: `BIND_HOST = "127.0.0.1"`, constante.
- Uvicorn: `log_config=None`, `access_log=False`, `server_header=False`, `proxy_headers=False`, `ws="websockets-sansio"`, `ws_max_size=1048576`, `lifespan="on"`.
- `create_app(settings: Settings) -> FastAPI` en `app/main.py`. No existe un `app` a nivel de módulo. `docs_url`, `redoc_url` y `openapi_url` son `None`.
- Orden del `lifespan`: preparar directorios → `configure_logging` → `migrate` → escribir archivo de sesión. Al apagar, borrar el archivo de sesión. Si `migrate` falla, el arranque falla.

## `app/core/config.py`

```python
BIND_HOST: Final = "127.0.0.1"

class Settings(BaseSettings):
    # env_prefix="DRAKTER_", extra="ignore", frozen=True
    # env_file = Path(user_config_dir("drakter")) / ".env"; respeta XDG_CONFIG_HOME
    port: int = 8765                        # 1024..65535
    data_dir: Path                          # por defecto user_data_dir("drakter")
    runtime_dir: Path                       # por defecto user_runtime_dir("drakter")
    log_level: Literal["DEBUG","INFO","WARNING","ERROR"] = "INFO"
    allowed_origins: Annotated[tuple[str, ...], NoDecode] = ("app://drakter",)
    # Propiedades: db_path = data_dir/"drakter.db", backups_dir = data_dir/"backups",
    #              logs_dir = data_dir/"logs", session_file = runtime_dir/"session.json"

def ensure_private_dir(path: Path) -> None: ...
def load_settings() -> Settings: ...
```

- `DRAKTER_ALLOWED_ORIGINS` es una lista separada por comas. Rechaza `*`, `null`, y cualquier valor que no sea exactamente `scheme://host[:port]` (sin ruta, consulta, fragmento ni credenciales). Se normaliza a minúsculas.
- `ensure_private_dir`: crea con 0700 y padres; si existe, es symlink, no es del usuario actual o da permisos a grupo u otros, lanza `ValueError` (no corrige en silencio salvo que el directorio sea del usuario y no sea symlink: entonces `chmod 0700`).

## `app/core/logging.py`

```python
def configure_logging(level: str, logs_dir: Path) -> None: ...
def register_secret(value: str) -> None: ...
def redact(value: object) -> object: ...
class JsonFormatter(logging.Formatter): ...
```

- Una línea JSON por evento con `ts` (UTC ISO 8601), `level`, `logger`, `message` y los campos de `extra`. Salida a stderr y a `logs_dir/"backend.log"` (rotación 5 MiB, 3 copias, permisos 600, también las rotadas).
- Redacción en el formateador, sobre el texto final, incluidos `extra` y trazas de excepción. Sustituye por `[REDACTED]`: valores registrados con `register_secret`; valores de claves que contengan `authorization`, `token`, `secret`, `password`, `api_key`, `apikey`, `cookie`, `credential` (sin distinguir mayúsculas, también anidadas); `Bearer <x>`; `drakter.auth.<x>`; `sk-…`; y `<clave>=<valor>` o `"clave": "valor"` en texto libre con esas claves.
- `configure_logging` encamina también `uvicorn`, `uvicorn.error`, `uvicorn.access`, y es idempotente: no duplica manejadores.

## `app/core/errors.py`

```python
class ErrorDetail(BaseModel):  # field: str | None, code: str, message: str
class ErrorBody(BaseModel):    # code: str, message: str, request_id: str, details: list[ErrorDetail]
class ErrorEnvelope(BaseModel):# error: ErrorBody

class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400,
                 details: list[ErrorDetail] | None = None): ...

def error_body_bytes(code: str, message: str, request_id: str,
                     details: list[ErrorDetail] | None = None) -> bytes: ...
def install_error_handlers(app: FastAPI) -> None: ...
```

- Todo error HTTP responde `{"error":{"code","message","request_id","details"}}` con `application/json`.
- Cubre `AppError`, `RequestValidationError` (422, código `validation_error`; `details` con `field`, `code` y `message`, jamás `input` ni `ctx`), `StarletteHTTPException` (`http_404`, `http_405`, …, con mensaje fijo, conservando sus cabeceras) y `Exception` (500, código `internal_error`, mensaje fijo, traza solo en el log).
- `request_id` sale de `request.scope["state"]["request_id"]`; si no está, `uuid4`. Nunca se toma de la petición del cliente.

## `app/core/security.py`

```python
PUBLIC_PATHS: Final = frozenset({"/health"})
WS_SUBPROTOCOL: Final = "drakter.v1"
WS_AUTH_PREFIX: Final = "drakter.auth."

class SessionToken:
    def __init__(self) -> None: ...             # secrets.token_urlsafe(32); registra con register_secret
    def matches(self, candidate: bytes) -> bool: ...   # hmac.compare_digest sobre bytes
    def reveal(self) -> str: ...                # solo para el archivo de sesión
    # __repr__ y __str__ nunca muestran el valor

def write_session_file(path: Path, token: SessionToken, port: int) -> None: ...
def remove_session_file(path: Path) -> None: ...

class SecurityGuardMiddleware:                  # ASGI puro; http y websocket
    def __init__(self, app, *, token: SessionToken, port: int,
                 allowed_origins: tuple[str, ...]): ...
```

Archivo de sesión: JSON `{"token","port","pid","started_at"}`, escrito en un temporal 0600 con `O_CREAT|O_EXCL|O_NOFOLLOW` en el mismo directorio y publicado con `os.replace`. El token nunca va a logs, argumentos ni variables de entorno. `remove_session_file` no falla si no existe y solo borra el archivo si su `pid` es el actual.

`SecurityGuardMiddleware` es la capa más externa de las añadidas y, por este orden:

1. Asigna `scope["state"]["request_id"] = str(uuid4())` y `lifespan` pasa sin más.
2. Exige que `scope["client"]` sea `127.0.0.1` (403 `forbidden_client`).
3. Exige exactamente una cabecera `Host`, igual a `127.0.0.1:<port>` o `localhost:<port>` (sin distinguir mayúsculas). Si no: 403 `forbidden_host`. Una petición sin `Host` o con dos la corta antes h11 con un 400 sin envelope; el guardia es la segunda barrera.
4. Si hay `Origin`, exige exactamente uno y que esté en `allowed_origins`. Si no: 403 `forbidden_origin`. Sin `Origin` se continúa: los clientes que no son navegador no lo envían.
5. Solo en HTTP, deja pasar sin token las rutas de `PUBLIC_PATHS` y las preflight CORS (`OPTIONS` con `Origin` ya validado y `Access-Control-Request-Method`). En websocket, `/health` también exige token.
6. Todo lo demás, incluidas rutas inexistentes, exige token: `Authorization: Bearer <token>`. En websocket vale además el subprotocolo `drakter.auth.<token>`. Nunca por query string ni cookie. Si no: 401 `unauthorized` con `WWW-Authenticate: Bearer`.

En websocket, cualquier rechazo se hace antes de aceptar: se consume `websocket.connect` y se envía `websocket.close` con código 1008, de modo que el cliente recibe un rechazo del handshake. El guardia nunca registra cabeceras, consulta ni token. Registra `event`, `method`, `path` sin consulta, `status` y `request_id`.

Con un `Origin` validado, el guardia lo guarda en `scope["state"]["cors_origin"]` y sus 401 y el 500 de `install_error_handlers` añaden `Access-Control-Allow-Origin`, porque nacen fuera de `CORSMiddleware`. Una preflight con método no permitido devuelve el 400 en texto plano de `CORSMiddleware`.

CORS: `CORSMiddleware` dentro del guardia, con `allow_origins=settings.allowed_origins`, `allow_credentials=False`, `allow_methods` GET/POST/PUT/PATCH/DELETE, `allow_headers` Authorization/Content-Type. Sin expresiones regulares.

## `app/api/`

- `health.py`: `GET /health` (público) → `{"status":"ok"}`; hace `SELECT 1` con `connect`. Si falla → `AppError("service_unavailable", ..., 503)`, sin detalles.
- `auth.py`: `GET /api/v1/auth/check` → `{"authenticated": true}`.
- `ws.py`: `WS /ws`. Si el cliente ofreció `drakter.v1`, acepta con ese subprotocolo; nunca devuelve el de autenticación. Si recibe el texto `ping`, responde `pong`. Cualquier otra entrada cierra con 1003.

## `app/database/`

```python
# connection.py
def connect(db_path: Path) -> sqlite3.Connection: ...

# migrator.py
SCHEMA_VERSION_TABLE: Final = "schema_version"
MIGRATIONS_DIR: Final = Path(__file__).resolve().parents[2] / "migrations"
class MigrationError(Exception): ...
@dataclass(frozen=True)
class MigrationResult:
    from_version: int; to_version: int; applied: tuple[str, ...]; backup: Path | None
def current_version(conn: sqlite3.Connection) -> int: ...
def migrate(db_path: Path, backups_dir: Path, migrations_dir: Path = MIGRATIONS_DIR) -> MigrationResult: ...

# backup.py
class BackupError(Exception): ...
def create_backup(db_path: Path, backups_dir: Path, label: str) -> Path: ...
def verify_backup(backup_path: Path) -> None: ...
def restore_backup(db_path: Path, backups_dir: Path, backup_path: Path) -> Path: ...  # devuelve la copia de seguridad previa

# cli.py: python -m app.database.cli status|migrate|backup|restore <archivo>
```

- `connect`: crea la base con `os.open(..., O_CREAT|O_RDWR|O_NOFOLLOW, 0o600)`, fuerza 0600 si ya existía, rechaza symlink o propietario ajeno, y aplica `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, `busy_timeout=5000`, con `isolation_level=None` (transacciones explícitas). Verifica que WAL y `foreign_keys` han quedado activos. Los `-wal` y `-shm` también quedan en 0600 cuando existan.
- Migraciones: archivos `NNNN_nombre.sql` en `migrations/`, numerados de 1 en 1 sin huecos. `schema_version(version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)`, con SHA-256 y hora UTC ISO 8601.
- `migrate`: valida los archivos antes de tocar nada. Falla con `MigrationError` si hay huecos, duplicados, un checksum aplicado que cambió, una migración aplicada que falta o una base más nueva que el código. Sin pendientes no crea copia y es idempotente. Con pendientes y datos existentes, crea y verifica una copia y solo entonces aplica todo dentro de una transacción `BEGIN IMMEDIATE`, comprobando dentro del bloqueo la versión actual. Trocea con `sqlite3.complete_statement`, ejecuta sentencia a sentencia (nunca `executescript`) y rechaza sentencias de control de transacción, `PRAGMA`, `ATTACH` y `DETACH` en los archivos. Antes del `COMMIT` ejecuta `foreign_key_check` e `integrity_check`. Cualquier fallo hace `ROLLBACK` y lanza `MigrationError` citando la copia.
- Copias: API `sqlite3.Connection.backup`, archivo `drakter-<AAAAmmddTHHMMSSffffffZ>-<label>.db` en `backups_dir` (0700) con permisos 0600, escritas en temporal y publicadas con `os.replace` tras `integrity_check`. `label` solo admite `[a-z0-9-]`.
- `restore_backup`: exige que `backup_path` resuelto esté dentro de `backups_dir`, sea archivo regular y no symlink; lo abre en solo lectura (`mode=ro`), lo verifica, crea una copia con label `pre-restore` y vuelca con la API de backup sobre la base viva, sin sustituir archivos. Tras restaurar, comprueba `integrity_check` y permisos.
