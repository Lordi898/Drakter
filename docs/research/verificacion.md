# Verificación real: Hermes, OpenViking, Haiku 5.5 y hardware de voz

Fecha: 2026-11-04. Rama `drakter/verificacion`. Estado: **parcial**, pendiente la verificación independiente de §1.8.

Convención: **VERIFICADO** (ejecutado, con comando y salida resumida), **NO FUNCIONA** (error exacto), **⚠️** (no comprobado y por qué). Ningún modelo real se ha ejecutado: todas las pruebas de agente usan stubs locales, que demuestran mecánica, no el comportamiento de Claude ni la calidad de resultados.

## Resumen para contratos

| Tema | Conclusión | Recomendación |
|---|---|---|
| Versión de Hermes | Git v0.22.7 `b200f5bc60e31588ba2cb60e288029c4a54ba5fa`. PyPI 0.19.0 está abandonado | Fijar ese commit, venv propio, solo Python 3.14 |
| Integración | `AIAgent` funciona con tokens y eventos por callbacks | Runner propio con `AIAgent` en proceso aparte, sin gateway |
| Lista blanca | Funciona dentro del turno con `enabled_toolsets` y `tool_search` "off" | Usar la receta de §1.3, y validar siempre en el backend |
| Cron | En gateway saltó la lista blanca y ejecutó `terminal` | Sin gateway ni scheduler |
| OpenViking | Viable con condiciones; servidor HTTP obligatorio, ~600 MB, AGPL-3.0 | Proceso y venv propios; ver condiciones de §2.5 |
| Plugin OpenViking | Externo, `community`; la memoria entra como "authoritative" y hay herramientas peligrosas | No exponer `viking_forget` ni `viking_add_resource` |
| Haiku 5.5 | `claude-haiku-5-5` confirmado; petición de Hermes compatible con las reglas documentadas | ⚠️ falta prueba real con clave |
| Voz | Sin GPU útil: 14 GiB, i7-8665U, UHD 620, solo CPU | Voz por turnos; `base` int8 pendiente de medir |

Premisa del plan que es falsa: **32 GB de RAM y 4 GB de VRAM**. Están en `docs/MASTER_PLAN.md` §20.3 y `.claude/CLAUDE.md` §2.

## 0. Entorno

- **VERIFICADO** `lspci -nn`: `Intel Corporation WhiskeyLake-U GT2 [UHD Graphics 620] [8086:3ea0]`, única GPU. `grep 'model name' /proc/cpuinfo`: i7-8665U, 8 hilos, AVX2+FMA, sin AVX-512. `free -h`: 14 GiB y 4 GiB de swap llena.
- **VERIFICADO** el sistema tiene Python 3.14.4 sin pip, ensurepip, curl ni uv.
- **NO FUNCIONA** escribir en `/tmp` con la cuota agotada: `OSError: [Errno 122] Disk quota exceeded`, aunque `df` mostraba 1,6 GB libres. `findmnt` muestra `tmpfs ... usrquota`. El orquestador liberó cachés de otra sesión y autorizó `/var/tmp/drakter-5-verif`.
- **VERIFICADO** `uv 0.13.7` reutilizado de otra sesión: `sha256sum uv.whl` = `2c9bdc4a…5e25`, igual que PyPI.

Incidencias de esta verificación:
- Un agente ejecutó Python con `-I`, que ignora `PYTHONDONTWRITEBYTECODE`, y dejó hasta 2.698 `.pyc` (35,4 MB) en `/tmp/drakter-3-work`, que debía ser solo lectura. Solo `.pyc`; `git status` de `hermes-src` limpio. Orquestador informado: no se limpia.
- `hermes doctor` llamó a `GET https://api.anthropic.com/v1/models` con la clave falsa `sk-ant-api03-fake-for-stub`, en contra de lo pedido. URL fija (`hermes_cli/doctor_connectivity.py:165`), ignora `base_url`. Sin clave real ni llamada a Messages. **No ejecutar `hermes doctor` con claves reales salvo que se acepte enviarlas a todos los proveedores configurados.**
- OpenViking descargó sin avisar un modelo de 47,9 MB de HuggingFace durante una prueba sin embedding (§2.3).
- El plugin de OpenViking se descargó de GitHub con autorización del líder, fijado por sha y leído antes de ejecutar.

## 1. Hermes Agent

