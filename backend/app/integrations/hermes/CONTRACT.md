# Contrato del frente Hermes (agente, herramientas y chat)

Rama `drakter/agente-hermes`. `contracts/` (paquete `drakter_contracts`) manda sobre este archivo en formatos, errores, `ToolOutcome`, `UntrustedEnvelope`, eventos y tablas. Lo que aquí repita un nombre de allí debe importarse, no redefinirse.

Base verificada: Hermes **v0.22.7**, commit `b200f5bc60e31588ba2cb60e288029c4a54ba5fa`, instalado desde git (`hermes --version` lo confirma; `pyproject.toml` del tag dice `0.0.0`). Instalación: solo Python >=3.14, `uv sync --frozen`, venv propio separado del backend (3.12); nunca PyPI (0.19.0, retirado a propósito). Se compara **por commit**, no por el texto de versión. Extras: `anthropic` y `mcp`; sin gateway no hace falta `aiohttp`. `_repair_tool_call` puede reescribir nombres en Hermes: `dispatch` valida siempre por su cuenta. Mecanismo: **runner propio** (§2bis), proceso separado que instancia `AIAgent`, con herramientas por MCP desde el backend. **Prohibido `hermes gateway run`**: su cron se salta la lista blanca (verificado por drakter-5). Hermes y el modelo **no son confiables**: un control que dependa de que obedezcan no cuenta.

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

Servidor ASGI **propio**, en un listener de loopback con **puerto efímero** (`bind 127.0.0.1:0`, ni fijo ni configurable), con SDK `mcp` 2.x de bajo nivel, HTTP transmisible, sin estado. Autenticación `Authorization: Bearer <agent_tool_token>`, un token aleatorio por arranque distinto del de la GUI; ningún token `ui` ni `approver` vale aquí. `Host` debe ser exactamente `127.0.0.1:<puerto real>`. Así Hermes no alcanza **ninguna** ruta de la GUI ni de confirmaciones: la separación es de red y credencial, no de buena conducta. Sin recursos, prompts, sampling ni elicitation. `readOnlyHint` solo en READ. El nombre visto por Hermes es `mcp__drakter__<tool>`.

```python
def build_agent_tools_app(registry, turns, token: SessionToken-like, state) -> ASGIApp
class AgentToolsServer:  # uvicorn propio sobre socket de loopback
    def __init__(self, app); async def start(self); async def stop(self); port: int; url: str  # tras start()
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
    hermes_python: Path                              # python del venv de Hermes; sin shell
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
    def __init__(self, settings, data_dir, tool_names, agent_tool_token, agent_tools_url, repo_root, on_state)  # sin API HTTP
    async def start(self) -> None; async def stop(self) -> None
    state: Literal["stopped","starting","ready","restarting","failed"]
    def run_turn(self, turn_id, session_id, text, instructions) -> AsyncIterator[dict]   # eventos crudos del runner; siempre acaba en terminal
    async def stop_turn(self, turn_id, grace_s: float = 5) -> None   # `stop`; si no hay terminal en grace_s, mata y rearranca
# preflight.py: python -m app.integrations.hermes.preflight  (salida 0 solo si todo pasa)
```

`render_config` (JSON válido como YAML, sin dependencia nueva) fija: `agent.disabled_toolsets` con terminal, file, web, browser, code_execution, delegation, skills, cronjob, memory y demás; `approvals.mode: manual`; `tools.tool_search.enabled: "off"`; `auth.adopt_external_logins: false`; `auxiliary.background_review.enabled: false`; `curator.enabled: false`; `updates.check: false`; `plugins.auto_update_check_hours: 0`; `plugins.load_timeout_seconds: 0`; `terminal.cwd` absoluto y vacío; `memory.memory_enabled: false`, `memory.user_profile_enabled: false`, sin `memory.provider` (F18 pendiente); `model.context_length: 1000000`; `compression.threshold_tokens: 80000`; `auxiliary.*` en el mismo modelo; `mcp_servers.drakter` con `url` y token por `${DRAKTER_MCP_URL}` y `${DRAKTER_MCP_TOKEN}` (el puerto es efímero: nunca entra en la config ni en su hash), `tools.include` nativo, `resources: false`, `prompts: false`, `sampling.enabled: false`. Toda clave se contrasta con el código del tag.

### 2bis. Runner: `backend/app/integrations/hermes/runner/drakter_runner.py`

Proceso separado: `<hermes_python> -I <ruta>`, entorno limpio por lista blanca, `HERMES_HOME` y `HOME` dedicados, cwd vacío. Solo stdlib y Hermes; nunca importa `app`. Sin gateway, sin scheduler, sin cron.

Arranque: duplica el fd 1 para el protocolo y redirige `sys.stdout` a stderr (nada de Hermes puede corromper el JSONL). `discover_mcp_tools(["drakter"])`. Crea `AIAgent(enabled_toolsets=["mcp-drakter"], max_iterations=agent_max_turns, skip_memory=True, skip_background_review=True, skip_context_files=True, load_soul_identity=True, cwd=<vacío>, callbacks...)`. **Comprueba `agent.tools` real**: si hay un nombre fuera de `mcp__drakter__*`, sale con error y no acepta turnos.

