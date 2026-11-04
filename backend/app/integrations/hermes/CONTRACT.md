# Contrato del frente Hermes (agente, herramientas y chat)

Rama `drakter/agente-hermes`. Interfaz fina y adaptable: cuando `contracts/` publique el `ToolSpec` y los eventos, se adapta `app/tools/spec.py` y `app/integrations/hermes/events.py`; el resto no cambia.

Base verificada: Hermes **v0.22.7** (`b200f5bc`), subproceso `hermes gateway run` con `/v1/runs`, herramientas por MCP desde el backend. Hermes y el modelo **no son confiables**: un control que dependa de que obedezcan no cuenta.

## 1. Herramientas: `backend/app/tools/`

```python
# spec.py
class RiskClass(StrEnum):  READ="read"; WRITE="write"; CONFIRM="confirm"
AuditPolicy = Literal["log", "hash", "omit"]

@dataclass(frozen=True, slots=True)
class ToolContext:
    turn_id: UUID; session_id: UUID; call_id: str; principal: Literal["agent"]; state: Any  # app.state

@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str                     # ^[a-z][a-z0-9_]{2,47}$, único
    description: str              # para el modelo, sin reglas de negocio
    domain: str                   # tasks, projects, habits, calendar, subjects, storage, relationships, memory, system, config
    args_model: type[BaseModel]   # extra="forbid"; el JSON Schema sale de aquí
    result_model: type[BaseModel]
    permission: str               # "<dominio>.<accion>", p. ej. "tasks.write"
    risk: RiskClass               # obligatorio, se declara aquí y nunca se deduce del nombre
    handler: ToolHandler          # async def | def (ctx, args) -> result_model; lo síncrono va a un hilo
    errors: tuple[str, ...] = ()  # códigos ToolError posibles
    idempotent: bool = False
    timeout_s: float = 15.0       # 1..120
    returns_untrusted: bool = False  # documentos, memoria: contamina el turno
    audit: Mapping[str, AuditPolicy] = {}  # por argumento; lo no listado se trata como "hash"
    summarize: Callable[[BaseModel], str] | None = None  # resumen para la confirmación; sin él, CONFIRM falla al registrar

class ToolError(Exception):  # code estable, message seguro, retryable=False, details=None
```

Cada módulo crea `app/tools/<dominio>.py` con `TOOLS: tuple[ToolSpec, ...]`. `load_builtin_tools(registry)` descubre esos módulos con `pkgutil`: **nadie edita un archivo común para añadir herramientas**.

```python
# registry.py
class ToolRegistry:
    def register(self, spec: ToolSpec) -> None          # falla si duplicado o incompleto
    def catalog(self) -> tuple[ToolSpec, ...]
    def get(self, name: str) -> ToolSpec | None
    async def dispatch(self, name: str, raw_args: dict, ctx: ToolContext) -> ToolOutcome  # nunca lanza

# gate.py: lo implementa drakter/seguridad; aquí viven el Protocol y los valores por defecto
class ToolGate(Protocol):
    async def authorize(self, spec, args: BaseModel, ctx, *, tainted: bool) -> GateDecision
class AuditSink(Protocol):
    async def record(self, event: ToolAuditEvent) -> None   # si lanza, no se ejecuta (fail-closed)
@dataclass GateDecision: kind: Literal["allow","deny","confirm"]; code; message; action_id; summary; expires_at
```

`ToolOutcome.model_dump()` es lo único que ve el agente:

```json
{"status":"ok","data":{}}
{"status":"error","error":{"code":"...","message":"...","retryable":false,"details":[]}}
{"status":"confirmation_required","action_id":"<uuid>","summary":"...","expires_at":"<ISO UTC>"}
```

Orden de `dispatch`, sin excepciones: herramienta registrada → turno activo y `call_id` → validar args (extra prohibido, jamás `input` en el error) → permiso → riesgo efectivo (WRITE pasa a CONFIRM si el turno está contaminado) → `ToolGate.authorize` → `AuditSink.record(attempt)` → handler con `timeout_s` → validar resultado con `result_model` → marcar contaminación si `returns_untrusted` → `AuditSink.record(result)`. Los rechazos también se auditan.

