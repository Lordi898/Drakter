# Contrato del frente almacén + relaciones

Local a `drakter/almacen-relaciones`. Lo que no fija este archivo lo fija `backend/CONTRACT.md`.
Base común: `app/services/storage_ports.py`, `app/schemas/storage.py`, `app/schemas/relations.py`.
Esquema real: `backend/migrations/0001`, `0005`, `0006`, `0007`, `0008`, `0009` (solo drakter-11 las edita). Instantes con `storage_ports.utc_now()`: 24 caracteres, milisegundos y `Z`. `entities.metadata_json` de un recurso guarda `{"file_dev","file_ino","index_content"}`.

## Reglas transversales

- `sqlite3` síncrono sobre `app.database.connection.connect`, sin ORM. Rutas FastAPI con `def`: una conexión por petición, cerrada en `finally`. `sqlite3.Row` se pone con `conn.row_factory`.
- Escrituras compuestas con `storage_ports.write_tx(conn)`.
- Errores: `AppError(code, message, status)`, mensaje fijo sin entrada ni rutas. La GUI nunca lo muestra: `ApiError` usa texto propio en español y elige por `code`. Catálogo común (`contracts/python/drakter_contracts/errors.py`), con su HTTP: `not_found` 404, `conflict` 409, `revision_mismatch` 412, `confirmation_required` 409, `confirmation_unavailable` 503, `permission_denied` 403, `path_not_allowed` 403, `file_too_large` 413, `archive_limit_exceeded` 413, `unsupported_media_type` 415, `resource_unavailable` 424, `relationship_not_allowed` 422, `hierarchy_cycle` 409, `has_dependents` 409. Códigos del almacén que faltan en el catálogo y se proponen a drakter-11: `read_failed` 422, `url_not_allowed` 403, `link_fetch_failed` 502. Duplicado o entidad archivada: `conflict`, con `ErrorDetail.code` `duplicate` o `entity_archived`.
- `confirmation_required` siempre lleva `confirmation {id, summary, affected_count, expires_at, params_hash}` en el sobre; nunca 2xx, nunca sin esos datos. Mientras no haya gate real, `confirmation_unavailable`.
- Todo acto mutador o de lectura de contenido llama a `deps.audit.record` con `action` (`storage.resource.read`, `relations.create`…). Nunca se audita contenido, `note_body` ni rutas absolutas.
- Lo destructivo o masivo llama antes a `deps.gate.require(...)`, con `summary` y `affected_count` calculados por el backend. En REST lo impone `deps.gate`. En herramientas lo impone `ToolRegistry.dispatch` por `RiskClass.CONFIRM`, y el handler usa `tool_deps(ctx.state)`. El aprobador es siempre la GUI.
- El contenido y los snippets son datos no confiables: viajan con `content_trust: "untrusted"` y nunca se concatenan en instrucciones.
- Tablas ajenas (`entities`, `tags`, `entity_tags`) solo se tocan desde `repositories/storage.py` y `repositories/relations.py`.
- El borrado de un recurso quita la entrada del catálogo. El archivo del usuario no se toca nunca: v1 no escribe en ubicaciones.

## SafeFS — `app/services/storage_safefs.py`

```python
class PathNotAllowed(Exception): ...   # traducir a AppError path_not_allowed
class MissingFile(Exception): ...      # el archivo no está: disponibilidad `missing`
@dataclass(frozen=True)
class RootIdentity: dev: int; ino: int
@dataclass(frozen=True)
class ScanEntry: relative_path: str; size: int; mtime_ns: int; dev: int; ino: int; nlink: int
@dataclass(frozen=True)
class OpenedFile:  # context manager; __exit__ cierra fd
    fd: int; size: int; mtime_ns: int; dev: int; ino: int
    def close(self) -> None: ...

def validate_location_path(path: str, denied: Sequence[Path]) -> tuple[Path, RootIdentity]: ...
def validate_relative_path(relative: str) -> str: ...   # normalizado; rechaza vacío, absoluto, `..`, NUL, control
def open_file(root: Path, identity: RootIdentity | None, relative: str, *, denied: Sequence[Path],
              max_bytes: int | None = None) -> OpenedFile: ...
def stat_file(root, identity, relative, *, denied) -> ScanEntry: ...
def scan(root, identity, *, denied, max_entries, max_depth) -> Iterator[ScanEntry]: ...  # scandir sin seguir symlinks
```