Protocolo JSONL, una línea por mensaje, tamaño acotado, entrada no reconocida → error y sin ejecutar nada:

```text
entrada:  {"op":"turn","turn_id","session_id","input","instructions"} | {"op":"stop","turn_id"}
          | {"op":"steer","turn_id","text"} | {"op":"shutdown"}
salida:   {"ev":"ready","nonce","commit","tools":[...]}
          {"ev":"thinking","turn_id"} {"ev":"delta","turn_id","text"}
          {"ev":"tool_started","turn_id","tool","call_id"} {"ev":"tool_completed","turn_id","tool","call_id","error"}
          {"ev":"steered","turn_id","accepted":bool}
          {"ev":"completed","turn_id","output","usage","pending_steer"?} {"ev":"cancelled","turn_id"} {"ev":"failed","turn_id","code","message"}
```

`steer` (voz v2, V-22): el lector de stdin llama a `agent.redirect(text)` sobre el turno activo y responde `steered{accepted}`. El `turn_id` no cambia. Si el agente ya no admite redirección, el texto queda en `pending_steer` y sale en `completed`; el backend decide si abre otro turno con él. Un `steer` para un turno que no es el activo responde `accepted:false`. `reasoning_effort` va en la config del home (`agent.reasoning_effort`): `low` en primer plano (`hermes`), `medium` en los carriles de trabajo (`hermes-w1`).

Un lector de stdin en su hilo atiende `stop` con `agent.hard_interrupt()` mientras `run_conversation` corre en otro hilo. Si no llega terminal en `grace_s`, el supervisor mata el grupo de procesos y rearranca: el turno acaba en `TurnCancelled` o `agent_disconnected`, nunca se repite. Un solo turno a la vez. `ready` debe traer el nonce del guardián y `commit == b200f5bc…`; `tools` se compara con el catálogo. Sin `ready` válido no hay turnos. Historial: `SessionDB` del home con `session_id` del backend, o lista en memoria reanudada desde ahí; un `AIAgent` por sesión para mantener `system` y `tools` estables (H-21).

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

`AgentEvent` (`integrations/hermes/events.py`, unión discriminada): `Thinking`, `MessageDelta(text)`, `ToolStarted(tool, call_id)`, `ToolCompleted(tool, call_id, error: bool)`, y terminales `TurnCompleted(text, usage)`, `TurnCancelled`, `TurnFailed(code, message, retryable)`. Códigos estables: `agent_unavailable`, `agent_busy`, `agent_timeout`, `agent_disconnected`, `provider_auth`, `provider_error`.

Implementaciones: `HermesProvider` (`hermes_provider.py`) y `FakeProvider` (`fake.py`, sin red ni API de pago). `model` y `provider` no se reenvían a Hermes. `instructions` es estable por sesión. Sin HTTP: `HermesProvider` consume `supervisor.run_turn`. Toda aprobación interna de Hermes se deniega por código en el runner: la confirmación vive en el backend. No hay reintento automático de un turno con desenlace incierto.

## 4. Chat: `backend/app/api/chat.py`

Todo tras `SecurityGuardMiddleware`, prefijo `/api/v1`, errores con el sobre común.

| Método | Ruta | Respuesta |
|---|---|---|
| POST | `/chat/sessions` | 201 `ChatSession` |
| GET | `/chat/sessions?limit&offset` | `{items,total}` |
| POST | `/chat/sessions/{id}/close` | 200 `ChatSession` |
| GET | `/chat/sessions/{id}/messages?limit&offset` | `{items,total}` |
| POST | `/chat/sessions/{id}/messages` `{text, client_message_id, input_source?}` | 202 `{turn_id, message_id}`; 409 `agent_busy` |
| POST | `/chat/turns/{turn_id}/cancel` | 202 |
| GET | `/agent/status` | `{state, provider, model, detail}`; `state` = `runtime.status_arbiter.current.state` |

Eventos: **no hay WS de chat**. Todo sale por el flujo único `WS /api/v1/events?after_seq=N&boot_id=<id>` (`contracts/README.md` §7), con `EventEnvelope` y los modelos de `drakter_contracts.events`. `submit_message` publica `chat.user_message` (texto o voz, con `input_source`) al guardar el mensaje del usuario. El turno emite `agent.turn_started` (con `input_source`), `agent.message_started`, `agent.message_delta`, `agent.message_completed`, `agent.tool_started`, `agent.tool_completed`, `agent.turn_finished` y `agent.error`. `agent.status_changed` lo publica **solo** el `StatusArbiter` (§5bis); el runtime le pasa señales. Una herramienta con `confirmation_required` emite `confirmation.requested`. Si el búfer no cubre `after_seq` o cambia `boot_id`: `system.resync_required`.