- Sin `ToolGate` real (`DefaultToolGate`): READ y WRITE pasan, CONFIRM se deniega con `confirmation_unavailable`. Lo que no esté registrado se deniega.
- Identidad de sesión y turno: nunca sale de argumentos del modelo. `TurnTracker` (`turns.py`) admite **un turno activo** a la vez; toda llamada MCP se atribuye a él y sin turno activo se rechaza con `no_active_turn` (F19). La contaminación es por sesión y no caduca.
- Permisos del agente: `agent/configuration/permissions.json`, lista `granted` con comodín `"<dominio>.*"`. Lo no concedido se deniega con `permission_denied`.
- `untrusted_envelope(source_type, source_id, content, *, truncated=False) -> dict` devuelve `{trust:"untrusted", source_type, source_id, retrieved_at, content_hash, truncated, content}` (F11). Todo contenido de documentos o memoria sale con este sobre.

### Puente MCP: `app/tools/mcp_bridge.py`

Servidor ASGI **propio**, en otro puerto de loopback (`DRAKTER_AGENT_TOOLS_PORT`, 8766), con SDK `mcp` 2.x de bajo nivel, HTTP transmisible, sin estado. Autenticación `Authorization: Bearer <agent_tool_token>`, un token aleatorio por arranque distinto del de la GUI. Así Hermes no alcanza **ninguna** ruta de la GUI ni de confirmaciones: la separación es de red y credencial, no de buena conducta. Sin recursos, prompts, sampling ni elicitation. `readOnlyHint` solo en READ. El nombre visto por Hermes es `mcp__drakter__<tool>`.

```python
def build_agent_tools_app(registry, turns, token: SessionToken-like, state) -> ASGIApp
class AgentToolsServer:  # uvicorn propio sobre socket de loopback
    def __init__(self, app, port: int); async def start(self); async def stop(self)
```

## 2. Hermes: `backend/app/integrations/hermes/`

```python
# settings.py  (BaseSettings propio, mismo .env, env_prefix "DRAKTER_", frozen, extra="ignore")
class AgentSettings:
    env: Literal["development","production"] = "development"
    agent_provider: Literal["hermes","fake"] = "hermes"
    model_provider: Literal["anthropic","dev_stub"] = "anthropic"
    model_name: str = "claude-haiku-5-5"
    dev_stub_url: str = "http://127.0.0.1:28517"     # solo con model_provider=dev_stub; solo loopback
    hermes_command: str = "hermes"                   # sin shell
    hermes_port: int = 8767
    agent_tools_port: int = 8766
    agent_max_turns: int = 12
    turn_timeout_s: float = 300; idle_timeout_s: float = 120
    anthropic_api_key: SecretStr | None   # alias ANTHROPIC_API_KEY, sin prefijo
```

`model_provider=dev_stub` con `env=production` hace fallar el arranque.

```python
# home.py
@dataclass HomePaths: root, config, soul, plugins, cwd   # data_dir/"hermes", cwd vacío absoluto
def render_config(s: AgentSettings, tool_names: Sequence[str]) -> dict     # puro y determinista
def materialize_home(s, data_dir, tool_names, repo_root) -> HomeManifest   # escribe y devuelve hashes
# supervisor.py
class HermesSupervisor:
    def __init__(self, settings, data_dir, tool_names, agent_tool_token, repo_root, on_state)
    async def start(self) -> None; async def stop(self) -> None
    state: Literal["stopped","starting","ready","restarting","failed"]; api_base: str; api_key(): str
# preflight.py: python -m app.integrations.hermes.preflight  (salida 0 solo si todo pasa)
```

`render_config` (JSON válido como YAML, sin dependencia nueva) fija siempre: `platform_toolsets: {api_server: [drakter], cron: [no_mcp]}`; `agent.disabled_toolsets` con terminal, file, web, browser, code_execution, delegation, skills, cronjob, memory y demás; `agent.max_turns`; `approvals.mode: manual`; `tools.tool_search.enabled: off`; `auth.adopt_external_logins: false`; `auxiliary.background_review.enabled: false`; `curator.enabled: false`; `kanban.dispatch_in_gateway: false`; `updates.check: false`; `plugins.auto_update_check_hours: 0`; `plugins.load_timeout_seconds: 0`; `terminal.cwd` absoluto y vacío; `gateway.api_server.max_concurrent_runs: 1`; `memory.memory_enabled: false`, `memory.user_profile_enabled: false`, sin `memory.provider` (decisión F18 pendiente); `model.context_length: 1000000`; `compression.threshold_tokens: 80000`; `auxiliary.*` en el mismo modelo; `mcp_servers.drakter` con `tools.include` nativo, `resources: false`, `prompts: false`, `sampling.enabled: false`. Toda clave se contrasta con el código del tag.