`open_file`: `openat2` por ctypes (syscall 437) con `RESOLVE_BENEATH|RESOLVE_NO_SYMLINKS|RESOLVE_NO_MAGICLINKS` y `O_RDONLY|O_CLOEXEC|O_NONBLOCK`, relativo a un fd de la raíz con `(st_dev, st_ino)` comprobados; ante `ENOSYS`, falla cerrado. Tras abrir: `fstat`, `S_ISREG`, `st_nlink == 1`, tamaño máximo. Solo se usa el fd; prohibido `FileResponse`. Denegación: lista `denied`, más `.env`, `.env.*`, y cualquier componente `.ssh`, `.gnupg` dentro de una raíz. `validate_location_path` rechaza symlinks en la ruta dada, `/`, el `home` entero y raíces que contengan o estén contenidas en una ruta denegada.

## Lectores — `app/services/readers/`

```python
# readers/__init__.py
@dataclass(frozen=True)
class ReadOptions: selector: str | None = None; offset: int = 0; max_chars: int = 8000
@dataclass(frozen=True)
class Extracted: text: str; truncated: bool; next_offset: int | None; metadata: dict[str, str|int|float|bool|None]
class UnsupportedFormat(Exception): ...
class ReadFailed(Exception): ...         # archivo inválido o protegido
class TooLarge(Exception): ...
class ArchiveLimit(Exception): ...
def detect_type(name: str, head: bytes) -> tuple[ResourceTypeLiteral, str | None]: ...
def read_file(fd: int, resource_type: str, mime: str | None, options: ReadOptions, limits: StorageLimits) -> Extracted: ...
def extract_for_index(fd: int, resource_type: str, mime: str | None, limits: StorageLimits) -> str: ...
# readers/link.py
class UrlNotAllowed(Exception): ...
class LinkFetchFailed(Exception): ...
def read_link(url: str, options: ReadOptions, limits: StorageLimits) -> Extracted: ...
```

- PDF (`pypdf`) y comprimidos se analizan en proceso hijo (`readers/sandbox.py` + `readers/worker.py`) con `RLIMIT_AS`, `RLIMIT_CPU`, `RLIMIT_FSIZE=0`, `RLIMIT_NOFILE`, timeout y salida acotada. El fd se pasa con `pass_fds`. Texto y metadatos de imagen se resuelven en proceso con lectura acotada.
- Imágenes: solo metadatos (formato, ancho, alto) con parser propio de cabeceras PNG, JPEG, GIF, WebP, BMP; sin Pillow ni OCR.
- Comprimidos: `app/services/storage_archives.py`. zip, tar con gz, bz2 y xz. v1 solo lista: nunca extrae a disco, ni ejecutables ni nada. Sin recursión. Límites de `StorageLimits`; tar con lectura de cabeceras acotada; se valida cada nombre (`..`, absoluto, NUL, profundidad, longitud), se ignoran enlaces y dispositivos como entradas marcadas. Superar un límite da `ArchiveLimit`.
- Enlaces: solo http/https en puertos 80 y 443, sin credenciales en la URL; resolver DNS, rechazar IP no global (loopback, privada, link-local, multicast, reservada, incluida IPv4 mapeada en IPv6), conectar a la IP fijada con SNI y `Host` del nombre, revalidar en cada redirección, límites de bytes y tiempo. Solo `text/*`, `application/xhtml+xml` y `application/json`. HTML a texto con `html.parser` de stdlib, sin ejecutar nada.

## Catálogo — `app/repositories/storage.py` y servicios

Todas las funciones de servicio reciben `(conn, deps, actor, ...)` y devuelven modelos de `app/schemas/storage.py`.