### 1.1 Versión e instalación

- **VERIFICADO** PyPI: `hermes-agent` 0.19.0, `requires_python <3.14,>=3.11`, legítimo de Nous Research. Lo retiraron a propósito: `git log -1 d84e11af4d` → `2026-07-22 rip out brew + pip/PyPI wheel support (#68217)`.
- **NO FUNCIONA** `pip install hermes-agent==0.19.0` en 3.14: `ERROR: No matching distribution found for hermes-agent==0.19.0`. `uv pip install --dry-run` sí resuelve porque ignora ese tope, así que no sirve como prueba.
- **VERIFICADO** `git tag --points-at b200f5bc` → `v0.22.7`. `hermes --version` → `Hermes Agent v0.22.7 (2026.9.24) · stable · local b200f5bc60e3`, aunque `pyproject.toml` diga `0.0.0`. En un venv recién creado la primera ejecución mostró `v0.21.5+20302.gb200f5b` y la siguiente v0.22.7, mismo commit: comparar siempre por commit.
- **VERIFICADO** solo Python 3.14: `uv.lock` tiene `supported-markers = ["python_full_version >= '3.14'"]` y todas las dependencias llevan `python_version >= '3.14'`. `requires-python >=3.11,<3.15` engaña: en 3.13 se resuelven 0 paquetes.
- **VERIFICADO** en Python 3.14.10: `uv sync --frozen --extra anthropic --extra mcp`, 80 paquetes, venv de 179 MB, ~11 s; más checkout de 286 MB. El lock interno de Hermes pide 3.14.9.
- **VERIFICADO** por el líder en Python del sistema 3.14.4: misma instalación en 10,5 s, 167 MB. Solo se probó `--version` e `import run_agent` (113 MB).
- ⚠️ `HERMES_HOME` creció a 694 MB porque Hermes descargó por su cuenta `uv`, Python 3.14.9 y dos entornos. No se identificó el disparador. Debe vigilarse en el runner y en el empaquetado.
- **NO FUNCIONA** compartir venv con el backend: `browser-harness>=0.1.13 depends on pillow==12.3.0 ... hermes-agent==0.0.0 depends on pillow==13.0.0`. Hermes también fija `pydantic==2.14.1`, `rich==14.3.4`, `httpx2==2.15.1`, `mcp==2.3.0`. El intérprete sí es compartible.

**Recomendación:** `git checkout b200f5bc`, `uv sync --frozen --extra anthropic --extra mcp`, venv propio, Python 3.14.x fijado y comunicación con el backend por proceso.

### 1.2 Mecanismos de integración

| Mecanismo | Estado | Tokens y eventos | Arranque | RSS | Comentario |
|---|---|---|---|---|---|
| **`AIAgent`** | VERIFICADO | Sí, por callbacks | import ~1,5 s; MCP 2,4-3,2 s; 1.er agente 1,2 s | 146 MB cargado; 237 MB tras 3 turnos; hijo MCP 78 MB | Sin scheduler, sin `state.db` si no se pasa `session_db` |
| API server | VERIFICADO con ⚠️ | Sí, SSE | 7,2 s | 241-348 MB | Necesita aiohttp, que no entra con `--extra anthropic --extra mcp` (`API Server: aiohttp not installed`); arrastra cron, kanban y curator; `API_SERVER_KEY` <16 caracteres se ignora en silencio |
| `hermes chat -q` | VERIFICADO, desaconsejado | Sí, `--format stream-json` | 4,7-42 s | 115-127 MB + gateway oculto de 270-303 MB | Lanza siempre `gateway run --quiet --idle-exit`, que sobrevive 600 s |
| ACP | NO FUNCIONA aquí | Sin probar | | | `ModuleNotFoundError: No module named 'acp'`; sin valor frente a la librería |

Medición independiente de RAM: `AIAgent()` creado 194 MB, 229 MB tras 2 turnos (VmRSS, 3 ejecuciones).

**Recomendación (decisión del orquestador):** runner propio con `AIAgent`, proceso separado, en el venv de Hermes, sin gateway. Ver §1.7.

### 1.3 Lista blanca

**VERIFICADO** con el array `tools` registrado por el stub en 61 peticiones:

| Configuración | Herramientas que ve el modelo |
|---|---|
| Sin `enabled_toolsets` | 21-36, incluidas terminal, read_file, write_file, web_search, execute_code |
| `["mcp-drakter"]` con tool_search por defecto | `tool_search, tool_describe, tool_call` (puente; las MCP quedan ocultas) |
| `["mcp-drakter"]` + `tools.tool_search.enabled: "off"` | **Solo las MCP** |
| Lo anterior + `mcp_servers.drakter.tools.include` | Solo las incluidas |

Receta (`enabled_toolsets=None` significa TODAS: el runner debe abortar si la lista queda vacía o difiere):

```yaml
mcp_servers:
  drakter:
    command: <python>
    args: [<servidor MCP>]
    sampling: {enabled: false}
    tools: {include: [drakter_echo], resources: false, prompts: false}
tools:
  tool_search: {enabled: "off"}
```

```python
class DrakterAgent(AIAgent):
    def _repair_tool_call(self, name):   # método privado: fijar commit
        return None

agent = DrakterAgent(..., enabled_toolsets=["mcp-drakter"], disabled_toolsets=["kanban"],
    skip_memory=True, skip_context_files=True, skip_background_review=True,
    load_soul_identity=True, quiet_mode=True)
assert agent.valid_tool_names == PERMITIDAS   # no ejecutado en las pruebas
```

`disabled_toolsets` no sirve como lista blanca: resta de "todas", y una herramienta nueva entraría sola.

### 1.4 Violaciones

**VERIFICADO** dentro de un turno, con `matrix.py`: 24 nombres prohibidos o inventados (terminal, write_file, read_file, patch, web_search, execute_code, delegate_task, memory, skill_manage, cronjob_manage, `Terminal`, `tool_call`, etc.) devolvieron al modelo `Tool 'terminal' does not exist. Available tools: ...`, y el turno continuó. Archivos centinela sin crear. Lote mixto: la legal se ejecuta y la prohibida no. 3 lotes inválidos seguidos cortan con `partial=True`.

⚠️ **Reparación difusa:** `Auto-repaired tool name: 'mcp__drakter__drakter_danger' -> 'mcp__drakter__drakter_add'`. Una herramienta excluida se reescribe a otra permitida con esos argumentos; el prefijo común facilita superar el umbral de similitud. Nunca alcanza herramientas fuera de la lista. Se cierra con la subclase de §1.3. **El backend debe validar por sí mismo, sea cual sea el nombre recibido.**

### 1.5 MCP

**VERIFICADO** con servidor stdio propio (`mcp` 2.3.0, FastMCP): herramienta llamada y resultado devuelto.
- Nombre real: `mcp__<servidor>__<herramienta>`, con doble guion bajo; toolset `mcp-<servidor>`.
- La librería exige `discover_mcp_tools()`, una vez por proceso; sin ello `tools=[]`, fallo cerrado.
- El resultado llega al modelo como `<untrusted_tool_result source="mcp__drakter__drakter_echo">…</untrusted_tool_result>`.

### 1.6 Otras vías