El subproceso arranca con entorno limpio (lista blanca), `HERMES_HOME` dedicado, `API_SERVER_ENABLED=true`, `API_SERVER_HOST=127.0.0.1`, `API_SERVER_KEY` aleatoria por arranque. Clave del modelo solo en el entorno del hijo. El guardián `drakter_guard` es defensa en profundidad y demuestra que está cargado con un nonce por arranque; sin esa señal no se aceptan runs.

## 3. Proveedor: `app/integrations/hermes/provider.py`

```python
@dataclass(frozen=True) class TurnRequest: session_id: UUID; turn_id: UUID; text: str

class AgentProvider(Protocol):
    name: str
    async def start(self) -> None
    async def stop(self) -> None
    def status(self) -> ProviderStatus            # state, detail seguro, model
    async def create_session(self) -> UUID
    async def close_session(self, session_id: UUID) -> None
    def stream_turn(self, request: TurnRequest) -> AsyncIterator[AgentEvent]   # siempre acaba en terminal
    async def cancel(self, turn_id: UUID) -> None
```

`AgentEvent` (`events.py`, unión discriminada): `Thinking`, `MessageDelta(text)`, `ToolStarted(tool, call_id)`, `ToolCompleted(tool, call_id, error: bool)`, y terminales `TurnCompleted(text, usage)`, `TurnCancelled`, `TurnFailed(code, message, retryable)`. Códigos estables: `agent_unavailable`, `agent_busy`, `agent_timeout`, `agent_disconnected`, `provider_auth`, `provider_error`.

Implementaciones: `HermesProvider` (`hermes_provider.py`) y `FakeProvider` (`fake.py`, sin red ni API de pago). `model` y `provider` no se reenvían a Hermes. `instructions` es estable por sesión. Un `approval.request` se deniega por código y se audita: la confirmación vive en el backend. No hay reintento automático de un turno con desenlace incierto.

## 4. Chat: `backend/app/api/chat.py`

Todo tras `SecurityGuardMiddleware`, prefijo `/api/v1`, errores con el sobre común.

| Método | Ruta | Respuesta |
|---|---|---|
| POST | `/chat/sessions` | 201 `ChatSession` |
| GET | `/chat/sessions?limit&offset` | `{items,total}` |
| POST | `/chat/sessions/{id}/close` | 200 `ChatSession` |
| GET | `/chat/sessions/{id}/messages?limit&offset` | `{items,total}` |
| POST | `/chat/sessions/{id}/messages` `{text, client_message_id}` | 202 `{turn_id, message_id}`; 409 `agent_busy` |
| POST | `/chat/turns/{turn_id}/cancel` | 202 |
| GET | `/agent/status` | `{state, provider, model, detail}` |
| WS | `/api/v1/chat/events?after_seq=N` | eventos, subprotocolo `drakter.v1` |

Sobre de evento: `{event_id, seq, timestamp, type, version:1, payload}`. Tipos: `agent.status_changed` (`state`: idle/thinking/executing/speaking/error/offline), `agent.message_delta` `{session_id,turn_id,delta}`, `agent.message_completed` `{session_id,turn_id,message_id,text}`, `agent.tool_started`/`agent.tool_completed` `{session_id,turn_id,tool,call_id,error?}`, `agent.confirmation_required` `{session_id,turn_id,action_id,summary,expires_at}`, `agent.error` `{session_id,turn_id,code,message,retryable}`. Búfer circular de 500 eventos para reconectar con `after_seq`; si el hueco no cabe, llega `agent.replay_truncated` y la GUI relee `/messages`.

Persistencia: `ChatStore` (Protocol) con `SqliteChatStore` sobre `app/database/connection.py` y `MemoryChatStore` si las tablas de `app/schemas/ddl_chat.sql` aún no están migradas. El historial mostrado vive en Drakter; el contexto del modelo, en Hermes.

## 5. Arranque: `app/integrations/hermes/runtime.py`

```python
class AgentRuntime:
    def __init__(self, settings: Settings, agent_settings: AgentSettings | None = None): ...
    registry; turns; provider; hub; store
    async def start(self) -> None   # nunca hace fallar el backend: Hermes ausente deja el estado offline
    async def stop(self) -> None
```

Conexión en `app/main.py` (lo hace el integrador, tres líneas): crear `AgentRuntime(settings)`, guardarlo en `app.state.agent_runtime`, `await start()` tras `migrate` y `await stop()` al apagar, e `include_router(chat.router)`.