```python
# services/storage_catalog.py
list_locations(conn, deps, actor) -> list[StorageLocationOut]
create_location(conn, deps, actor, data) -> StorageLocationOut      # solo actor.kind == "user" y origin "rest"
update_location(conn, deps, actor, location_id, data) -> StorageLocationOut   # igual
delete_location(conn, deps, actor, location_id) -> None      # gate; quita catálogo, no archivos
list_folders(conn, deps, actor, parent_id: str | None, include_archived: bool = False) -> list[FolderOut]
create_folder / update_folder / delete_folder(conn, deps, actor, ...)  # update con expected_revision
list_resources(conn, deps, actor, *, folder_id, resource_type, availability, tag, include_archived, limit, cursor) -> ResourcePage
get_resource(conn, deps, actor, resource_id) -> ResourceOut
create_resource(conn, deps, actor, data) -> ResourceOut
update_resource(conn, deps, actor, resource_id, data) -> ResourceOut
archive_resource / unarchive_resource(conn, deps, actor, resource_id) -> ResourceOut
delete_resource(conn, deps, actor, resource_id, detach: bool = False) -> None
read_resource(conn, deps, actor, resource_id, request: ReadRequest) -> ReadResult
# services/storage_index.py
search_resources(conn, deps, actor, *, q, types, limit, cursor) -> SearchPage
index_resource(conn, deps, actor, resource_id, include_content: bool | None = None) -> ResourceOut
refresh_index(conn, deps, actor) -> RefreshResult   # gate si el agente lo pide
sync_document(conn, resource_row) -> None  # metadatos a search_documents, misma transacción
# services/storage_scan.py
scan_location(conn, deps, actor, location_id) -> ScanResult
```

Permisos: `create_location`, `update_location`, `delete_location` rechazan actores que no sean `user`/`rest` con `permission_denied`. `read_resource` de un archivo con `agent_read = 0` y actor agente da `permission_denied`. Ubicación `enabled = 0`: `resource_unavailable`. `read_resource`: buscar → disponibilidad → permisos → lector → auditar. La disponibilidad se actualiza si el archivo falta. `note_body` se lee por `read_resource`, no por `get_resource`.

Búsqueda: cada término como frase FTS5 con `"` duplicada y `*` aparte, sin sintaxis expuesta; archivados fuera; recursos archivados por join con `entities`. Cursor opaco base64 de `offset`.

Detección de movidos: en `scan`, un `(dev, ino)` conocido en otra ruta de la misma ubicación actualiza `relative_path` y deja `available`. Si el recurso falta, `missing`.

Índice: `chunk_no = 0` lleva título, tipo, ruta relativa, descripción, etiquetas y metadatos permitidos. El texto extraído va en chunks `1..n` solo con `index_content = 1`, y solo para `text`, `code`, `pdf`, `document`, nunca desde `archive`.

## REST (`/api/v1`, `app/api/storage.py`, `app/api/relations.py`)

`get_deps(request) -> StorageDeps` en `app/api/storage.py`: usa `app.state.storage_deps` si existe; si no, crea uno con `app.state.settings`. Actor REST: `Actor("user", "rest", request.scope["state"]["request_id"])`. Exponen `router`.

| Método y ruta | Servicio |
|---|---|
| `GET/POST /storage-locations`, `PATCH/DELETE /storage-locations/{id}` | catálogo |
| `GET/POST /folders`, `PATCH/DELETE /folders/{id}` | catálogo |
| `GET/POST /resources`, `GET/PATCH/DELETE /resources/{id}` | catálogo |
| `POST /resources/{id}/archive`, `/unarchive`, `/read`, `/index` | catálogo, índice |
| `GET /resources/search?q=&type=&limit=&cursor=` | índice |
| `POST /resources/refresh-index`, `POST /resources/scan` | índice, escaneo |
| `GET /relationships/types` | relaciones |
| `GET/POST /relationships`, `PATCH/DELETE /relationships/{id}` | relaciones |
| `GET /entities/{id}/related?direction=&type=` | relaciones |

El cliente nunca manda identificador de confirmación: la ruta responde 409 y `approve` ejecuta los argumentos guardados con `services/storage_confirmed.execute_confirmed`. Rutas fijas (`search`, `scan`, `refresh-index`, `types`) antes de `/{id}`.

## Relaciones — `app/services/relations.py`