| Vía | Resultado |
|---|---|
| **Cron en gateway** | **Crítico.** Job creado por operador con `platform_toolsets.api_server` limitado recibió 23 herramientas y ejecutó `terminal` 3 veces (`tool terminal completed (0.83s, 45 chars)`). Cierre probado: `platform_toolsets.cron: [drakter]`. `[no_mcp]` pendiente de §1.8 |
| Librería sin gateway | Job vencido, 100 s: 0 ejecuciones, 0 gateways (a confirmar en §1.8) |
| `HERMES_KANBAN_TASK` | Añade 13 herramientas. Cierre: `disabled_toolsets=["kanban"]` |
| Contexto del cwd | `.hermes.md`, `HERMES.md`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules` entran en system. Cierre: `skip_context_files=True` y cwd vacío |
| Memoria | Sin `skip_memory`, MEMORY.md y USER.md entran en system |
| Revisión en segundo plano | Con `memory` en la lista, un fork escribe memoria solo. Cierre: `skip_background_review=True` |
| Skills con shell | `skills.inline_shell: true` ejecuta shell en CLI aunque `-t` lo limite. Librería: texto |
| Hooks, `/commands`, `@file` | Librería: sin efecto |
| Hook `pre_tool_call` de plugin | Bloquea de verdad: sirve de 2.ª puerta |
| Identidad | `ephemeral_system_prompt` se AÑADE tras "You are Hermes Agent…"; solo `load_soul_identity=True` sustituye la cabecera, y sigue un párrafo sobre Hermes |
| Red propia de Hermes | Intenta leer `hermes-agent.nousresearch.com/docs/api/model-catalog.json` y GitHub. En librería, 0 conexiones no loopback del proceso principal en 3 sesiones; no cubre hijos |

### 1.7 API de `AIAgent` para el runner

Del código de `b200f5bc` y de `fastapi_lib.py`, que sí se ejecutó:

- `run_conversation(mensaje)` es síncrono y devuelve un dict con `final_response`. Un `AIAgent` y un hilo por turno; 3 turnos paralelos sin fuga de herramientas.
- VERIFICADOS: `stream_delta_callback(delta)`, `tool_start_callback(...)`, `tool_complete_callback(...)`, `valid_tool_names`.
- Solo declarados en la firma (⚠️ no ejecutados): `thinking_callback`, `step_callback`, `event_callback(str, dict)`, `tool_progress_callback`, `notice_callback`, `tool_result_metadata_callback`.
- Parada, ⚠️ pendiente de prueba: `interrupt()` y `clear_interrupt()` en `agent/interrupt_control.py`; `is_interrupted`, `close()` y `release_clients()` en `run_agent.py`.
- MCP: `discover_mcp_tools(allowed_mcp_names=...)` global al proceso; `shutdown_mcp_servers()` en `tools/mcp_tool_lifecycle.py` (⚠️ cierre no ejecutado). `HERMES_HOME` se resuelve por proceso.

### 1.8 Verificación independiente

**Pendiente.** Un agente que no vio las notas intenta refutar lista blanca, reparación difusa, cron `[no_mcp]`, kanban e inyecciones condicionales, y cerco de memoria, en instalación limpia.

## 2. OpenViking 0.5.3

### 2.1 Instalación

**VERIFICADO** `uv pip install --only-binary :all: 'openviking==0.5.3'`: Python 3.14.10 y 3.14.4, 10,75 s, 314 paquetes, 775 MB más 125 MB de `.pyc`. El líder confirmó `du -sh` = 775 MB. Wheel precompilado (Rust, C++); `ldd` sin librerías ausentes. No exige Docker, Go, Rust ni Redis. `volcengine*` son 141 paquetes y 211 MB sin uso local.

### 2.2 Servicio y recursos

- **NO FUNCIONA** el modo embebido: `ImportError: cannot import name 'OpenViking' from 'openviking'`. El servidor HTTP es obligatorio: un proceso, un puerto.
- **VERIFICADO** RAM en reposo: VmRSS 560-607 MB. Pico con ingesta: 595 MB (549 MB al arrancar). Arranque 10-21 s, 92 s sin `.pyc`. Workspace vacío 2-2,7 MB; con 6 recursos 6,9 MB.
- ⚠️ Sin `root_api_key`: `auth_mode: dev` y `cors_origins` `["*"]` según el código. Fijar clave y CORS.

### 2.3 Modelos

- **VERIFICADO** arranca sin clave, pero sin embedding y VLM no indexa ni extrae memoria.
- **VERIFICADO, peligro:** sin `embedding.dense.provider` declarado **descarga sin avisar** `bge-small-zh-v1.5-f16.gguf` (47,9 MB) de HuggingFace, modelo solo de chino, y luego falla (`Local embedding is enabled but 'llama-cpp-python' is not installed`). Declarar siempre el embedding.
- **NO FUNCIONA** `provider=local`: `llama-cpp-python` sin wheels y sin compilador.
- ⚠️ VLM local: el asistente de OpenViking pide `qwen3.5:4b`, ~3,4 GB y 8 GB de RAM mínimos. No medido; no cabe aquí. Hace falta VLM remoto, con salida de datos.
- ⚠️ No hay proveedor Anthropic directo. Haiku vía `litellm` sin probar.
- Proveedor `openai` con `api_base` local: VERIFICADO con stub.

### 2.4 Funcionamiento

Con stubs; sin afirmar calidad.

| Punto | Resultado |
|---|---|
| Ingesta | VERIFICADO: 3 VLM y 5 embeddings por documento pequeño; 50 KB con 40 secciones: 43 VLM, 19 s |
| Capas | VERIFICADO con diferencias: L0 sale del primer párrafo de L1; L0 y L1 son por directorio, no por archivo |
| Búsqueda | VERIFICADO: `level` por resultado, 1 embedding, 0 VLM, 15-60 ms típico |
| Borrado | VERIFICADO: fuera del índice y del disco |
| Sesiones | VERIFICADO: commit asíncrono (~14 s), 1 VLM de ~31 KB aunque la conversación sea trivial. Tipos reales: entities, events, identity, preferences, profile, soul; `patterns` no existe en el servidor |
| Reinicio | VERIFICADO: datos intactos, 0 llamadas a modelos |
| Backup | Copia en frío VERIFICADA. `ov backup` NO FUNCIONA en modo dev (`Admin API requires api_key mode`); con clave de usuario sí. ⚠️ `--include-vectors` falló (`Cannot export incomplete OpenViking vector index snapshot`), causa sin determinar |

### 2.5 Plugin de Hermes y seguridad

**VERIFICADO:** no viene en Hermes. Sale de `plugin-catalog/openviking.yaml`: `volcengine/OpenViking`, sha `e855796c83f9eb575d9b0f3082926660730f6a63`, `examples/hermes-plugin`, versión 2.1.2, tier `community`, `requires_hermes >=0.21.4`, licencia MIT. Añade 6 `viking_*`, que no saltan la lista blanca (`Tool 'viking_search' does not exist.`).

| Riesgo | Evidencia | Regla afectada |
|---|---|---|
| Memoria etiquetada como autoritativa | `Treat as authoritative reference data` en `agent/memory_context.py`, dentro del mensaje user | MASTER_PLAN §10.7, CLAUDE.md §8 |
| Cerco parcial | `</memory-context>` se elimina, pero un `[System note: ...]` falso sobrevive dentro. `viking_read` devuelve el texto sin sanear | Memoria como datos no confiables |
| `viking_add_resource` | Ingirió un `~/.ssh/id_rsa` falso y lo envió al VLM; `raise_if_read_blocked` permite `.ssh` y `/etc/shadow` | Rutas permitidas |
| `viking_forget` | Borra sin confirmación | Destructivas con confirmación |
| Toolset `memory` todo o nada | Con él entran las 6 y la memoria nativa. Excluirlo quita el aviso "evidence, not instructions", pero la memoria se sigue inyectando; solo `skip_memory=True` la corta | Lista blanca |

**Recomendación:** ejecutar el runner con `skip_memory=True` y dar acceso a memoria mediante herramientas MCP propias del backend que llamen a OpenViking por HTTP, con validación, confirmación y marca de no confiable. Es una propuesta derivada de estas pruebas, no ejecutada de extremo a extremo; deja sin uso el plugin y `memory.provider: openviking`, y debe registrarse en `DECISIONS.md`. Además: `recall_resources: false` si se usara el plugin, `api_key` desde el inicio, copia en frío y fijar sha.

### 2.6 Convivencia, red y licencia

- **NO FUNCIONA** en un mismo venv con `hermes-agent[mcp]`: `openviking>=0.5.3 depends on mcp>=1.27,<2` frente a `mcp==2.3.0`. **VERIFICADO** que `openviking-sdk` más Hermes y backend resuelve (108 paquetes). Venv y proceso propios.
- **VERIFICADO** sin telemetría: `strace` con 48 `connect`, todos a loopback; arranca bajo `bwrap --unshare-net`. La excepción es la descarga de §2.3.
- ⚠️ **Licencia AGPL-3.0** en `openviking` y `openviking-sdk`; el wheel no trae avisos de terceros. Si se empaqueta con Drakter hay obligaciones de código fuente. Hablarle por HTTP plano sin importar el SDK reduce exposición. **Hace falta revisión legal.**

**Veredicto:** viable, con ~600 MB permanentes y VLM remoto obligatorio aquí.

## 3. Claude Haiku 5.5

- **VERIFICADO** en [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) y [Haiku 5.5](https://platform.claude.com/docs/en/models/haiku-5-5/overview): ID `claude-haiku-5-5`, lanzado 2026-10-07, 1M de contexto, 128K de salida, effort `medium` por defecto. $0,10/$0,50 por MTok hasta 100K tokens de prompt; $0,50/$2,50 por encima.
- **VERIFICADO** contra un stub Anthropic que emula las reglas: Hermes configura `model.provider: anthropic`, `model.default: claude-haiku-5-5`. La petición cumple: `max_tokens` 128000, sin `budget_tokens`, sin sampling, sin prefill, sin `fallbacks`, y `refusal` termina con rc=1 sin reintentos.
- ⚠️ **Prueba real sin clave.** No demostrada contra la API. Las cabeceras beta `interleaved-thinking-2025-05-14` y `fine-grained-tool-streaming-2025-05-14` son heredadas y sin confirmar.
- **VERIFICADO en el stub:** tras compresión o rescate de respuesta solo-thinking, Hermes reenvía bloques inválidos, recibe 400 y reintenta sin ellos, perdiendo ese razonamiento. Afecta a cuentas creadas desde 2026-08-31. Fecha de la cuenta de Drakter desconocida.
- Trampas: sin red el contexto cae a 200K, fijar `model.context_length: 1000000`. Una clave `sk-ant-*` de tipo desconocido activa modo OAuth ("You are Claude Code"). `model.base_url` sin `/anthropic` se ignora y va a la API real. Con host que no sea anthropic.com, Hermes quita todo el thinking.
- Superar 100K tokens de prompt multiplica el precio por 5, y el umbral de compresión por defecto (0,5 de 1M) queda muy por encima: fijar umbral.

**Proveedor local falso: VERIFICADO.** Sin clave, con stub OpenAI-compatible y Hermes real:

```bash
hermes config set model.provider custom
hermes config set model.base_url http://127.0.0.1:28431/v1
hermes config set model.default stub-local-1
```

En librería, `AIAgent(base_url=..., api_key="stub-key", model=...)`. Fijar `model.context_length`. Sirve para desarrollar sin clave.

## 4. Hardware de voz

- **VERIFICADO** sin VRAM: `/sys/class/drm/card1` con driver `i915` y sin `mem_info_vram_total`; sin `/dev/nvidia*` ni `/dev/kfd`. Vulkan declara un heap de 11,15 GiB, que es RAM compartida.
- **NO FUNCIONA** CUDA: no hay GPU NVIDIA. ONNX Runtime solo ofrece Azure y CPU; CTranslate2 usa `int8` con AVX2.
- ⚠️ Vulkan con whisper.cpp es la única aceleración plausible, sin medir. OpenVINO GPU no está disponible hoy: falta el ICD de OpenCL.
- **VERIFICADO** Kokoro int8 en CPU, nunca en reposo: 4 hilos, carga 7-8: RTF 0,68-0,69, con 0,93/3,83/11,6 s para audios de 1,37/5,55/16,81 s (el líder cotejó las duraciones con los WAV). Con carga 18-25: RTF 0,93-2,26. RSS 192 MB tras cargar; ~435 MB por frases; 900 MB con texto largo.
- **VERIFICADO** `create_stream` no trocea por frases: 306 caracteres llegaron en un fragmento. La app debe trocear; primer audio ~1 s con 20 caracteres, 3,8-4,7 s con 80.
- **VERIFICADO** Silero VAD: 0,65 % de un núcleo.
- ⚠️ Faster-Whisper sin medir, no se descargan modelos. Inferido con ±50 %: `base` 1,5-4 s y `small` 5-12 s por turno, porque el encoder procesa 30 s aunque se hable 2.
- ⚠️ Calidad de voz sin evaluar: no se reprodujo sonido.

**Recomendación:** voz viable por turnos, no en tiempo real: 3-9 s estimados más el LLM. `base` int8, `beam_size=1`, `language="es"`, `cpu_threads=4`, medir antes de elegir. Kokoro con síntesis por frases y 4 hilos. Nube opcional con consentimiento. Limita la CPU, no la RAM.

Cambios propuestos en el plan: §20.3 con hardware real; §21-22 y §30, síntesis y cancelación por frase; Fase 12, medir `base`, `small` y Piper; cambiar "Medir VRAM" por RAM y térmica; corregir `.claude/CLAUDE.md` §2.

## 5. Presupuesto de memoria

Medido: Hermes runner ~230 MB + MCP ~78 MB; OpenViking ~600 MB; Kokoro 200-900 MB. ⚠️ Backend y Electron sin medir aquí. Con 1-3 GB disponibles hoy, la carga total cabe solo si se liberan los procesos actuales de esta máquina, que no se han contado.