### Bus: `backend/app/events/`

```python
class EventHub:
    boot_id: UUID
    def publish(self, type: str, payload: BaseModel, *, correlation_id: str | None = None) -> EventEnvelope  # valida contra EVENTS; único punto que asigna seq
    def subscribe(self, after_seq: int | None, boot_id: UUID | None) -> Subscription
```

Vive en `app.state.event_hub`. Los módulos publican con `event_hub.publish`, solo tras COMMIT. La ruta está en `app/api/events.py`.

Persistencia: `SqliteChatStore` sobre `conversations`, `agent_turns` y `messages` (migración 0007) y `app/database/connection.py`. Al arrancar, los turnos que sigan en `running` pasan a `interrupted`. El historial mostrado vive en Drakter; el contexto del modelo, en Hermes (`conversations.hermes_session_id`).

## 5. Arranque: `app/integrations/hermes/runtime.py`

```python
class AgentRuntime:
    def __init__(self, settings: Settings, agent_settings: AgentSettings | None = None): ...
    registry; turns; provider; hub; store
    async def start(self) -> None   # nunca hace fallar el backend: Hermes ausente deja el estado offline
    async def stop(self) -> None
```

Conexión en `app/main.py` (lo hace el integrador, tres líneas): crear `AgentRuntime(settings)`, guardarlo en `app.state.agent_runtime` y su `hub` en `app.state.event_hub`, `await start()` tras `migrate` y `await stop()` al apagar, `include_router(chat.router)` e `include_router(events.router)`, y retirar `/ws`.

## 5bis. Voz v2 y trabajos: puertos del runtime (`runtime.py`, `events/status.py`, `lanes.py`)

Congelados por WP0 (plan de voz v2 §4.6). Las etiquetas de expresión `[tag]` llegan crudas al tap y
se limpian con `drakter_contracts.speech_markup` antes del chat, la BD y la auditoría: deltas con
`IncrementalStripper`, texto terminal con `strip_tags`.

```python
class TurnTap(Protocol):     # lo implementa VoiceOrchestrator. Métodos SÍNCRONOS y NO bloqueantes (put_nowait; nunca lanzan)
    def on_turn_started(self, turn_id: UUID, session_id: UUID, source: Literal["text","voice"]) -> None
    def on_raw_delta(self, turn_id: UUID, text: str) -> None          # ANTES del stripper
    def on_tool_started(self, turn_id: UUID, tool: str) -> None
    def on_steered(self, turn_id: UUID, accepted: bool) -> None       # accepted → el tap abre un speech_id nuevo
    def on_terminal(self, turn_id: UUID, outcome: Literal["completed","cancelled","failed"]) -> None

AgentRuntime.submit_message(session_id: UUID, text: str, client_message_id: UUID | None, *,
                            source: Literal["text","voice"] = "text") -> tuple[UUID, UUID]   # (turn_id, message_id); publica chat.user_message
async AgentRuntime.current_session() -> UUID          # la última sesión abierta, o crea una (voz y chat la comparten)
AgentRuntime.set_turn_tap(tap: TurnTap | None) -> None
AgentRuntime.add_turn_prefix(fn: Callable[[UUID, str], str | None]) -> None   # (session_id, source). Solo al turn_prompt: ni BD ni chat.user_message
async AgentRuntime.steer(turn_id: UUID, text: str) -> bool
AgentRuntime.active_turn() -> ActiveTurnInfo | None   # {turn_id, session_id, phase: "generating"|"executing"}
AgentRuntime.status_arbiter: StatusArbiter            # lo crea el runtime junto al hub

class StatusArbiter:                                  # events/status.py; único productor de agent.status_changed
    def __init__(self, hub: EventHub) ; current: StatusPayload
    def signal(self, source: Literal["agent","voice"], state: CharacterState | None, *,
               turn_id: UUID | None = None, reason: str | None = None) -> None
```

- **Prefijos de turno** (V-21): canal (`[canal: voz]`), nota de «lo oído» y bloque «Trabajos en curso» se anteponen al `turn_prompt`. Las instructions (con `agent/identity/VOICE.md`) son estables: cambiar el system por turno rompe la caché.
- **Arbiter**: prioridad `offline` > `error` (2 s) > `interrupted` (0,8 s) > `speaking` > `executing` > `thinking` > `listening` > `success` (1,2 s) > `idle`; mínimo 350 ms por estado; fuentes `agent` y `voice`. Los trabajos no alimentan el personaje.
- **Carriles** (`lanes.py`, V-24): `Lane` = TurnTracker + ToolRegistry sin `jobs_*` + AgentToolsServer con token propio + Supervisor + home `hermes-w1`. N=1 sin cola (`jobs_full`). No se usa `delegate_task`. `ToolContext.job_id: UUID | None`; `confirmation.requested` lleva `job_id`. Con la sesión contaminada, `jobs_start` y `jobs_cancel` suben a `confirm`.