```python
list_types(conn, deps, actor) -> list[RelationshipTypeOut]
create_relationship(conn, deps, actor, data: RelationshipCreate) -> RelationshipOut
update_relationship(conn, deps, actor, relationship_id, data: RelationshipUpdate) -> RelationshipOut
delete_relationship(conn, deps, actor, relationship_id) -> None
search_relationships(conn, deps, actor, query: RelationshipSearch) -> RelationshipPage
get_related_items(conn, deps, actor, entity_id, *, direction="both", relationship_type=None) -> RelatedItems
count_for_entity(conn, entity_id) -> int
detach_entity(conn, deps, actor, entity_id) -> int   # dentro de la transacción de quien llama
```

- Tipos de origen y destino salen de `entities`; regla por `relationship_rules`; sin regla, `invalid_relationship`. Entidad archivada: `entity_archived`.
- `related_to` es simétrica: se guarda con `source_id < target_id`, y se comprueba duplicado en esa forma.
- Reglas `acyclic = 1`: las corta el trigger `trg_relationships_no_cycle`; traducir su `IntegrityError` (mensaje `relationship_cycle`) a `AppError`. Etiquetas `label`/`inverse_label` en español: dict en `services/relations.py`, la tabla no las tiene.
- Aristas virtuales: tabla `VIRTUAL_EDGES` declarativa (tasks.project_id → `belongs_to`, tasks.subject_id → `belongs_to`, tasks.parent_task_id → `parent_of` invertido, resources.folder_id → `belongs_to`, folders.parent_folder_id → `parent_of` invertido, class_sessions.subject_id → `belongs_to`).
- Títulos: vista `v_entity_labels`; `v_orphan_entities` queda para la comprobación de arranque.
- `delete_relationship` pasa siempre por el gate, también desde la GUI (`contracts/api/routes.md`).

## Herramientas — `app/tools/storage.py`, `app/tools/relations.py`

Contrato: `git show drakter/agente-hermes:backend/app/integrations/hermes/CONTRACT.md` §1. `from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec`, y `untrusted_envelope` de donde indique esa rama; si `spec.py` aún no está en esta rama, se comprueba con un módulo sustituto en `tests/storage_tool_stub.py`, sin crear `app/tools/spec.py`. Cada archivo expone `TOOLS: tuple[ToolSpec, ...]` y se autodescubre.

Handler síncrono: abre `connect(ctx.state.settings.db_path)` con `row_factory`, cierra en `finally`, usa `tool_deps(ctx.state)` y `Actor("agent", "mcp", str(ctx.turn_id))`, y traduce `AppError` a `ToolError(code, message)`. `audit` por argumento: `q`, `query`, ids → `"log"`; `note_body`, `description`, `url` → `"hash"`. `returns_untrusted=True` en `read_resource` (sale con `untrusted_envelope`), `search_resources` y `get_resource` por los títulos y descripciones.

| Herramienta | `domain` | `permission` | `risk` |
|---|---|---|---|
| `search_resources`, `get_resource`, `read_resource`, `list_folders` | storage | `storage.read` | READ |
| `create_resource`, `update_resource_metadata`, `index_resource` | storage | `storage.write` | WRITE |
| `refresh_resource_index` | storage | `storage.write` | CONFIRM, con `summarize` |
| `get_related_items`, `search_relationships` | relationships | `relationships.read` | READ |
| `create_relationship` | relationships | `relationships.write` | WRITE |
| `delete_relationship` | relationships | `relationships.delete` | CONFIRM, con `summarize` |

No hay herramienta de ubicaciones, de borrado de recursos ni de escaneo. Ninguna acepta rutas ni URL: `create_resource` solo crea notas y los enlaces los registra la GUI. Al agente no le llegan `url_not_allowed` ni `link_fetch_failed`: `read_resource` los convierte en `resource_unavailable`.

## Interfaz

Cliente único: `apiRequest`, `ApiError`, `describeError` de `desktop/src/services/api.ts`. Rutas con prefijo `/api/v1`. Sin cliente propio ni datos de ejemplo. El renderer nunca ve el token. Las ubicaciones usan `window.api.addStorageLocation`, `updateStorageLocation` y `deleteStorageLocation`: los diálogos nativos están en main y el renderer no envía rutas.
