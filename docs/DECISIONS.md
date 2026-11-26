# DECISIONS

Decisiones técnicas, cambios de tecnología y motivos.

## [2026-11-04] Instalación de las skills del proyecto en `.claude/skills/`
- **Contexto:** `CLAUDE.md` y `drakter-toolkit` piden instalar las skills de terceros antes de escribir código, cada una en su carpeta.
- **Decisión:** copia local en `.claude/skills/<nombre>/`, con estos orígenes:
  - `LLMTooling/agent-skills@f096e2bc`: `electron`, `electron-vite`, `electron-builder`, `vite`, `vitest`, `typescript-best-practices`, `playwright-cli`. Son paquetes `.skill` (zip); se extraen y se normalizan a LF los `SKILL.md` que venían con CRLF.
  - `obra/superpowers@22f0b463` (MIT): 14 skills sueltas, sin `test-driven-development`. Se reescribe `superpowers:<x>` a `<x>` porque ya no van como plugin, se añade una nota de TDD desactivado a las 6 skills que lo mencionan y se quitan las exigencias explícitas de cargar TDD. No se instala el hook `SessionStart` del plugin.
  - `NousResearch/hermes-agent@785c2e51` (MIT): `skills/autonomous-ai-agents/hermes-agent`.
  - `frontend-design`: idéntica a `anthropics/skills@ca45fc49`.
  - `skill-creator`: se conserva la versión que ya estaba en el proyecto; no es la de `anthropics/skills`, que incluye evals y benchmarks.
  - `drakter-toolkit.md` pasa a `drakter-toolkit/SKILL.md`, la ruta que cita `CLAUDE.md`.
- **Alternativas descartadas:** instalar superpowers como plugin (quedaría fuera de `.claude/skills/` y activaría TDD); una única carpeta `superpowers/` (Claude Code no descubre skills anidadas); las 105 skills de LLMTooling (ver la entrada siguiente).
- **Motivo:** cada skill en su carpeta, versionada con el proyecto y sin TDD obligatorio.
- **Impacto:** `.claude/skills/`. Una actualización futura de superpowers debe repetir las adaptaciones. Los scrapers de `vite` y `electron-builder` y el `screenshot.js` de `playwright-cli` se revisaron por encima y no se han ejecutado.

## [2026-11-04] Marketplace de plugins `claude-market` añadido a mano (solo este proyecto)
- **Contexto:** `/plugin` no está disponible en este entorno, así que no se puede usar `/plugin marketplace add`.
- **Decisión:** registrar el marketplace en `.claude/settings.local.json` con `extraKnownMarketplaces` (fuente git `https://github.com/claude-market/marketplace.git`). Es un fichero local y no se versiona. No se ha instalado ningún plugin.
- **Revisión previa:** clonado en un directorio temporal de la sesión, commit `8cda5e18`. Contiene 3 plugins (`plugin-builder` 1.3.2, `specforge` 0.1.2, `specforge-backend-rust-axum` 1.0.0) hechos de Markdown: comandos, agentes y skills. No hay hooks, ni servidores MCP, ni llamadas de red en los manifiestos.
- **Alternativas descartadas:** `~/.claude/settings.json` (afectaría a todos los proyectos); `.claude/settings.json` (se versionaría y lo verían los demás).
- **Impacto:** `.claude/settings.local.json`. Para activar un plugin concreto hará falta añadir `enabledPlugins`, o instalarlo desde una sesión interactiva con `/plugin`.
- **Actualización:** se activa `plugin-builder@claude-market` en `enabledPlugins` de `.claude/settings.local.json`. `specforge` y `specforge-backend-rust-axum` quedan sin activar (el backend es Python + FastAPI).

## [2026-11-04] Selección de skills de LLMTooling en lugar de todas
- **Contexto:** `CLAUDE.md` pedía las 105 skills de `LLMTooling/agent-skills`, muchas ajenas a Drakter (Android, Wear OS, Minecraft, Angular…), y cada una añade su descripción al contexto de cada sesión.
- **Decisión:** instalar 19 skills de `LLMTooling/agent-skills@f096e2bc`: las 7 iniciales más `shadcn`, `tailwind-css`, `react-19`, `radix-ui`, `lucide-react`, `fastapi`, `pydantic-dev`, `python-best-practices`, `fastmcp-sdk`, `motion`, `react-arborist`, `pdf-to-markdown`. Se actualizan `CLAUDE.md` (sección 6) y `drakter-toolkit` a petición del usuario.
- **Alternativas descartadas:** `electron-store` (segundo origen de datos frente al Workspace), `pytest`/`jest`/`mypy` (política de pruebas mínima), `modern-frontend-design` (duplica `frontend-design`).
- **Motivo:** cubrir el stack real, sobre todo el backend, sin cargar skills que no se van a usar.
- **Impacto:** `.claude/skills/`, `.claude/CLAUDE.md`, `drakter-toolkit`. Los scripts incluidos (scrapers de documentación y `convert_pdf.py`) se revisaron por encima y no se han ejecutado; `pdf-to-markdown` necesita `pymupdf4llm` cuando se use.

## [2026-11-04] Memoria: nativa de Hermes + OpenViking con capas L0/L1/L2
- **Contexto:** los documentos se contradecían (`PLAN_DISEÑO` usaba Hermes + OpenViking; `MASTER_PLAN`, `ROADMAP` e `IMPLEMENTATION_STATUS`, OpenViking + Hindsight + Mem0). El usuario decide usar la memoria nativa de Hermes y OpenViking, con sus capas L0, L1 y L2 y su indexación.
- **⚠️ Actualización:** en v1 esta decisión queda sin aplicar (entrada "Memoria v1 en SQLite + FTS5; OpenViking desactivado"), a falta de que el usuario lo confirme (U-1).
- **Decisión:** OpenViking ocupa el único lugar de proveedor externo de Hermes mediante su plugin (`memory.provider: openviking`), junto a `MEMORY.md` y `USER.md`. Hindsight y Mem0 salen del plan. El Memory Adapter queda como servicio del backend para la interfaz y la ingesta. Diseño en `MASTER_PLAN.md` §10.
- **Parte relacional:** verificado en su documentación que OpenViking no ofrece una base relacional de memorias: tiene AGFS, índice vectorial y SQLite/MySQL interno para colas y tareas. La parte relacional de Drakter la cubre SQLite del Workspace.
- **Alternativas descartadas:** memoria triple (solapa extracción, coste y fuentes de verdad; Hindsight y Mem0 chocan en dependencias); llamar a OpenViking solo desde el adapter (se perdería la integración nativa de herramientas y extracción).
- **Motivo:** decisión del usuario. Reduce a un motor externo y aprovecha la carga progresiva.
- **Riesgos abiertos:** `bge-small-zh` no es adecuado para asumir buen español; no hay proveedor directo de Anthropic para L0/L1; AGPL-3.0; extracción de sesión expuesta a inyección; permisos por herramienta del plugin sin verificar. Ninguno se ha probado en ejecución.
- **Verificado:** `openviking` 0.5.3 en PyPI (2026-11-02), `requires-python >=3.10`, wheels `cp310-abi3` para Linux x86_64. Fuentes: documentación de OpenViking y de proveedores de memoria de Hermes.
- **Impacto:** `MASTER_PLAN.md` §10 y referencias, `ROADMAP.md`, `PLAN_DISEÑO`, `IMPLEMENTATION_STATUS.md`, `CLAUDE.md` §2, `drakter-toolkit`.

## [2026-11-04] Drakter-orquestator como agente principal y flota anidada
- **Contexto:** el usuario pide un orquestador principal que gestione, cree y despliegue agentes, subagentes y agentes que crean subagentes. `orchestrator.md` tenía el frontmatter sin cerrar, y `agent-forge`, `contract-architect`, `integrator`, `docs-keeper` y `researcher` no existían.
- **Decisión:** se crean `drakter-orquestator` (activado con `"agent"` en `.claude/settings.local.json`), `drakter-lider` (sublíder con la herramienta `Agent`), los cuatro agentes de apoyo y la skill `agent-forge`. Se elimina `orchestrator.md`, cuyo contenido pasa al nuevo agente (recuperable en Git).
- **Corrección:** `CLAUDE.md` afirmaba que los subagentes no pueden lanzar subagentes. La documentación actual de Claude Code permite hasta 3 niveles bajo el hilo principal (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`).
- **Alternativas descartadas:** equipos de agentes (experimentales, sin anidación y sin subagentes en segundo plano para sus miembros); `.claude/settings.json` (se versionaría y no era necesario para activarlo en esta máquina).
- **Motivo:** aprovechar la anidación real y dejar un agente principal que funcione.
- **Impacto:** `.claude/agents/`, `.claude/skills/agent-forge/`, `.claude/settings.local.json`, `.claude/CLAUDE.md` §5, `drakter-toolkit`. Pendiente de comprobar en una sesión nueva.

## [2026-11-04] drakter-toolkit rehecha como mapa del tooling
- **Contexto:** la skill seguía orientada a la instalación inicial, pedía instalar superpowers como plugin y no recogía la flota ni lo instalado después.
- **Decisión:** reescribirla con el inventario real: 40 skills, 7 agentes en la raíz de `.claude/agents/`, 202 del catálogo, comandos, plugins, adaptaciones y trampas conocidas. Quedan registrados aquí `build-orchestrator` (`indiekitai/claude-orchestrator@7a81c78`), `find-skills`, `astraeus` (`RchGrav/astraeus@1ff17b0`) y el catálogo de `categories/`, que no constaban.
- **Alternativas descartadas:** mantener los pasos de instalación, ya ejecutados y registrados en este archivo.
- **Motivo:** que cualquier agente sepa qué hay y cómo combinarlo.
- **Impacto:** `.claude/skills/drakter-toolkit/SKILL.md`.

## [2026-11-04] Eliminación de los .docx de docs/
- **Contexto:** `docs/` tenía copias `.docx` de `IMPLEMENTATION_STATUS`, `MASTER_PLAN` y `PLAN_DISEÑO_COMPLETO_DRAKTER`, y el usuario ya las había borrado en su checkout.
- **Decisión:** eliminarlas de `drakter/build`. Los `.md` son la fuente de verdad.
- **Alternativas descartadas:** conservarlas junto a los `.md` (dos versiones del mismo documento que se desincronizan).
- **Motivo:** un único origen por documento.
- **Impacto:** `docs/`. Siguen recuperables en el historial de Git.

## [2026-11-04] build-orchestrator y astraeus pasan de gitlinks a archivos normales
- **Contexto:** `.claude/skills/build-orchestrator` y `.claude/commands/astraeus` eran gitlinks sin `.gitmodules` y llegaban vacíos a clones y worktrees.
- **Decisión:** versionar su contenido como archivos normales, sin `.git`. Origen: `indiekitai/claude-orchestrator@7a81c78` y `RchGrav/astraeus@1ff17b0`. El hash de cada árbol coincide con el de su commit de origen. Los `.git` anidados del checkout del usuario se mueven a `~/.drakter-backup/build-orchestrator.git` y `~/.drakter-backup/astraeus.git`.
- **Alternativas descartadas:** submódulos (exigen inicializarlos en cada worktree, y los agentes volverían a encontrar carpetas vacías).
- **Motivo:** que cualquier worktree tenga el tooling completo sin pasos extra.
- **Impacto:** `.claude/skills/build-orchestrator/`, `.claude/commands/astraeus/`, `drakter-orquestator`, `drakter-toolkit`. Las actualizaciones desde esos repos pasan a ser manuales.

## [2026-11-04] Preparación del repositorio: .gitignore, worktrees, Workflow y RUN_STATE
- **Contexto:** faltaba `.gitignore` en la raíz, los worktrees salían de `origin/main`, el orquestador limitaba `Workflow` y no había un sitio para el estado operativo.
- **Decisión:** añadir `.gitignore` con secretos, configuración local, dependencias y estado de AO (`.ao/`, `.claude/.gitignore`). Fijar `"worktree": {"baseRef": "head"}` y `"workflowSizeGuideline": "unrestricted"` en `.claude/settings.local.json`. Levantar la restricción de `Workflow` en `drakter-orquestator`. Crear `docs/RUN_STATE.md`.
- **Alternativas descartadas:** `.claude/settings.json` (se versionaría una preferencia de esta máquina).
- **Motivo:** decisión del usuario, para que el trabajo paralelo parta de la rama actual y sin tope de tamaño.
- **Impacto:** `.gitignore`, `.claude/settings.local.json` (no versionado, hay que fijarlo en cada checkout nuevo), `.claude/agents/drakter-orquestator.md`, `docs/RUN_STATE.md`. `RUN_STATE.md` se suma a los tres documentos de control de `CLAUDE.md` §2 como foto operativa. `CLAUDE.md` no mencionaba gitlinks ni `Workflow`, así que no ha cambiado.

## [2026-11-04] Anidación de drakter-lider comprobada
- **Contexto:** la entrada del orquestador dejaba la anidación pendiente de comprobar. Desde una sesión ya abierta falla con `Agent type 'drakter-lider' not found`, porque la lista de agentes se carga al arrancar y el agente se añadió después.
- **Decisión:** comprobarla en una sesión nueva de `claude -p` sobre un worktree temporal de `drakter/build`. El flujo registró `principal → drakter-lider → general-purpose` y la cadena de prueba volvió intacta.
- **Alternativas descartadas:** dar la anidación por buena solo por el frontmatter (no demuestra que funcione en ejecución).
- **Motivo:** dos niveles bajo el hilo principal funcionan sin configuración adicional. El tercer nivel no se ha probado.
- **Impacto:** `drakter-toolkit`, `docs/RUN_STATE.md`. Los agentes nuevos solo se pueden usar en sesiones arrancadas después de añadirlos.

## [2026-11-04] Jerarquía de documentos y numeración única de fases
- **Contexto:** los planes se contradecían y cada uno numeraba las fases a su manera. "Fase 15" significaba ampliaciones prohibidas en `MASTER_PLAN` y Skills obligatorias en `ROADMAP`. `CLAUDE.md` situaba los documentos en la raíz y hablaba de "exactamente tres". Hallazgos C-02, C-03, C-04, C-36 a C-39 y C-44 del dossier.
- **Decisión:** prevalece, en este orden, la entrada más reciente de `DECISIONS.md`, `CLAUDE.md`, `MASTER_PLAN.md`, `ROADMAP.md` y `PLAN_DISEÑO_COMPLETO_DRAKTER.md`. Lo verificado en la realidad corrige a todos, y una inversión de ese orden exige entrada aquí. Los documentos viven en `docs/`. `IMPLEMENTATION_STATUS.md` es la única lista viva de casillas; las de `MASTER_PLAN` y `ROADMAP` son históricas; `RUN_STATE.md` es la foto operativa. Formato de esta bitácora: el de `CLAUDE.md` §2, con campos adicionales opcionales. La fase se identifica por el **paso** del orden real de 20 pasos:

| Paso | Contenido | MASTER | ROADMAP | PLAN_DISEÑO | Checklist |
|---|---|---|---|---|---|
| 1 | Arquitectura y repositorio | 0 | 0-1 | 0 | 0 |
| 2 | Electron + React | 1 | 2 | 1 | 1 |
| 3 | FastAPI + SQLite | 1 | 3 | 1 | 2 |
| 4 | Comunicación GUI-backend | 1 | 3 | 1 | 2 |
| 5 | Hermes + Claude Haiku 5.5 | 2 | 4 | 1 | 3 |
| 6 | Personalidad y contexto | 3 | 5 | 8 | 4 |
| 7 | Personaje | 4 | 6 | 2 | 5 |
| 8 | Modelo de datos | 5 | 7 | 3 | 6 |
| 9 | Tareas y proyectos | 6 | 8-9 | 3 | 7 |
| 10 | Hábitos | 7 | 10 | 4 | 8 |
| 11 | Calendario y asignaturas | 7 | 11-12 | 4 | 9 |
| 12 | Almacén e indexación | 8 | 13 | 5 | 10 |
| 13 | Relaciones avanzadas | 9 | 14 | 3 y 5 | 11 |
| 14 | Integración de herramientas y Skills | 11 | 15 | 3 y 6 | 13 |
| 15 | Memoria avanzada | 10 | 16 | 6 | 12 |
| 16 | Voz local | 12 | 17 | 7 | 14 |
| 17 | Automejora controlada | 13 | 18 | 9 | 15 |
| 18 | Seguridad | 14 | 19 | 10 | 16 |
| 19-20 | Optimización, empaquetado y lanzamiento | 14 | 20 | 10 | 17 |
| Fuera de alcance | Ampliaciones futuras | 15 | 21 | — | 18 |

- **Pruebas y autonomía:** `CLAUDE.md` §3 y §4 sustituyen las suites, los tests de cierre de fase y las esperas de aprobación de `ROADMAP` y `MASTER_PLAN`. Lint, typecheck y build siguen como comprobación rápida. Se conservan las reglas de `ROADMAP` sobre seguridad, secretos, acciones destructivas, no marcar sin evidencia y no presentar mocks como integraciones.
- **Alternativas descartadas:** fusionar los planes en uno (obliga a rehacer 6.000 líneas sin aportar nada); renumerar las fases de cada plan (rompe las citas existentes).
- **Motivo:** un solo criterio para resolver conflictos y un solo identificador de fase.
- **Impacto:** cabeceras de los tres planes, `CLAUDE.md` §2, §3 y §7, `IMPLEMENTATION_STATUS.md`.

## [2026-11-04] Hardware real y paralelismo acotado
- **Contexto:** `CLAUDE.md` y `MASTER_PLAN` daban por hechos 32 GB de RAM y 4 GB de VRAM (C-40), y el paralelismo sin límite chocaba con la máquina (C-46).
- **Decisión:** la máquina de desarrollo y de comprobación es un i7-8665U de 8 hilos con 14 GB de RAM y gráfica integrada Intel UHD 620, sin VRAM dedicada. Voz y OpenViking se dimensionan para CPU; las cifras de rendimiento solo se publican medidas. Las casillas "Medir VRAM" pasan a medir uso de CPU y RAM. El reparto de agentes se mantiene máximo para lectura y edición, con dos frenos: como mucho 2 instalaciones o compilaciones pesadas a la vez y ningún lanzamiento nuevo con `MemAvailable` por debajo de 300 MB.
- **Comprobado el 2026-11-04 en esta máquina:** `lspci` solo lista la Intel UHD 620, `nvidia-smi` no existe, `MemTotal` da 15.589.436 kB y `lscpu` da 8 CPU. Cuando se escribió, `drakter/verificacion` no tenía commits propios; después ha publicado `docs/research/verificacion.md`.
- **Sin comprobar:** si el destino final es otra máquina con 32 GB y GPU. Esto solo puede confirmarlo el usuario; si lo es, se reabre esta entrada.
- **Alternativas descartadas:** conservar 32 GB y 4 GB como objetivo (llevaría a elegir modelos que aquí no se pueden medir).
- **Motivo:** la orden del usuario fija estos frenos, y dimensionar con datos que no se han medido produce decisiones falsas.
- **Impacto:** `CLAUDE.md` §2 y §5, `MASTER_PLAN` Parte IX, `IMPLEMENTATION_STATUS.md` Checklist 17.

## [2026-11-04] Python 3.12 para el backend, con Hermes y OpenViking en entornos propios
- **Contexto:** ningún plan fijaba versión. El sistema trae Python 3.14.4 y 3.12.16. `drakter/backend-base` declara `requires-python = ">=3.12,<3.13"`. Un primer razonamiento atribuía el 3.12 del backend a Hermes, y era erróneo: Hermes no lo condiciona.
- **Decisión:** Python 3.12 es obligatorio para `backend/` y para todo el código propio que corra en su entorno, por elección propia del proyecto. Hermes es el tag v0.22.7 (`b200f5bc`), instalado desde git, en venv propio y ejecutado como subproceso, con Python 3.14. Cuando se active, OpenViking irá en otro entorno, con 3.12 o 3.13. Ningún entorno se comparte.
- **Hermes y Python, comprobado en el checkout de ese tag:** `.python-version` es 3.14, el lock es para 3.14.x y el venv instalado da Python 3.14.10. En cambio, `pyproject.toml` declara `requires-python = ">=3.11,<3.15"`: el requisito de 3.14 es efectivo por el fijado de versiones, no por esa metadata, y el orquestador lo comunicó como `>=3.14`.
- **PyPI descartado para Hermes:** `pip install hermes-agent` no se usa. Nous retiró el soporte en `d84e11af4d` ("rip out brew + pip/PyPI wheel support", 2026-07-22, confirmado en el historial del checkout) y la 0.19.0 de PyPI está desfasada.
- **Sin comprobar:** desde esta rama no se ha ejecutado Hermes. `backend/app/integrations/hermes/CONTRACT.md`, en `drakter/agente-hermes`, afirma que `hermes --version` confirma el commit.
- **Alternativas descartadas:** subir el backend a 3.14 (el código escrito y su lock están en 3.12, y el proceso aparte hace innecesario igualarlos); un solo entorno para todo (mezcla dependencias de licencias y ritmos distintos); instalar Hermes desde PyPI (retirado y desfasado).
- **Motivo:** el backend usa 3.12 por decisión propia. Hermes puede ir en otra versión porque corre como subproceso.
- **Impacto:** `CLAUDE.md` §1 y §9, `ROADMAP`, `backend/pyproject.toml` (ya alineado).

## [2026-11-04] Los 14 archivos de identidad viven en agent/identity/
- **Estado:** REVOCADA por la entrada "Identidad repartida en identity/, context/ y knowledge/". Se conserva como historial.
- **Contexto:** `MASTER_PLAN` y `ROADMAP` los repartían en `identity/`, `context/` y `knowledge/`. `PLAN_DISEÑO` los ponía en `~/.hermes/` y `config/`, y `CLAUDE.md` §8 solo cita `agent/identity/`. El commit `c487985` de `drakter/identidad-personaje` los creó los 14 en `agent/identity/` (C-14).
- **Decisión:** los 14 archivos están en `agent/identity/`: `SOUL`, `PERSONALITY`, `BEHAVIOR`, `COMMUNICATION`, `EMOTIONAL_STYLE`, `VALUES`, `USER`, `ENVIRONMENT`, `PREFERENCES`, `CURRENT_CONTEXT`, `CAPABILITIES`, `WORKSPACE_GUIDE`, `TOOL_GUIDE` y `SYSTEM_GUIDE`, todos `.md`. `agent/context/` y `agent/knowledge/` no forman parte de la estructura vigente (ver la nota ⚠️ de esta entrada). La fuente es el repositorio: un cargador compone esos archivos y los publica en el `HERMES_HOME` de un perfil propio, y comprueba el tope de 20.000 caracteres de los archivos de contexto de Hermes, porque un recorte podría eliminar reglas del centro.
- **Sin comprobar:** la carga real en Hermes.
- **Alternativas descartadas:** mantener tres carpetas (rompería lo ya escrito sin beneficio); `~/.hermes/` como fuente (dejaría la personalidad fuera del repositorio).
- **Resolución:** el desajuste entre esta entrada y `d88fb4e`, que dejó 22 archivos en `drakter/build`, lo cierra la revocación.
- **Motivo:** `CLAUDE.md` §8 y el código ya existente.
- **Impacto:** `MASTER_PLAN` §8.1 y Parte XII, `ROADMAP` Fase 5 y árboles, `PLAN_DISEÑO` §5, `drakter-orquestator`.

## [2026-11-04] Estado `offline` en lugar de `sleeping`
- **Contexto:** `CLAUDE.md`, `MASTER_PLAN` y `ROADMAP` usan `offline` como noveno estado; `PLAN_DISEÑO` §6.2 usa `sleeping` (C-33).
- **Decisión:** los 9 estados son `idle`, `listening`, `thinking`, `speaking`, `executing`, `success`, `error`, `interrupted` y `offline`. `sleeping` desaparece.
- **Alternativas descartadas:** tener ambos (un décimo estado que nadie emite).
- **Motivo:** `CLAUDE.md` §2 prevalece, y el personaje de `drakter/identidad-personaje` ya usa estos nueve.
- **Impacto:** `PLAN_DISEÑO` §6.2.

## [2026-11-04] La memoria no se impone a la instrucción actual
- **Contexto:** el orden de prioridad pone la memoria (6) antes de la instrucción actual (7). Leído literalmente, un recuerdo, incluso envenenado, vencería a lo que el usuario pide ahora, y eso contradice que la memoria sea dato no confiable (C-45).
- **Decisión:** se mantiene el orden, y se aclara su lectura como hace `agent/knowledge/SYSTEM_GUIDE.md`: los niveles 1 a 5 enmarcan la instrucción actual; la memoria y los datos no confiables solo informan y nunca dan órdenes; el nivel 7 es lo que hay que hacer dentro de ese marco. Si la memoria contradice al usuario, vale lo que dice ahora y se señala la discrepancia. Para datos operativos, la fuente es el Workspace.
- **Alternativas descartadas:** intercambiar los niveles 6 y 7 (cambiaría una regla de `CLAUDE.md` §8 que no está mal, solo mal explicada).
- **Motivo:** cerrar la lectura peligrosa sin alterar la regla.
- **Impacto:** `CLAUDE.md` §8, `MASTER_PLAN` §8.3. La barrera real la impone el backend, no este texto.

## [2026-11-04] Huecos de MASTER_PLAN §19: borrar o mover archivos y listar hábitos
- **Contexto:** `MASTER_PLAN` §19 no tiene herramienta para eliminar o mover recursos ni para listar hábitos, aunque §24 clasifica esas acciones. `agent/knowledge/TOOL_GUIDE.md` lo señala como hueco (C-09 y dossier de contratos C-05).
- **Decisión:** §19 sigue siendo la base del catálogo. Se añade `list_habits`, de solo lectura. Eliminar o mover recursos queda sin herramienta de agente en la v1: se hace desde la GUI, con confirmación. Si el agente recibe esa petición, lo dice y no improvisa un sustituto. El catálogo definitivo lo congela `drakter/contratos`; si difiere, manda su entrada posterior aquí.
- **Alternativas descartadas:** añadir `delete_resource` y `move_resource` al agente (amplía la superficie destructiva antes de que exista el flujo de confirmación).
- **Motivo:** menor superficie destructiva para el agente, y coherencia con lo que dicen ya las guías de identidad.
- **Impacto:** `MASTER_PLAN` §19, `ROADMAP` Fase 15, `PLAN_DISEÑO` §13.

## [2026-11-04] Las expresiones no tienen campo propio
- **Contexto:** `MASTER_PLAN` §6.3 lista 10 expresiones, `PLAN_DISEÑO` §5 otras 10 y `PLAN_DISEÑO` §6.2, 7. El objeto expresivo de `PLAN_DISEÑO` (`state`, `tone`, `intensity`, `speech_rate`, `voice_profile`, `animation`) no tiene campo `expression`, y `agent/identity/EMOTIONAL_STYLE.md` indica elegirla en `animation` (C-33).
- **Decisión:** el catálogo cerrado son las 7 de `PLAN_DISEÑO` §6.2: `neutral`, `curious`, `focused`, `happy`, `concerned`, `confused`, `calm`. La expresión viaja en `animation`; no se añade un campo `expression` al objeto que genera el modelo. La app valida cada valor contra su catálogo. El nombre del campo que transporte la expresión en el evento `agent.expression_changed` lo fija `drakter/contratos`.
- **Alternativas descartadas:** el catálogo de 10 de `MASTER_PLAN` (Sorpresa, Satisfacción, Frustración y Atención no tienen arte ni guía de uso); añadir un campo propio (duplica `animation`).
- **Motivo:** es lo que ya definen las guías de identidad y el personaje provisional.
- **Impacto:** `MASTER_PLAN` §6.3, `PLAN_DISEÑO` §5, contrato de eventos.

## [2026-11-04] agent/context/USER.md es plantilla; el USER.md vivo es el de Hermes
- **Contexto:** los datos del usuario tenían varias fuentes: `agent/context/USER.md` y `PREFERENCES.md` en el repositorio, `USER.md` nativo de Hermes y perfil y preferencias de OpenViking (C-15).
- **Decisión:** en el repositorio solo se versionan plantillas sin datos reales. El `USER.md` nativo, en el `HERMES_HOME` del perfil de Drakter, guarda lo esencial, y OpenViking, lo demás. La plantilla rellenada por el usuario vive fuera del repositorio, en el directorio de datos de Drakter, y solo inicializa el `USER.md` nativo; a partir de ahí manda el nativo. `PREFERENCES.md` sigue el mismo criterio.
- **Sin comprobar:** el cargador no existe todavía, y el ciclo de inicialización no se ha ejecutado.
- **Alternativas descartadas:** rellenar el archivo versionado (metería datos personales en Git); eliminar la plantilla (se perdería la estructura que espera la identidad).
- **Motivo:** un único origen vivo y ningún dato personal en el repositorio.
- **Impacto:** `MASTER_PLAN` §8 y §10, `PLAN_DISEÑO`, cargador de identidad.

## [2026-11-04] Eventos WebSocket distintos entre planes: pendiente de drakter/contratos
- **Contexto:** `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4 dan listas distintas, y `MASTER_PLAN` no tiene evento para `idle` (C-32). `backend/CONTRACT.md` deja los eventos de negocio fuera de su alcance, y a fecha de esta entrada `drakter/contratos` no ha publicado el catálogo.
- **Decisión:** no se decide aquí. Lo resuelve `drakter/contratos` con entrada propia. Hasta entonces, `ROADMAP` §5.4 es la base de trabajo por ser la única lista tipada y versionada, y las listas de `MASTER_PLAN` §6.5 y `PLAN_DISEÑO` §6.4 son orientativas.
- **Estado:** RESUELTA por la entrada "Eventos WebSocket resueltos en contracts/".
- **Alternativas descartadas:** fijar aquí la lista final (es una decisión de contrato y otro frente la tiene asignada).
- **Motivo:** evitar dos contratos.
- **Impacto:** `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4 quedan remitidos a esa entrada.

## [2026-11-04] Puente Hermes-backend y flujo de una petición
- **Contexto:** `PLAN_DISEÑO` fijaba MCP, `MASTER_PLAN` describía Skills que llaman a la API, y `CLAUDE.md` lo dejaba por investigar (C-08, C-13, C-42, C-48). El flujo de `MASTER_PLAN` §28 recuperaba memoria antes de Hermes, pero las herramientas `viking_*` se usan dentro de su bucle.
- **Decisión:** Hermes corre como proceso aparte, supervisado por FastAPI: `hermes gateway run` con API server en loopback, venv y `HERMES_HOME` propios, versión fijada (tag v0.22.7, `b200f5bc`, desde git, nunca PyPI) y un `AgentProvider` por encima para que el proveedor siga siendo intercambiable. Las herramientas las sirve el backend por MCP en loopback, en un servidor delgado sin lógica de negocio que usa los mismos servicios que la API; Hermes es solo cliente. El perfil lleva lista de permitidos. El backend entrega mensaje y contexto de sesión, y la recuperación de memoria ocurre dentro de Hermes. (Revocado: ver "El backend recupera los recuerdos".) Skills e identidad tienen su fuente en `agent/` y se publican al perfil. Sigue sin importarse `AIAgent` en FastAPI.
- **Actualización:** el mecanismo `hermes gateway run` queda sustituido por la entrada "Hermes sin gateway: runner propio sobre AIAgent". El resto de esta entrada sigue vigente.
- **Sin comprobar:** nada de esto se ha ejecutado; proviene de leer el código de v0.22.7. Quedan por probar la lista de permitidos real, el nombre visible de las herramientas MCP, si puede bloquearse del todo la escritura de Skills y la RAM consumida.
- **Alternativas descartadas:** importar `AIAgent` en FastAPI (rompe la separación de procesos y mezcla dependencias); Skills que llaman a la API (no valen como frontera de herramientas).
- **Motivo:** el modelo y Hermes se tratan como no confiables; la frontera real es el backend. Esto invierte `MASTER_PLAN` §28.
- **Impacto:** `CLAUDE.md` §2, `MASTER_PLAN` §28 y Parte XII, `ROADMAP`. El conflicto con `agent/knowledge/SYSTEM_GUIDE.md` (paso 2) y `builder.py` lo cierra la entrada "El backend recupera los recuerdos".

## [2026-11-04] Memoria sin pipeline propio ni recuerdos en el repositorio
- **Contexto:** `MASTER_PLAN` §11, `ROADMAP` y la Checklist 12 seguían pidiendo archivos de recuerdos en `memory/` y una extracción propia, en contra de la decisión de memoria nativa + OpenViking (C-05, C-11, C-12, C-16, C-17).
- **Actualización:** en v1 no hay OpenViking que configurar (entrada "Memoria v1 en SQLite + FTS5; OpenViking desactivado"): extracción, deduplicación y contradicciones van en el Memory Adapter del backend. Se mantiene que `memory/` no guarda recuerdos.
- **Decisión:** `memory/` guarda configuración e integración, nunca recuerdos ni datos personales. Extraer, clasificar, deduplicar y resolver contradicciones se configura y se comprueba en OpenViking; lo que falte se anota con ⚠️. ByteRover sale de la memoria del producto y queda como utilidad opcional de desarrollo. La casilla "Skill de memoria" pasa al paso 15. La ingesta del almacén en OpenViking es opcional por recurso, viene apagada y pasa siempre por el backend. Esto último cambia el flujo de `MASTER_PLAN` §10.
- **Alternativas descartadas:** pipeline propio (duplica lo que aporta OpenViking y anula la decisión anterior).
- **Motivo:** aplicar la decisión de memoria ya tomada.
- **Impacto:** `MASTER_PLAN` §10-§11, `ROADMAP` Fase 16, `IMPLEMENTATION_STATUS.md` Checklists 12 y 13, `CLAUDE.md` §5.

## [2026-11-04] Herramientas con su módulo; confirmación y auditoría antes de la primera
- **Contexto:** `MASTER_PLAN` y las checklists crean herramientas en cada módulo, `ROADMAP` las concentra en su Fase 15, y los tres dejan confirmación y auditoría para después de exponer herramientas destructivas. Ningún documento define el flujo de confirmación, y `ROADMAP` admitía "confirmación y/o undo" (C-06, C-07, C-35, C-49).
- **Decisión:** cada herramienta se construye con su módulo y se comprueba por llamada directa; el paso 14 integra Skills y comprueba la selección con modelo. Permisos, confirmación pendiente y auditoría van en el backend base o en el modelo de datos, antes de la primera herramienta, y las casillas tardías de la Checklist 16 pasan a ser revisión y endurecimiento. La confirmación es obligatoria y el undo es adicional. Flujo: la herramienta destructiva crea una confirmación pendiente y devuelve su id sin ejecutar; solo la GUI la resuelve, por un endpoint que no es herramienta; la ejecución y la auditoría ocurren después. Los detalles los congela `drakter/contratos`.
- **Alternativas descartadas:** dejar confirmaciones para el paso 18 (incumple `CLAUDE.md` §8); usar las aprobaciones nativas de Hermes (solo cubren comandos de shell).
- **Motivo:** `CLAUDE.md` §8.
- **Impacto:** `MASTER_PLAN` Partes VIII y XVI, `ROADMAP` §5.5 y Fases 15 y 19, `IMPLEMENTATION_STATUS.md` Checklist 16.

## [2026-11-04] Datos fuera del repositorio y estructura de carpetas
- **Contexto:** los árboles de `MASTER_PLAN` y `ROADMAP` ponen datos reales dentro del repositorio, y `PLAN_DISEÑO` propone otra estructura. `MASTER_PLAN` pide crear todas las carpetas al inicio y `ROADMAP` lo prohíbe (C-20 a C-22).
- **Decisión:** los datos de ejecución viven en `DRAKTER_DATA_DIR`, que por defecto es el `user_data_dir("drakter")` ya fijado en `backend/CONTRACT.md`; `workspace/` no guarda datos. La estructura es la de `MASTER_PLAN` Parte XII con las desviaciones registradas aquí, y se descartan `apps/` y `docker-compose`. Las carpetas se crean cuando entra código. La configuración no sensible puede versionarse; la sensible, nunca.
- **Alternativas descartadas:** datos en `workspace/` ignorados por Git (se pierden con un `git clean` y mezclan código con datos personales).
- **Motivo:** el código ya escrito lo hace así, y es la opción más segura.
- **Impacto:** `MASTER_PLAN` Parte XII, `ROADMAP` árbol y §2, `PLAN_DISEÑO` §17, `CLAUDE.md` §9.

## [2026-11-04] Trabajo sin clave y alcance de automejora, copias y v1
- **Contexto:** las reglas del plan impiden cerrar el paso 5 sin clave de API (C-47), `PLAN_DISEÑO` permitía cambios sin aprobación en automejora (C-50), las copias de seguridad difieren (C-19), `PLAN_DISEÑO` metía en la v1 lo que `MASTER_PLAN` aplaza (C-41) y las casillas del `.riv` no pueden cumplirse con código (C-43).
- **Decisión:**
  - **Sin clave:** el paso 5 queda con ⚠️, el adaptador se construye con un doble identificado como mock, y ninguna casilla de conversación, personalidad, selección de herramientas o memoria se marca hasta probarla con clave.
  - **Automejora:** lo publicado al agente en uso cuenta como producción. Todo cambio pasa por propuesta y autorización, también en Skills.
  - **Copias:** incluyen SQLite, configuración, identidad, Skills, datos de OpenViking y home de Hermes, sin secretos.
  - **Alcance v1:** paneles y automatizaciones avanzadas quedan fuera, con un mínimo local que dispara recordatorios. Sin Recharts ni Docker hasta necesitarlos. SQL propio para el modelo de datos (entrada "SQL propio sin Alembic").
  - **Credenciales:** un único origen, `~/.config/drakter/.env`.
  - **Rive:** el personaje provisional cubre el trabajo por código, y las casillas del `.riv` llevan ⚠️ hasta que el usuario lo diseñe.
- **Alternativas descartadas:** marcar el paso 5 como hecho con el mock (`ROADMAP` lo prohíbe y `CLAUDE.md` §2 también).
- **Motivo:** `CLAUDE.md` §2 pide anotar lo bloqueado y seguir, y §8 no admite excepciones en automejora.
- **Impacto:** `IMPLEMENTATION_STATUS.md`, `MASTER_PLAN` Partes X y XI, `ROADMAP` Fases 18 y 19, `PLAN_DISEÑO`.

## [2026-11-04] Contratos de datos que resuelve drakter/contratos
- **Contexto:** quedan conflictos de esquema y de catálogo que son decisiones de contrato: catálogo de herramientas y Skills (C-09, C-10), entidades y campos (C-23, C-24), pertenencia (C-25), estados (C-26), tipos de relación (C-27), calendario (C-28), asignaturas (C-29), hábitos (C-30), auditoría (C-31), permisos (C-34) y FTS (C-18).
- **Decisión:** los planes no los resuelven: remiten al contrato. Cuando `drakter/contratos` publique, su entrada en este archivo y su contrato prevalecen sobre las listas de los planes. Criterios fijos ya: fuente única de pertenencia, todo borrado definitivo confirma, y el agente no modifica permisos. Archivar es reversible y no cuenta como eliminación, salvo que supere el umbral de operación masiva.
- **Estado:** RESUELTA EN PARTE por la entrada "Eventos WebSocket resueltos en contracts/". Sigue pendiente lo que allí se indica.
- **Alternativas descartadas:** decidir el esquema desde documentación (un frente lo tiene asignado, y haría dos contratos).
- **Motivo:** evitar dos fuentes.
- **Impacto:** cabecera de los tres planes.

## [2026-11-04] Eventos WebSocket resueltos en contracts/
- **Contexto:** `drakter/contratos` publicó el commit `061975a` con `contracts/README.md`, `contracts/python/drakter_contracts/events.py` y las migraciones `0001` a `0010`. Cierra la entrada de eventos pendiente y parte de los contratos de datos.
- **Decisión:** el catálogo de eventos es `contracts/python/drakter_contracts/events.py`, con 32 tipos, y sustituye a las listas de `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4. Hay un único flujo, `WS /api/v1/events`, solo de servidor a cliente. `agent.status_changed` lleva `state` con los 9 estados; `offline` lo deriva la GUI si cae el socket o llega por `system.health_changed`. `agent.confirmation_required` pasa a ser `confirmation.requested`. Esquema, formatos, errores, reglas de datos, confirmaciones y migraciones siguen `contracts/README.md` y `backend/migrations/`. Si contradicen esta bitácora, manda la bitácora, como dice ese README.
- **Expresiones:** el objeto que genera el modelo sigue sin campo `expression` y la elige en `animation`. El evento `agent.expression_changed` la transporta en `expression`, de modo que el backend hace esa traducción.
- **Actualización:** lo que aquí constaba como pendiente ya está publicado en `drakter/build`: `contracts/tools/catalog.json` (78 herramientas), `contracts/api/routes.md`, `contracts/python/drakter_contracts/models/` y `contracts/ts/`. El catálogo incluye `list_habits` y no tiene herramienta para eliminar o mover recursos, como decidió la entrada de los huecos de §19.
- **Sin comprobar:** `contracts/` no está fusionado en `drakter/docs`, y esta entrada procede de leer la rama. `expression` es `str` y no un enumerado, así que el catálogo cerrado de 7 aún no lo impone el contrato. La traducción de `animation` a `expression` no se ha visto implementada.
- **Alternativas descartadas:** copiar el catálogo a los planes (crearía una segunda fuente).
- **Motivo:** un solo contrato.
- **Impacto:** remisiones de `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4.

## [2026-11-04] Interfaz del renderer y confirmación por REST
- **Contexto:** el orquestador comunica cómo queda el puente Electron frente al borrador. Las referencias D-13 y D-14 solo constan en comentarios de `desktop/electron/shared/` de las ramas `drakter/electron-host` y `drakter/chat-personaje`, no en este archivo.
- **Decisión:** la interfaz del renderer es `window.api.call(method, path, body)`, en lugar del `api.call(opId, args)` del borrador, y conserva la lista cerrada `ALLOWED_ROUTES` de D-14: main rechaza lo que no esté en ella y el renderer no conoce puerto ni credenciales. Se añaden `getConnection` y los resultados `conflict` y `failed` (D-13). En REST, una operación que necesita confirmación responde 409 con `error.code = "confirmation_required"`, igual que `contracts/python/drakter_contracts/errors.py`, nunca 2xx.
- **Actualización:** el token HMAC de confirmación queda retirado (entrada "Confirmación sin token HMAC").
- **Alternativas descartadas:** `api.call(opId, args)`, el borrador anterior.
- **Motivo:** decisión del orquestador; no se han recibido más motivos.
- **Impacto:** `desktop/electron/`, contrato de rutas. No se ha comprobado en ejecución.

## [2026-11-04] Servidor MCP en listener propio de loopback con puerto efímero
- **Contexto:** el borrador D-07 montaba el MCP en el puerto del backend. La referencia D-07 no consta en este archivo; la desviación la comunica el orquestador.
- **Decisión:** el MCP escucha en un listener propio de loopback con puerto efímero (`127.0.0.1:0`), dentro del proceso del backend y separado del puerto de la GUI. El WebSocket es único: `/api/v1/events`. `contracts/README.md` ya lo recoge en `drakter/contratos` (`2b48344`).
- **Alternativas descartadas:** montar el MCP en el puerto del backend (el token del agente quedaría separado de las rutas de la GUI solo por la matriz de permisos).
- **Motivo:** aislar por construcción el token del agente de toda ruta de la GUI, además de la matriz.
- **Coste:** un servidor más en el proceso.
- **Impacto:** backend, integración con Hermes. No se ha comprobado en ejecución en esta rama.

## [2026-11-04] Hermes sin gateway: runner propio sobre AIAgent
- **Contexto:** el gateway de Hermes arranca además cron y kanban. Los jobs de cron usan `platform_toolsets.cron`, cuyo valor por defecto `hermes-cron` incluye terminal, de modo que la lista blanca de `api_server` no los cubre (hallazgo H-20 del dossier). Esto se desvía de D-06, que solo consta en mensajes del orquestador.
- **Decisión:** no se usa el gateway. Un runner propio (`backend/app/integrations/hermes/runner/drakter_runner.py`) crea `AIAgent` en un proceso separado, con el venv de Hermes, y habla con el backend por JSONL en stdin y stdout. Solo usa stdlib y Hermes, sin scheduler ni cron. El runner termina con EOF en stdin. Salen `aiohttp` y `API_SERVER_KEY`. `AIAgent` sigue sin importarse en FastAPI.
- **Alternativas descartadas:** mantener el gateway con `platform_toolsets.cron: [no_mcp]` (cierra los jobs, pero `/api/jobs` y las tareas de fondo siguen vivas, sin interruptor para quitar esas rutas); importar `AIAgent` en FastAPI (mezcla procesos y dependencias).
- **Motivo:** el cron del gateway salta la lista blanca.
- **⚠️ Estado en código:** `866ad9d`, de `drakter/agente-hermes`, añade `runner/drakter_runner.py`, pero a fecha de `4a84a5d` no está en `drakter/build`. `contracts/README.md` §1 sigue citando `API_SERVER_KEY`.
- **Sin comprobar:** el runner no se ha ejecutado, ni la salida por EOF.
- **Impacto:** `CLAUDE.md` §2, `MASTER_PLAN` §28, `ROADMAP` Fase 4, `PLAN_DISEÑO` §18 y flujo de arranque, `contracts/README.md` §1.

## [2026-11-04] SQL propio sin Alembic
- **Contexto:** los planes citaban SQLAlchemy y Alembic. El dossier comprobó que un rebuild de Alembic sobre SQLite con FK activas perdía filas hijas y triggers.
- **Decisión:** migraciones `NNNN_*.sql` en `backend/migrations/`, aplicadas por `backend/app/database/migrator.py`, con las reglas de `contracts/README.md` §8. Acceso con `sqlite3` y SQL propio. Sin Alembic ni SQLAlchemy.
- **Alternativas descartadas:** Alembic (por lo anterior) y ORM (el esquema depende de triggers y CHECK con nombre).
- **Motivo:** control total sobre triggers, auditoría y migraciones.
- **Impacto:** sustituye a lo dicho en la entrada "Trabajo sin clave y alcance de automejora, copias y v1". `ROADMAP` §2, `PLAN_DISEÑO` §2 y §11.

## [2026-11-04] Búsqueda con reconcile_structured
- **Contexto:** el índice `search_documents` es un dato derivado y puede quedarse atrás respecto a los módulos.
- **Decisión:** `reconcile_structured` (`backend/app/services/search_index.py`, rama `drakter/busqueda`) lleva al índice lo que cambió. Los borrados los resuelven `ON DELETE CASCADE` y los triggers. Si otra escritura retiene la base, la búsqueda continúa con el índice anterior.
- **Alternativas descartadas:** escribir el índice solo en la transacción de cada módulo, como dice `contracts/README.md` §4 (obliga a tocar cada módulo y cualquier olvido deja el índice mal sin aviso). Esta entrada prevalece sobre ese punto del README.
- **Motivo:** un solo punto de escritura del índice.
- **Impacto:** `backend/app/services/`, `contracts/README.md` §4.

## [2026-11-04] Recordatorios locales
- **Contexto:** el alcance v1 pide un mínimo local que dispare recordatorios.
- **Decisión:** al abrir se recupera lo vencido en las últimas 6 horas (`CATCH_UP`). Lo que solo tiene fecha avisa a las 09:00 (`MORNING`). Máximo 20 por tick (`MAX_PER_TICK`), los más antiguos primero, y el resto sale en el siguiente. `read_at` significa "ya entregada a la GUI". No hay borrado de notificaciones.
- **Alternativas descartadas:** recuperar todo lo vencido (una avalancha tras días sin abrir).
- **Motivo:** avisar de lo útil sin saturar.
- **Impacto:** `backend/app/services/reminders.py`, `backend/app/repositories/notifications.py` (rama `drakter/recordatorios`).

## [2026-11-04] Pantalla Hoy y ajustes
- **Contexto:** Hoy necesitaba criterios fijos para vencimientos, zona horaria y estado de la clave.
- **Decisión:** una tarea está vencida si está abierta y su `due_at` ya pasó o su `due_date` es anterior a hoy; con hora ya pasada hoy está vencida, no "de hoy". `GET /api/v1/today` exige `timezone`, y lo inválido da 422 `invalid_timezone`. Los ajustes se guardan por `POST /api/v1/settings/{key}`. Si la clave no está en el entorno y `.env` existe, el estado es `unknown`: el backend no abre `.env`, solo mira si existe.
- **Alternativas descartadas:** leer `.env` para informar (toca secretos sin necesidad); una zona horaria implícita (`CLAUDE.md` §9 las exige explícitas).
- **Motivo:** `CLAUDE.md` §8 y §9.
- **Impacto:** `backend/app/api/today.py`, `backend/app/api/settings.py`, `backend/app/services/settings_status.py` (rama `drakter/hoy-ajustes`).

## [2026-11-04] Límites de la memoria
- **Contexto:** al borrar un recuerdo no todo se alcanza, y el contexto de usuario no cabía en el presupuesto previsto (hallazgo N3).
- **Decisión:** `forget` borra de `memory_records` y `memory_fts`, y su `ForgetReport` declara `hermes_sessions` como no alcanzado: el texto enviado queda como residuo en la base de sesiones de Hermes. El nivel 4 (contexto del usuario) tiene un tope de 6.000 caracteres. `memory_records` vive en la base de datos del Workspace.
- **Sin comprobar:** el borrado del residuo no existe. Afecta a lo que el usuario cree haber olvidado.
- **Alternativas descartadas:** 4.000 caracteres en el nivel 4 (cortaría `CURRENT_CONTEXT`); una base aparte para memoria (otra copia de seguridad y otra fuente).
- **Motivo:** decir la verdad sobre el alcance de `forget` y no recortar el contexto.
- **Impacto:** `backend/app/integrations/memory/`, `backend/migrations/0010_memory_improvement.sql`.

## [2026-11-04] Provider custom con anthropic_messages para el stub
- **Contexto:** sin clave, las pruebas apuntan Hermes a un stub local.
- **Decisión:** con `model_provider = dev_stub`, la configuración usa `provider: custom` y `api_mode: anthropic_messages` (`backend/app/integrations/hermes/home.py`).
- **Alternativas descartadas:** `provider: anthropic` con `base_url` local: según el orquestador, iría a `api.anthropic.com`. No se ha comprobado en ejecución.
- **Motivo:** que una prueba sin clave no salga a la red.
- **Impacto:** `home.py`, herramienta `dev-llm-stub`.

## [2026-11-04] El composer aloja la transcripción
- **Contexto:** hacía falta decidir dónde se monta la conversación en el chat.
- **Decisión:** `ChatComposer` aloja `ChatTranscript` (`desktop/src/chat/ChatComposer.tsx`, rama `drakter/chat-personaje`).
- **Alternativas descartadas:** ninguna comunicada.
- **Motivo:** no se ha recibido ninguno.
- **Impacto:** `desktop/src/chat/`.

## [2026-11-04] Host de Electron: interfaz, aprobaciones y arranque
- **Contexto:** `drakter-24` comunica por el orquestador cómo queda el host. Completa la entrada "Interfaz del renderer y confirmación por REST".
- **Decisión:** la firma es `call(method, path, body, options)`, con `options` limitado a `ifMatch` e `idempotencyKey` y lista cerrada de rutas. `ALLOWED_ROUTES` lo genera `desktop/electron/scripts/generate-routes.mjs`. `ApprovalOutcome` incluye `conflict` y `failed`. Cancelar en el diálogo de aprobación rechaza. El handshake con el backend espera 120 s por las migraciones. El WebSocket no usa ping de texto. D-14 prevalece sobre `contracts/README.md` §1.
- **Resuelto en código:** `drakter/build` ya tiene `ifMatch` e `idempotencyKey` en `bridge.ts`. También están `generate-routes.mjs`, `ApprovalOutcome`, `HANDSHAKE_TIMEOUT_MS = 120_000` y el botón Cancelar con `cancelId: 0`. D-14 no consta en este archivo: solo en comentarios de código y mensajes.
- **Alternativas descartadas:** `api.call(opId, args)`.
- **Motivo:** el proceso principal es el único que conoce token y puerto.
- **Impacto:** `desktop/electron/`, `contracts/README.md` §1.

## [2026-11-04] Confirmación sin token HMAC
- **Contexto:** el token HMAC de confirmación estaba anotado como provisional.
- **Resuelto en código:** `05861f9` retira `ApprovalSigner`, y está en `drakter/build`.
- **Decisión:** se retira. Para aprobar bastan el rol `approver` de D-14 y `params_hash`, con `UPDATE` atómico sobre la fila pendiente.
- **⚠️ Desajuste con el código:** `drakter/seguridad` (`87f5481`) mantiene `ApprovalSigner` en `backend/app/permissions/credentials.py`, y su `README.md` pide `{params_hash, approval_token}` en `POST /api/v1/confirmations/{id}/approve`. Hay que quitarlo.
- **Alternativas descartadas:** mantener el HMAC (no aporta nada sobre el rol y el hash).
- **Motivo:** decisión del orquestador: el rol y el hash con transición atómica son suficientes.
- **Impacto:** `backend/app/permissions/`, `backend/app/services/actions.py`, `backend/app/api/confirmations.py`.

## [2026-11-04] Ajustes y mensajes: nombres fijados
- **Contexto:** faltaba fijar tres nombres que comparten backend y GUI.
- **Decisión:** la clave de zona horaria es `default_timezone`. La tabla `settings` se ajusta en la migración `0011_settings_value.sql`. El cuerpo de `POST /api/v1/chat/sessions/{id}/messages` lleva el texto en `text`, junto a `client_message_id`.
- **Comprobado por lectura:** `0011_settings_value.sql` está en `drakter/contratos` y `drakter/chat-personaje`, y aún no en `drakter/build`. `text` consta en `contracts/api/routes.md`.
- **Alcance de la prueba de `0011`:** se probó con datos sintéticos, no reales: `backend/migrations/check_migrations.py` inserta `default_timezone` y `bulk_threshold` y comprueba que se conservan. Los triggers obligatorios son 25 (7 de auditoría y confirmaciones, 9 `*_delete_entity`, 3 `*_no_cycle`, 3 `trg_search_*` y 3 `trg_memory_records_*`), recuento hecho sobre `contracts/README.md`. El script no se ha ejecutado desde esta rama.
- **Alternativas descartadas:** ninguna comunicada.
- **Motivo:** un solo nombre en todo el sistema.
- **Impacto:** `backend/migrations/`, `contracts/`, `desktop/src/stores/chat.ts`.

## [2026-11-04] Identidad repartida en identity/, context/ y knowledge/
- **Contexto:** la entrada "Los 14 archivos de identidad viven en agent/identity/" salió de una contradicción en las instrucciones del orquestador, no de un fallo de los planes: `MASTER_PLAN` §8.1 ya los repartía en tres carpetas y el cargador lee esas rutas.
- **Decisión:** se revoca esa entrada. Los 14 archivos quedan así: 6 en `agent/identity/` (`SOUL`, `PERSONALITY`, `BEHAVIOR`, `COMMUNICATION`, `EMOTIONAL_STYLE`, `VALUES`), 4 en `agent/context/` (`USER`, `ENVIRONMENT`, `PREFERENCES`, `CURRENT_CONTEXT`) y 4 en `agent/knowledge/` (`CAPABILITIES`, `WORKSPACE_GUIDE`, `TOOL_GUIDE`, `SYSTEM_GUIDE`). Se mantiene el resto de lo dicho allí: la fuente es el repositorio, y el cargador compone los archivos, los publica en el `HERMES_HOME` del perfil propio y comprueba el tope de 20.000 caracteres. `USER.md` y `PREFERENCES.md` son plantillas.
- **Comprobado por lectura:** `f13204a`, de `drakter/identidad-personaje`, quita los 8 duplicados y deja 14 archivos; `backend/app/integrations/memory/context/rules.py` lee `knowledge/`, `identity/` y `context/`.
- **Resuelto en código:** `drakter/build` ya tiene los 14 archivos.
- **Alternativas descartadas:** los 14 en `agent/identity/` (obliga a cambiar el cargador y se aparta de `MASTER_PLAN`, sin beneficio).
- **Motivo:** es lo que dice `MASTER_PLAN`, lo que lee el cargador, y deja la personalidad en `identity/`, como pide `CLAUDE.md` §8.
- **Impacto:** `MASTER_PLAN` §8.1 y Parte XII, `ROADMAP` árbol y Fase 5, `PLAN_DISEÑO` §5, `CLAUDE.md` §8, `RUN_STATE.md`.

## [2026-11-04] El backend recupera los recuerdos
- **Contexto:** la entrada "Puente Hermes-backend y flujo de una petición" situaba la recuperación dentro de Hermes, mientras `backend/app/integrations/memory/context/builder.py` y `agent/knowledge/SYSTEM_GUIDE.md` (paso 2) la hacen en el backend.
- **Decisión:** el backend recupera los recuerdos, y `builder.py` y `SYSTEM_GUIDE.md` son correctos. Lo recuperado se entrega siempre cercado como dato no confiable, nunca en el prompt de sistema. Es una desviación de `MASTER_PLAN` §28, ya recogida allí, y revoca esa parte de la entrada del puente.
- **Motivo:** con runner propio no hay plugin de memoria en Hermes, y el backend controla la delimitación y la procedencia.
- **Alternativas descartadas:** recuperación dentro de Hermes con `viking_*` (exige el plugin que el runner no carga).
- **Resuelto:** cómo entra OpenViking lo fija la entrada "Memoria v1 en SQLite + FTS5; OpenViking desactivado".
- **Sin comprobar:** el cercado no se ha ejecutado con Hermes ni con modelo; procede de leer `builder.py`.
- **Impacto:** `MASTER_PLAN` §10, §28, §30 y §31, `PLAN_DISEÑO`, `CLAUDE.md` §2.

## [2026-11-04] Raíces del almacén y roles de ruta
- **Contexto:** gestionar ubicaciones permitidas amplía lo que el sistema puede leer, así que no puede quedar al alcance del renderer ni del agente.
- **Decisión:** las raíces se gestionan desde el proceso principal con `window.api.addStorageLocation`, `update` y `delete`, selector nativo y token `approver`. Nacen con `read_only` y sin `agent_read`. En `storage-locations` y `permissions`, GET y HEAD usan `ui`; las escrituras, `approver`.
- **Comprobado por lectura:** `desktop/electron/main/storageRoots.ts` con `showOpenDialog` en `drakter/build`; `0005_storage.sql` tiene `read_only` con `DEFAULT 1`; `generate-routes.mjs` exige `approver` en esas rutas. No se ha ejecutado.
- **Alternativas descartadas:** un campo de ruta en el renderer (daría al renderer rutas absolutas).
- **Motivo:** las ubicaciones permitidas son una frontera de seguridad.
- **Impacto:** `desktop/electron/`, `contracts/api/routes.md`.

## [2026-11-04] Almacén en v1
- **Contexto:** `drakter-15` comunica por el orquestador el alcance del almacén.
- **Decisión:** en v1 las ubicaciones son `read_only=1`. Borrar un recurso no toca el archivo. El agente solo crea notas con `create_resource`. Las imágenes se leen sin Pillow (solo metadatos con parser propio). `.docx` no tiene lector. La caducidad de la confirmación se queda en 300 s.
- **Desajuste con el código (resuelto el 2026-11-13, ver «Cierre del desajuste de caducidad de confirmaciones»):** `CONFIRMATION_TTL_SECONDS = 300` está en `backend/app/services/actions.py` de `drakter/seguridad`, pero `drakter/build` (`488b83d`) tiene en `backend/app/services/habits_calendar_support.py` una caducidad propia de 15 minutos. Son dos caminos de confirmación con plazos distintos, y `contracts/README.md` §5 pide uno solo.
- **Alternativas descartadas:** añadir Pillow y un lector de `.docx` (más dependencias y más superficie para archivos no confiables).
- **Motivo:** menor superficie en v1.
- **Impacto:** `backend/app/services/`, `backend/app/tools/storage.py`.

## [2026-11-04] Rama verificacion integrada por squash
- **Contexto:** el historial de `drakter/verificacion` contenía una clave falsa de prueba.
- **Decisión:** se integra por squash para no publicarla.
- **Estado:** a fecha de `488b83d`, `drakter/verificacion` no es ancestro de `drakter/build` y `docs/research/` aún no aparece allí, así que el squash no se ha visto.
- **Alternativas descartadas:** fusión normal (publicaría ese historial).
- **Motivo:** no publicar nada con forma de credencial, aunque sea falsa.
- **Impacto:** historial de `drakter/build`.

## [2026-11-04] Memoria v1 en SQLite + FTS5; OpenViking desactivado
- **Estado:** DESVIACIÓN de una decisión del usuario, pendiente de que la confirme (U-1). Mientras tanto se trabaja así, y si no la confirma se reabre.
- **Contexto:** la entrada "Memoria: nativa de Hermes + OpenViking con capas L0/L1/L2" la pidió el usuario. Con el runner propio no hay plugin de memoria en Hermes, y `docs/research/verificacion.md` (en `drakter/verificacion`) midió OpenViking.
- **Decisión:** la v1 usa memoria SQLite + FTS5 tras el Memory Adapter. OpenViking queda desactivado, como opción posterior llamada desde el backend por HTTP, nunca como plugin de Hermes. `memory.provider`, las herramientas `viking_*` y las capas L0/L1/L2 de `MASTER_PLAN` §10 pasan a futuros.
- **Motivo:** unos 600 MB en reposo, servidor HTTP obligatorio, sin embeddings no indexa, y es un plugin externo. La cifra de 600 MB consta en `verificacion.md`; el resto llega del orquestador.
- **Alternativas descartadas:** OpenViking activo en v1, como plugin o por HTTP (por lo anterior, en una máquina de 14 GB).
- **Consecuencia:** se pierde en v1 la carga progresiva L0/L1/L2 y la búsqueda semántica: FTS5 busca por texto. Si U-1 se rechaza, hay que retomar `MASTER_PLAN` §10 tal como está.
- **Sin comprobar:** la calidad de recuperación con FTS5 en español.
- **Impacto:** `MASTER_PLAN` §10, `ROADMAP` §2 y Fase 16, `PLAN_DISEÑO` §8, `IMPLEMENTATION_STATUS.md` Checklist 12, `CLAUDE.md` §1 y §2, `RUN_STATE.md`. `.claude/skills/drakter-toolkit/SKILL.md` aún dice que la memoria es la nativa de Hermes + OpenViking.

## [2026-11-04] Hoy es la pantalla inicial
- **Contexto:** `MASTER_PLAN` §5.3 y `PLAN_DISEÑO` §3.2 hacían de la cara la pantalla principal.
- **Decisión:** Hoy es la pantalla inicial, con pestaña propia, y pasan a ser 10 pestañas. La cara sigue en su pestaña. Atajos: Ctrl+0 para Hoy y Ctrl+K para la búsqueda.
- **Alternativas descartadas:** mantener la cara como inicio.
- **Motivo:** prioridad del usuario de uso diario.
- **⚠️ Estado en código:** a fecha de `815976f`, `desktop/src/navigation/sections.ts` en `drakter/build` tiene 9 secciones con `home` primero, sin Hoy, y `useAppShortcuts.ts` documenta Ctrl+1 a Ctrl+9. En `drakter/desktop-shell` sí consta. Ctrl+K sí está en `SearchPalette.tsx`.
- **Impacto:** `MASTER_PLAN` §5.3, `PLAN_DISEÑO` §3.2 y §3.3, `desktop/src/navigation/`, `desktop/src/app/useAppShortcuts.ts`.

## [2026-11-13] Integración de las 22 ramas en drakter/integracion
- **Contexto:** `drakter/build` no tenía unos 140 commits de 21 ramas, y varios worktrees tenían cambios sin commit tras el reinicio de AO.
- **Decisión:** rama `drakter/integracion` desde `drakter/build` (`815976f`), fusiones `--no-ff` en el orden contratos → backend-base → seguridad → tareas-proyectos → hábitos-calendario → almacén-relaciones → memoria-contexto → agente-hermes → identidad-personaje → voz → automejora → desktop-shell → búsqueda → hoy-ajustes → docs → guías → resto. Sin conflictos textuales. Antes, los cambios pendientes de drakter-12, 16, 20, 22, 24, 30 y 31 se revisaron y se commitearon en su propia rama (el de seguridad, tras pasar `check_confirmations.py` con 0 fallos).
- **Conflictos semánticos resueltos:** (1) `app/tools/memory|search|storage.py` importaban `untrusted_envelope` de `app.tools.spec`; vive en `app.tools.envelope`. (2) La regla del registro "audit names an unknown argument" (de seguridad/agente) rechazaba los mapas de auditoría compartidos de relaciones, etiquetas, asignaturas, almacén y `get_task`: cada herramienta recibe ahora el mapa del módulo restringido a sus argumentos. (3) El runtime de Hermes creaba `SessionToken()` sin valor (API de agente-hermes) y el núcleo D-14 exige valor: se genera con `secrets.token_urlsafe(32)` y `SessionToken.reveal()` se añade para pasarlo al hijo; sin él, el supervisor habría pasado el texto redactado como token MCP.
- **Alternativas descartadas:** filtrar los mapas de auditoría en el registro (ocultaría erratas en módulos nuevos).
- **Motivo:** mínima corrección que respeta los contratos y la regla estricta del registro.
- **Impacto:** `backend/app/tools/`, `backend/app/core/security.py`, `backend/app/integrations/hermes/runtime.py`.

## [2026-11-13] Conexiones SQLite por petición sin check_same_thread
- **Contexto:** las dependencias síncronas con `yield` de almacén y de hábitos/calendario/asignaturas abrían la conexión en un hilo del threadpool y FastAPI la usaba o cerraba en otro. Con las peticiones paralelas de la GUI, casi todas daban 500 (`ProgrammingError`).
- **Decisión:** `connect(..., check_same_thread=False)` solo en esas dependencias de una petición. La conexión no se comparte: dependencia, endpoint y cierre van en secuencia, solo cambian de hilo.
- **Alternativas descartadas:** pasar los endpoints a `async` o usar el `contextmanager` de tareas (más cambios en módulos ajenos).
- **Impacto:** `backend/app/database/connection.py`, `backend/app/api/storage.py`, `backend/app/services/habits_calendar_support.py`.

## [2026-11-13] Runner de Hermes con -B
- **Contexto:** el supervisor lanza el runner con `python -I`, que ignora `PYTHONDONTWRITEBYTECODE`. El primer arranque dejó `__pycache__` en `plugins/drakter_guard/` y `verify_home` rechazó todos los siguientes ("unexpected content").
- **Decisión:** añadir `-B` a la orden del runner.
- **Impacto:** `backend/app/integrations/hermes/supervisor.py`.

## [2026-11-13] Arranque local: Electron es dueño del backend; stub elegible en desarrollo
- **Contexto:** `scripts/dev.sh all` arrancaba un backend propio y leía `Settings.port`, que ya no existe tras D-14 (puerto efímero y credenciales por stdin). Además Electron solo pasa al backend una lista blanca de variables.
- **Decisión:** `dev.sh all` valida ambos lados y lanza solo Electron; comprueba también el binario de Electron (npm 12 no ejecuta su `install.js`). En desarrollo (app no empaquetada), Electron pasa también `DRAKTER_MODEL_PROVIDER` y `DRAKTER_DEV_STUB_URL`; el backend sigue rechazando `dev_stub` en producción. Nuevo `scripts/drakter-local.sh start|stop|status` que deja stub y app desacoplados de la terminal. Hermes se expone como `~/.local/bin/hermes-python` (envoltorio al venv de `/var/tmp/drakter-agente-hermes/hv/venv`, fuera del repo).
- **Alternativas descartadas:** escribir `DRAKTER_MODEL_PROVIDER` en `~/.config/drakter/.env` (es del usuario y guarda secretos).
- **Impacto:** `scripts/dev.sh`, `scripts/drakter-local.sh`, `desktop/electron/main/backendProcess.ts`.

## [2026-11-13] Rutas permitidas de Electron regeneradas desde el contrato
- **Contexto:** `routes.generated.ts` no tenía `GET /api/v1/today` (Hoy mostraba "no conectado") y aún listaba `/api/v1/system/backups`.
- **Decisión:** regenerarlo con `electron/scripts/generate-routes.mjs` desde `contracts/api/routes.md`, sin editarlo a mano.
- **Impacto:** `desktop/electron/shared/routes.generated.ts`.

## [2026-11-13] Clave de Anthropic inválida: pruebas con el stub
- **Contexto:** la `ANTHROPIC_API_KEY` de `~/.config/drakter/.env` recibe 401 `invalid x-api-key`, también en una llamada directa a `GET /v1/models`.
- **Decisión:** la app se deja arrancada con `tools/dev-llm-stub`. Nada de lo marcado demuestra el comportamiento de Claude Haiku 5.5.
- **Impacto:** Checklist 3 y 13 de `IMPLEMENTATION_STATUS.md`.
- **Estado (2026-11-13, más tarde):** hay clave válida. La app del usuario se arranca con el modelo real (`scripts/drakter-local.sh start anthropic`) y las casillas ⚠️ «sin clave» se recomprueban con él; el stub queda para pruebas sin coste.

## [2026-11-13] Cierre de backend base: seguridad sin cablear en el arranque
- **Contexto:** al cerrar las Checklists 0/2/6, `app/permissions/setup.py` (confirmaciones y permisos del agente) no se invoca desde `app/main.py`. Cablearlo tal y como indica `permissions/README.md` rompe el arranque porque `load_confirmed_executors` espera `habits_calendar_support.CONFIRMED_ACTIONS`, que no existe.
- **Decisión:** no se cablea desde el módulo backend-base. Se marca «Crear sistema de permisos» con ⚠️ (guardia de red y roles operativos, confirmaciones no) y se traslada al integrador la reconciliación seguridad↔hábitos/calendario y el adaptador `ConfirmationGate` de tareas.
- **Alternativas descartadas:** cablear con `try/except` para tolerar el fallo (dejaría las confirmaciones a medias sin avisar); implementar el adaptador de tareas desde este módulo (fuera de zona y de alcance).
- **Motivo:** el arreglo cruza tres módulos y un archivo compartido. Hacerlo a medias ocultaría un fallo en una zona de seguridad.
- **Impacto:** `backend/app/main.py`, `backend/app/permissions/setup.py`, `backend/app/services/habits_calendar_support.py`/`calendar_actions.py`, `backend/app/services/tasks_ports.py`; Checklists 2 (permisos), 7 (borrado con confirmación) y 16; e2e `confirmacion.destructiva`.

## [2026-11-13] Clasificación de memoria: los hábitos van antes que el perfil
- **Contexto:** el clasificador por reglas evaluaba primero el perfil, y "Siempre estudio por la noche" (contiene "estudio") acababa como memoria semántica de perfil en vez de procedimental.
- **Decisión:** los marcadores de hábito (siempre, suelo, cada día…, always, usually…) se evalúan antes que perfil y preferencias.
- **Alternativas descartadas:** quitar "estudio"/"trabajo en" del perfil (perdería "Estudio Física", que sí es perfil).
- **Motivo:** que la memoria procedimental se alimente desde la conversación.
- **Impacto:** `backend/app/integrations/memory/pipeline/classify.py`, Checklist 12.

## [2026-11-13] Memoria v1: recuperación al turno y olvido sin conectar al cierre
- **Estado:** SUPERADA el mismo día (drakter-42): la recuperación al turno se conectó (`df258b1`) y el olvido y la aprobación desde la GUI pasan por confirmación (`effda18`, `6270011`). Se conserva como historia.
- **Contexto:** en el cierre se comprobó que `memories_for_context` + `build_context` no los llama el runner de Hermes, y que olvidar usa `DenyAllGate` (GUI) y `DefaultToolGate` (agente).
- **Decisión:** se cierra la v1 con la memoria accesible al agente solo por herramientas (`search_memory`, `get_memory_item`) y con el olvido fallando cerrado. Quedan con ⚠️ "recuperación selectiva", "límites de contexto" y "memoria de trabajo".
- **Alternativas descartadas:** conectarlo en el cierre (integración nueva en `app/integrations/hermes/` y en el flujo de confirmaciones, fuera del alcance de cierre).
- **Motivo:** el protocolo de cierre solo termina lo empezado.
- **Impacto:** Checklist 12; siguiente paso: llamar a `build_context` en el runner y enchufar `memory.forget` a `app/services/actions.py`.
- **Estado (2026-11-13, más tarde):** la recuperación al turno ya está conectada (ver «Contexto de cada turno de Hermes por build_context») y, con `effda18` y `6270011`, olvidar y aprobar recuerdos desde la GUI responden 409 y se ejecutan en `/confirmations/{id}/approve` (acciones `forget_memory_gui` y `approve_memory_gui`, con el hash del recuerdo como objetivo); `confirmation_id` en el cuerpo ya no tiene efecto.

## [2026-11-13] Caducidad única de confirmaciones: 300 s
- **Contexto:** convivían tres plazos de confirmación: `ActionService` 300 s (`backend/app/services/actions.py`), `habits_calendar_support` 15 min y `storage_ports` 600 s («propuesto»). `contracts/README.md` §5 pide un único camino de confirmación.
- **Decisión:** un único camino de confirmación, `ActionService` de `services/actions.py` con `CONFIRMATION_TTL_SECONDS = 300`, según `contracts/README.md` §5 y `backend/app/permissions/README.md`. Lo autorizó `drakter-1`.
- **Alternativas descartadas:** mantener un plazo propio por módulo (contradice el contrato y deja tres flujos de confirmación que auditar).
- **Motivo:** una sola frontera de confirmación, con un plazo corto y coherente para las acciones destructivas.
- **Impacto:** `backend/app/services/habits_calendar_support.py`, `backend/app/services/storage_ports.py`, cableado de seguridad en `backend/app/main.py` (drakter-34); Checklists 8, 9, 10 y 16. Resuelve el desajuste anotado en la entrada «Almacén en v1» (2026-11-04).

## [2026-11-13] get_related_items devuelve contenido no confiable
- **Contexto:** `get_related_items` devuelve títulos de entidades, entre ellos títulos de recursos del almacén (documentos importados). El código declaraba `returns_untrusted=True` y el catálogo `contracts/tools/catalog.json` decía `false`, lo que provocaba el aviso `tool_catalog_drift` al arrancar.
- **Decisión:** mantener `returns_untrusted=True` y alinear el catálogo a `true`.
- **Alternativas descartadas:** bajar el código a `false`. Se descarta porque los títulos de documentos del almacén son datos no confiables (CLAUDE.md §8) y deben marcar la sesión.
- **Motivo:** seguridad. Lo que viene del almacén no puede tratarse como instrucción.
- **Impacto:** `contracts/tools/catalog.json` (entrada get_related_items), Checklist 11 «Crear herramientas Hermes».

## [2026-11-13] SOUL.md compone los 14 archivos desde sus tres carpetas
- **Contexto:** la entrada "Identidad repartida en identity/, context/ y knowledge/" revocó la de los 14 archivos en agent/identity/, pero `render_soul` (backend/app/integrations/hermes/home.py) y `agent/evals/harness.py` seguían buscándolos todos en identity/. Los 8 de knowledge/ y context/ no llegaban al prompt de Hermes, y los evals abortaban.
- **Decisión:** `_IDENTITY_ORDER` pasa a ser una lista de pares (carpeta, archivo) con el mismo orden de antes: seguridad → identity → knowledge → context. Un archivo de identity/ con alguno de los 14 nombres se ignora; otros .md de identity/ se siguen añadiendo al final. El arnés de evals usa las mismas rutas.
- **Alternativas descartadas:** volver a juntar los 14 en identity/ (contradice la entrada vigente y `rules.py`); componer el SOUL con `build_context` (mezcla la carga estática del home con el armado de cada turno).
- **Motivo:** que el prompt real lleve lo que dice la decisión vigente, sin tocar el texto de la identidad.
- **Impacto:** Checklist 4 (carga de contexto). SOUL.md pasa de 21.922 a 46.227 caracteres, por debajo de `context_file_max_chars` = 120.000. La cifra de 20.000 caracteres que citan las entradas del 2026-11-04 ya no aplica: el tope configurado es `SOUL_MAX_CHARS`.

## [2026-11-13] Esquema de automejora: manda el del servicio (migración 0013)
- **Contexto:** la migración 0010 y `contracts/.../improvement.py` definían unas tablas `improvement_*` que ningún código usa. Los servicios de automejora se escribieron contra `backend/app/schemas/ddl_improvement.sql`, que nunca pasó a una migración, de modo que sobre una BD real todo el ciclo fallaba.
- **Decisión:** `0013_improvement_cycle.sql` (renumerada desde 0012 por la colisión con `0012_confirmation_hardening.sql`) borra las tablas de 0010 (vacías) y crea el esquema del servicio, con CHECK/FK/UNIQUE con nombre y triggers de inmutabilidad (propuestas inmutables, evaluaciones e historial de solo añadir). Las rutas se montan con `backend/app/api/improvement.py`.
- **Alternativas descartadas:** adaptar los servicios al esquema de 0010 (pierde el historial `improvement_events`, el parche, el digest de aprobación y los triggers de seguridad); tablas con otro nombre (dos esquemas vivos).
- **Motivo:** el esquema del servicio es el único con código, y garantiza en la BD que nada cambia sin aprobación.
- **Impacto:** `backend/migrations/0013_improvement_cycle.sql`, `check_migrations.py`, `backend/app/api/improvement.py`. `contracts/python/drakter_contracts/models/improvement.py` y `contracts/ts` quedan desalineados (categorías y estados distintos): hay que actualizarlos o marcarlos como obsoletos. Checklist 15.

## [2026-11-13] Checklist 5 cerrada con el personaje provisional SVG
- **Contexto:** el cierre verifica el personaje provisional (`desktop/src/character/`). El `.riv` sigue sin entregarse.
- **Decisión:** se marcan las casillas de diseño, los 9 estados, las transiciones, el sistema de eventos visuales y la prueba de animaciones como hechas en el provisional SVG, con nota de que la versión `.riv` sigue pendiente. Quedan ⚠️ «Crear proyecto Rive», «Integrar Rive con React» (plug listo, sin runtime ni `.riv`) e «Implementar sincronización labial» (solo generador procedural; `setMouth` sin audio).
- **Alternativas descartadas:** dejar todo sin marcar hasta tener el `.riv`, que ocultaría el trabajo ya hecho y verificado. Marcar también Rive y la sincronización labial, que no funcionan.
- **Motivo:** CLAUDE.md §2 (riesgo Rive) y DECISIONS [2026-11-04]: el provisional tiene la misma API de estados y el `.riv` se enchufa cambiando una línea de `plug.ts`.
- **Impacto:** `IMPLEMENTATION_STATUS.md` Checklist 5. Sin cambios de código.

## [2026-11-13] Evals: identidad y esquemas leídos del árbol integrado
- **Contexto:** tras la integración, los archivos de identidad están repartidos en `agent/identity/`, `agent/knowledge/` y `agent/context/`, y varias herramientas cambiaron de argumentos (`delete_*` exige `expected_revision`); el arnés de evals salía BLOQUEADO.
- **Decisión:** el arnés busca cada archivo de `IDENTITY_ORDER` en esas tres carpetas, en el mismo orden; `tool_inputs.json` se regenera desde `drakter/integracion` con el mismo `args_model.model_json_schema()` que usa `mcp_bridge.py`, y se ajustan los escenarios.
- **Alternativas descartadas:** reescribir `extract_schemas.py` para el árbol único (no era necesario para cerrar; se reutilizaron sus funciones); mover archivos de identidad (zona de otro módulo y prohibido tocar identidad).
- **Motivo:** que el arnés corra contra el código real integrado sin cambiar su contrato.
- **Impacto:** `agent/evals/`; casillas de prueba de modelo de CL3, CL4 y CL13 siguen ⚠️ sin clave.

## [2026-11-13] Cierre del desajuste de caducidad de confirmaciones (hábitos/calendario)
- **Contexto:** DECISIONS registraba un ⚠️: `habits_calendar_support.py` tenía su propia caducidad de 15 min frente a los 300 s de `ActionService`.
- **Decisión:** se da por cerrado. Desde a123a90 todos los borrados de hábitos, calendario y asignaturas pasan por `run_confirmable` → `ActionService` (300 s), con sus `ActionSpec` en `services/calendar_actions.py`. Se retira el bucle heredado `CONFIRMED_ACTIONS` de `permissions/setup.py`.
- **Alternativas descartadas:** restaurar `CONFIRMED_ACTIONS` vacío en `habits_calendar_support.py` como compatibilidad (mantendría un segundo camino muerto).
- **Motivo:** contracts/README.md §5 pide un único camino de confirmación.
- **Comprobado (drakter-38, sobre `612d8e4` con la seguridad cableada):** en la app real, DELETE de evento o asignatura → 409 con `expires_at` a +300 s; el token `ui` no aprueba; un hash distinto se rechaza; aprobar borra y rechazar conserva.
- **Impacto:** backend/app/permissions/setup.py, backend/app/main.py (instalar la seguridad al arrancar), Checklist 8/9.

## [2026-11-13] Confirmaciones de tareas y proyectos sobre pending_confirmations
- **Contexto:** los servicios de tareas y proyectos piden confirmación a través de `tasks_ports.ConfirmationGate`, pero nadie instalaba una puerta real: `FailClosedGate` daba 503 en todo DELETE. Además `main.py` no montaba `install_security`.
- **Decisión:** `services/tasks_confirmations.py` registra cada operación de `TASK_CONFIRMABLE`/`PROJECT_CONFIRMABLE` como `ActionSpec` (riesgo confirm, `external=True`, prefijo `workspace_`) y `ActionServiceGate` pide la confirmación con `ActionService.execute_or_request`, único camino (TTL 300 s). Los `targets` y `affected_count` que resuelve el servicio viajan en los argumentos firmados; al aprobar, el servicio abre su transacción y vuelve a comprobar alcance y revisiones. `main.py` deja `app.state.workspace_ports = build_ports(actions)`.
- **Alternativas descartadas:** insertar la fila en `pending_confirmations` desde el módulo, como hace almacén (segundo camino paralelo a `ActionService`); usar los nombres sin prefijo (chocarían con las herramientas del agente `delete_task`, `update_task` y `complete_task`, que ejecuta el registro).
- **Motivo:** reutiliza las reglas de dominio y la comprobación de revisiones del servicio sin tocar el contrato de confirmaciones.
- **Impacto:** `backend/app/services/tasks_confirmations.py`, `backend/app/main.py` (cableado de `drakter-34`); Checklist 7 (eliminar tareas, borrar proyectos).
- **Estado:** descartada el mismo día; ver «Seguridad cableada en el arranque». `tasks_confirmations.py` (`8ff52da`/`db85f3e`) no se fusiona.

## [2026-11-13] Voz: cierre mínimo, rediseño posterior sobre Pipecat
- **Contexto:** la capa de voz de v1 (`voice/`: openWakeWord, Silero VAD, Faster-Whisper, Kokoro/Piper, Voice Manager) llega al cierre sin probar de punta a punta. `drakter-1` indica que la capa de voz y conversación se rediseñará sobre Pipecat, con STT Whisper y TTS Fish Audio.
- **Decisión:** en v1 `voice/` solo se estabiliza y se documenta. Las casillas de la Checklist 14 no verificadas quedan con ⚠️ «rediseño previsto sobre Pipecat». El rediseño se planifica aparte, fuera de este cierre.
- **Alternativas descartadas:** terminar y verificar ahora toda la tubería actual (trabajo que el rediseño sustituiría); retirar `voice/` de v1 (se perdería lo que ya funciona hasta tener el nuevo diseño).
- **Motivo:** indicación de `drakter-1`; no invertir en una tubería que se va a sustituir.
- **Impacto:** `voice/`, Checklist 14, `MASTER_PLAN` (parte de voz) y `ROADMAP` (fase de voz), que se actualizarán cuando se planifique el rediseño; el módulo de voz del escritorio y la sincronización labial (CL5).

## [2026-11-13] Skills de agent/ inertes en Hermes
- **Contexto:** el toolset `skills` de Hermes v0.22.7 incluye `skill_manage`, con el que el agente podría escribir sus propias Skills e instrucciones (H-06/F14).
- **Decisión:** `home.py` desactiva el toolset `skills`; las Skills de `agent/skills/` existen como fuente y documentación, pero Hermes no las carga. El modelo se guía por la descripción y el esquema de cada herramienta MCP `mcp__drakter__*`.
- **Alternativas descartadas:** activar `skills` con `skill_manage` (persistencia de instrucciones controlada por el modelo, contraria a CLAUDE.md §8).
- **Motivo:** la automejora nunca modifica instrucciones sin autorización.
- **Impacto:** Checklists 3 ("Crear primera Skill") y 13 (Skills por dominio) quedan con ⚠️ hasta poder bloquear `skill_manage` por separado.

## [2026-11-13] El agente recibe storage.write
- **Contexto:** `agent/configuration/permissions.json` no concedía `storage.write`, y la política denegaba `create_resource`, `update_resource_metadata`, `index_resource` y `refresh_resource_index`, que el contrato de almacén define como herramientas del agente.
- **Decisión:** se añade `storage.write`. Las acciones de riesgo `confirm` siguen pasando por la confirmación de la GUI.
- **Alternativas descartadas:** dejar las cuatro herramientas inaccesibles (contradice el contrato y la Skill de almacén).
- **Motivo:** completar la configuración ya diseñada.
- **Impacto:** `agent/configuration/permissions.json`, Checklist 13.

## [2026-11-13] Pruebas del agente sin clave con guiones MCP de Drakter
- **Contexto:** los guiones del stub usaban herramientas nativas de Hermes (`read_file`, `terminal`) que Drakter nunca ofrece al modelo.
- **Decisión:** las pruebas de herramienta permitida, cadena y acción destructiva usan herramientas `drakter__*`, y el arnés espera a `agent/status = idle` antes del primer turno.
- **Alternativas descartadas:** reactivar toolsets nativos para la prueba (rompería la lista blanca que se quiere comprobar).
- **Motivo:** probar el cableado real del producto.
- **Impacto:** `tests/e2e/`, `tools/dev-llm-stub/scenarios/` (pendiente: lo hace drakter-32).

## [2026-11-13] Seguridad cableada en el arranque
- **Contexto:** al cerrar las Checklists 0/2/6, `app/permissions/setup.py` (confirmaciones y permisos del agente) no se invocaba desde `app/main.py`, y cablearlo tal cual rompía el arranque porque `load_confirmed_executors` esperaba `habits_calendar_support.CONFIRMED_ACTIONS`, que ya no existe. Resultado: `/api/v1/confirmations/**` y los borrados de tareas, proyectos, calendario y asignaturas daban 503 `confirmation_unavailable`. Tareas proponía además su propia puerta (`services/tasks_confirmations.py`, `8ff52da`/`db85f3e`).
- **Decisión:** `drakter-34` cablea la seguridad (`4d2bcd1`). `permissions/wiring.py` aporta `PendingConfirmationGate` para tareas y proyectos, los ejecutores de `TASK_CONFIRMABLE`/`PROJECT_CONFIRMABLE`, las `ActionSpec` de calendario y `wire_security()`; `main.py` llama a `wire_security` en `_install_services` y a `start_security`/`stop_security` en `lifespan`. `load_confirmed_executors` ya no falla sin `CONFIRMED_ACTIONS`. La migración `0012_confirmation_hardening.sql` congela la identidad de las confirmaciones (las filas nacen `pending` y las cerradas no cambian). Se descarta la puerta propia de tareas para no tener un segundo camino de confirmación.
- **Alternativas descartadas:** fusionar `tasks_confirmations.py` (segundo camino paralelo al de seguridad); cablear con `try/except` para tolerar el fallo (dejaría las confirmaciones a medias sin avisar).
- **Motivo:** un único camino de confirmación (`contracts/README.md` §5), con caducidad de 300 s.
- **Comprobado:** `check_security.py` 145/145, `check_confirmations.py` 0 fallos, borrado de tareas y proyectos 409 → aprobar → 404.
- **Impacto:** `backend/app/main.py`, `backend/app/permissions/wiring.py`, `setup.py`, `tool_gate.py`, `backend/app/services/actions.py`, `backend/migrations/0012_confirmation_hardening.sql`; Checklists 2 (sistema de permisos), 7 (eliminar tareas, borrar proyectos), 9 y 16. La migración de automejora se renumeró a `0013_improvement_cycle.sql`.

## [2026-11-13] Permisos de automejora para el agente: lectura libre, escritura siempre con confirmación
- **Contexto:** el informe de Hermes (drakter-36) vio que `agent/configuration/permissions.json` no concedía `improvement.read` ni `improvement.write`, así que las 4 herramientas de automejora quedaban denegadas al agente.
- **Decisión:** se conceden `improvement.read` e `improvement.write`, y las dos herramientas de escritura (`record_improvement_feedback`, `create_improvement_proposal`) pasan de `RiskClass.WRITE` a `RiskClass.CONFIRM`: toda escritura del agente pasa por confirmación en `ActionService`. El agente sigue sin herramientas para evaluar, aprobar, aplicar o revertir (solo GUI, `require_user`); sus escrituras solo insertan feedback o un borrador en SQLite y nunca tocan producción, permisos, confirmaciones ni auditoría.
- **Alternativas descartadas:** dejar las escrituras en `WRITE` sin confirmar (solo pedirían confirmación en sesiones `tainted`).
- **Motivo:** CLAUDE.md §8: la automejora no cambia nada sin autorización.
- **Comprobado:** con el motor real (`tool_action_spec` + `ActionService` + `permissions.json`), las lecturas dan ALLOW; cada escritura da CONFIRM y deja la fila en `pending_confirmations` sin escribir; al aprobar con `approver` se ejecuta; sin el permiso, DENY.
- **⚠️ En ejecución:** el runtime de Hermes usa `DefaultToolGate`, que deniega CONFIRM: hoy las escrituras del agente quedan denegadas (falla cerrado) hasta que el runtime use `BackendToolGate` (pendiente de drakter-34).
- **Impacto:** `agent/configuration/permissions.json`, `backend/app/tools/improvement.py` (`5dd55b1`); Checklists 13 (permisos, confirmaciones) y 15.

## [2026-11-13] Cierre del almacén: arreglos de integración
- **Contexto:** al integrar `drakter/integracion`, el almacén no funcionaba: `Settings` ya no tiene `runtime_dir`, `untrusted_envelope` se movió a `app.tools.envelope`, el registro de herramientas rechaza claves de `audit` que no son argumentos y `uv.lock` no incluía pypdf.
- **Decisión:** `denied_roots` usa `runtime_dir` solo si existe; los ejecutores confirmados del almacén fijan `sqlite3.Row` en la conexión del pipeline; el plazo de confirmación del almacén es el único de `services/actions.py` (300 s), lo que resuelve el desajuste de «Almacén en v1»; `tools/storage.py` importa de `envelope` y filtra `audit` por los campos de cada `args_model`; se regenera `uv.lock` con pypdf; el agente necesita `storage.write` para crear notas (DECISIONS «Almacén en v1»).
- **Alternativas descartadas:** añadir `runtime_dir` a `Settings` (es un archivo compartido y nadie más lo usa); quitar la validación de `audit` del registro (es un control de seguridad).
- **Motivo:** dejar el almacén operativo sin tocar contratos compartidos.
- **Comprobado:** `check_storage_paths.py` 127/127, `check_storage_archives.py` 35/35, `check_storage_catalog.py` y `check_storage_api.py` OK, flujo REST de extremo a extremo sobre la app real sin parches 27/27, con confirmaciones aprobadas (rutas denegadas, symlinks fuera de la raíz, SSRF, límites de comprimidos).
- **Impacto:** `backend/app/services/storage_ports.py`, `backend/app/tools/storage.py`, `backend/app/services/storage_confirmed.py` (`0eaab3b`), `backend/uv.lock`, `agent/configuration/permissions.json`, `desktop/src/modules/storage/StoragePage.tsx` (`2fe7cc6`), Checklist 10.

## [2026-11-13] Prefijo workspace_ en las confirmaciones de los servicios de tareas y proyectos
- **Contexto:** `wiring.py` registraba los ejecutores de `TASK_CONFIRMABLE`/`PROJECT_CONFIRMABLE` con los nombres `delete_task`, `update_task` y `complete_task`, que también son herramientas del agente. `ActionService.approve` prefiere los ejecutores al registro, así que un `delete_task` del agente aprobado nunca llegaba a borrar.
- **Decisión:** las filas de `PendingConfirmationGate` y las claves de los ejecutores de servicio llevan el prefijo `workspace_` (`workspace_delete_task`, `workspace_delete_project`, …). Las herramientas del agente siguen con sus nombres y las ejecuta el registro.
- **Alternativas descartadas:** renombrar las herramientas del agente (rompe el catálogo y la lista blanca); una puerta propia del módulo (segundo camino paralelo a `ActionService`).
- **Motivo:** un nombre identifica una sola acción en `pending_confirmations`.
- **Impacto:** `backend/app/permissions/wiring.py` (`b531106`); Checklist 7 (eliminar tareas, herramientas Hermes).

## [2026-11-13] Fecha-hora local sin segundos
- **Contexto:** `contracts/README.md` §2 y `drakter_contracts.common.LocalDateTime` exigían `YYYY-MM-DDTHH:MM:SS`. El calendario (esquemas, herramientas del agente, `HABITS_CALENDAR_CONTRACT.md`, `occurrence_id`) y el desktop (`localIso`) usan `YYYY-MM-DDTHH:MM`, y la API rechaza los segundos con 422.
- **Decisión:** el contrato pasa a `YYYY-MM-DDTHH:MM`.
- **Alternativas descartadas:** cambiar el calendario a segundos (toca datos guardados, `occurrence_id`, herramientas y GUI sin ganar nada).
- **Motivo:** el código construido y consumido es coherente entre sí; el desfasado era el contrato.
- **Impacto:** `contracts/README.md` §2, `contracts/python/drakter_contracts/common.py`; `contracts/ts` no cambia.

## [2026-11-13] routes.md refleja lo montado en drakter/integracion
- **Contexto:** la columna Estado de `contracts/api/routes.md` y su sección de desviaciones describían ramas anteriores a la integración (routers sin montar, `/ws`, tareas sin router…). Además faltaban 12 rutas de automejora ya montadas.
- **Decisión:** el Estado se calcula contra la app real (`construida`, `escrita, sin montar`, `(sin construir)`); las desviaciones solo recogen lo que sigue abierto; se documentan las 17 rutas de automejora.
- **Alternativas descartadas:** mantener el estado por frente (inservible tras integrar).
- **Motivo:** que el contrato sea la fuente fiable de lo que existe.
- **Comprobado:** 175 pares método+ruta de la app real frente a `routes.md`: 0 rutas en código sin contrato y 0 filas «construida» sin código; `gen_ts.py` regenera `contracts/ts/index.ts` idéntico.
- **Impacto:** `contracts/api/routes.md` (`dda565b`, `b31d1e8`, `6ba869a`); al regenerar `desktop/electron/shared/routes.generated.ts` entran 12 rutas de automejora, incluidas `apply` y `revert` (decisión de desktop/integrador).

## [2026-11-13] Contexto de cada turno de Hermes por build_context
- **Contexto:** `build_context` (recuperación, límites, cercado) existía, pero el provider de Hermes enviaba el texto crudo del usuario y solo las instrucciones de seguridad. Los niveles 2 y 4 no llegaban al modelo.
- **Decisión:** antes de cada turno, el backend recupera memorias (`memories_for_context`) y llama a `build_context`. `turn_prompt` es la entrada del turno, con la memoria cercada como `untrusted_data`. Las instrucciones efímeras son `safety_instructions.md` + niveles 1, 2 y 4, y la identidad sigue en `SOUL.md`. La conversación la guarda la sesión de Hermes (`conversation=()`). Un turno con memoria marca la sesión como `tainted`.
- **Alternativas descartadas:** meter la memoria en el prompt de sistema (Hermes la trataría como autoritativa durante toda la sesión); repetir el historial en `build_context` (duplicaría lo que ya guarda Hermes).
- **Motivo:** aplicar "El backend recupera los recuerdos" y la prioridad de CLAUDE.md §8.
- **Efecto conocido:** tras un turno con memoria la sesión queda `tainted` y las escrituras del agente escalan a `confirm`; mientras el runtime use `DefaultToolGate`, fallan cerradas (`confirmation_unavailable`).
- **Impacto:** `backend/app/integrations/hermes/hermes_provider.py`, `runtime.py` (`df258b1`), Checklist 12 (recuperación selectiva, límites de contexto, memoria de trabajo).

## [2026-11-13] Cierre de CL4: consistencia OK, estilo al rediseño
- **Contexto:** con Claude Haiku 5.5 real, drakter-45 dio por buena «Probar consistencia de personalidad» (2 casos, 0 hallazgos, lectura humana conforme) y drakter-51 la dejó con ⚠️: el modelo a veces supera `max_sentences` (4 frases para máx. 3), abre dos veces con la muletilla «Mal asunto a medias:» y las rúbricas de `agent/evals` (`report.md`) no tienen lectura humana.
- **Decisión (drakter-33):** la casilla queda `[x]` sin ⚠️, con una nota informativa. Los dos finalizadores verificaron que la personalidad es mecánicamente consistente (2 casos × 2 sesiones, respuestas estables), que es el criterio de CLAUDE.md §4. Los matices de estilo y la lectura humana de las rúbricas se tratan en el rediseño de personalidad, que se planifica aparte con el usuario.
- **Alternativas descartadas:** dejar la casilla en `[ ]` hasta ajustar el estilo (exigiría tocar los textos de identidad, fuera del alcance del cierre).
- **Motivo:** la consistencia está comprobada; ajustar el estilo es trabajo de personalidad, no de cierre.
- **Impacto:** `IMPLEMENTATION_STATUS.md` Checklist 4. Sin cambios en `agent/identity/`.

## [2026-11-13] Cierre de la voz propia: verificada y congelada a la espera de Pipecat
- **Contexto:** cierre del proyecto. El pipeline propio (`voice/`: Silero VAD, Faster-Whisper, Kokoro, Piper de respaldo, Voice Manager e IPC por socket Unix) y el puente del backend (`backend/app/integrations/voice/`) están escritos, pero el puente no está registrado en `main.py` y el desktop no tiene cliente de voz. drakter-1 ha decidido rediseñar la voz sobre Pipecat (STT Whisper, TTS Fish Audio).
- **Decisión:** el pipeline propio se deja verificado y sin ampliar: arranca como proceso aislado, cumple su contrato IPC y mide latencia (`bench_engines.py`, `voice.metrics`). No se registra en `main.py`, no se instalan Piper ni openWakeWord y no se toca la GUI. Whisper `small` se mantiene por defecto porque, medido en esta máquina, `medium` es ~4× más lento y usa más del doble de RAM.
- **Alternativas descartadas:** conectarlo ya a `main.py`, el agente y el desktop (es funcionalidad nueva y se perdería con el cambio a Pipecat); usar Whisper `medium` por defecto (inviable en esta CPU).
- **Motivo:** cerrar sin ampliar lo que se va a sustituir y sin dejar nada roto.
- **Comprobado:** `python -m voice` arranca y responde al contrato IPC (`status`, `speak`, `interrupt`, `listen.cancel`); `voice/tests/check_pipeline.py` 12/12; transcripción real con Whisper small correcta.
- **Impacto:** Checklist 14 (13 casillas verificadas; ⚠️ en wake word, Piper, sincronizar boca y conversación completa). Checklist 17 «Medir latencia de STT/TTS»: el método está listo, pero hay que repetir la medición con la máquina en reposo.

## [2026-11-13] Una sola ruta de búsqueda global
- **Contexto:** `app/api/relations_tags.py` (rama almacén-relaciones) y `app/api/search.py` (rama búsqueda) declaraban ambos `GET /api/v1/search`. El descubrimiento de routers monta por orden alfabético, así que ganaba el de relaciones, que no llama a `reconcile_structured`: tareas, proyectos, hábitos, eventos y asignaturas nunca llegaban al índice.
- **Decisión:** se elimina la ruta de `relations_tags.py`. La búsqueda global es `app/api/search.py` + `services/search.py` (`search_global`), coherente con la entrada "Búsqueda con reconcile_structured".
- **Alternativas descartadas:** añadir la reconciliación a `storage_search_all` (dos implementaciones del mismo contrato; su extracto con `[ ]` no encaja con `SearchHitOut` que espera el desktop).
- **Motivo:** un único punto de entrada y de escritura del índice.
- **Comprobado:** con la app real, 33/33 (búsqueda por prefijo de los 5 tipos, `content_trust=untrusted`, sintaxis FTS hostil → 200, cursor sin solapes, archivados excluidos).
- **Impacto:** `backend/app/api/relations_tags.py` (`7787e9b`); `backend/app/services/storage_search_all.py` queda sin uso; CL 10 «Implementar búsqueda».

## [2026-11-13] Aprobación y reversión de automejora por ActionService
- **Contexto:** automejora aprobaba y revertía con su propio `ConfirmationGate` (`app.state.confirmation_gate`), que nadie asignaba: `approval-request` y `revert-request` daban 503/403 y contradecían el camino único de confirmación (`contracts/README.md` §5, «Caducidad única de confirmaciones: 300 s»). Además nadie declaraba el principal de la GUI.
- **Decisión:** dos acciones CONFIRM `external` en `backend/app/services/improvement_actions.py`, `approve_improvement_proposal` (permiso `improvement.approve`) y `revert_improvement_proposal` (`improvement.revert`), con argumentos `{proposal_id, digest}`; el `content_hash` es el estado más el digest, así que un cambio entre petición y aprobación da `conflict`. `approval-request` y `revert-request` responden 409 con el ticket y el approver decide en `/api/v1/confirmations/{id}/approve|reject`. Se eliminan las rutas propias `/approve` y `/revert` y el `ConfirmationGate` de automejora. `wiring.py` registra las dos acciones y declara `app.state.gui_principal = user/desktop`.
- **Alternativas descartadas:** mantener la puerta propia de automejora (segundo camino de confirmación).
- **Motivo:** un único camino de confirmación con 300 s y auditoría.
- **Comprobado:** por HTTP con el guardia real: 409 con ticket, el token `ui` no aprueba (403), el approver aprueba → `approved`, confirmación de un solo uso, aplicar publica la rama, revertir borra la rama, cambio intermedio → 409 `conflict`, TTL 300 s, aprobación en `audit_events`, el agente recibe DENY.
- **Impacto:** `backend/app/services/improvement_actions.py`, `backend/app/api/improvement.py` (`2425da5`), `backend/app/permissions/wiring.py` (`b1a49a3`); Checklist 15 «Crear flujo de aprobación». `desktop/electron/shared/routes.generated.ts` debe regenerarse (lista `/approve`, no lista `approval-request` ni `revert-request`).

## [2026-11-13] Calendario: fecha-hora local con segundos opcionales
- **Contexto:** `drakter_contracts.common.LocalDateTime` y el catálogo e2e usaban `AAAA-MM-DDTHH:MM:SS`; `backend/app/schemas/calendar.py` y `HABITS_CALENDAR_CONTRACT.md` usan `AAAA-MM-DDTHH:MM`, que es lo que envía el escritorio. `POST /calendar/events` respondía 422 a los clientes del contrato compartido.
- **Decisión:** el esquema del calendario acepta `:00` final y lo recorta; se sigue guardando y devolviendo `HH:MM`. Otros segundos se rechazan.
- **Alternativas descartadas:** cambiar el escritorio y la base a segundos (migración y cambios en `occurrence_id` sin beneficio); cambiar `contracts/` desde el módulo de calendario (zona compartida).
- **Motivo:** compatibilidad con ambos formatos sin tocar datos.
- **Relación:** complementa «Fecha-hora local sin segundos», que alinea el contrato a `HH:MM`; la tolerancia a `:00` queda para clientes antiguos.
- **Impacto:** `backend/app/schemas/calendar.py` (`f16753f`); Checklist 9.

## [2026-11-13] Recursos de una asignatura vía relaciones, sin títulos
- **Contexto:** `get_subject_resources` era un stub vacío «hasta que exista el módulo de relaciones», que ya existe. El catálogo declara la herramienta con `returns_untrusted: false`, y los títulos de recursos son datos no confiables en el almacén.
- **Decisión:** se leen las filas de `relationships` asignatura↔recurso en ambos sentidos y se devuelven solo `resource_id`, `resource_type`, `availability_status`, `relationship_type` y `direction`. El detalle se obtiene con `get_resource`.
- **Alternativas descartadas:** devolver títulos y marcar la herramienta como no confiable (cambia el catálogo compartido); dejar el stub.
- **Motivo:** cerrar la casilla «Asociar recursos» sin cambiar el contrato ni meter texto no confiable en un resultado marcado como confiable.
- **Impacto:** `backend/app/services/subjects.py`, `backend/app/tools/subjects.py` (`bbee4c4`); Checklist 9.

## [2026-11-13] Paginación por offset en memoria, chat y automejora: desviación aceptada en v1
- **Contexto:** `contracts/README.md` §2 y `contracts/api/routes.md` piden `{items, next_cursor, total?}` con `limit`/`cursor`. Tres frentes paginan con `limit`/`offset`: memoria (`backend/app/integrations/memory/router.py`), chat (`backend/app/api/chat.py`, sesiones y mensajes) y automejora (`backend/app/services/improvement_api.py`: `feedback`, `proposals`, `changelog`).
- **Decisión:** no se refactorizan en v1. Se documentan como desviación aceptada en `routes.md` (convención de listados y sección «Paginación por `offset`»). El cliente usa `offset` en esos listados; el resto sigue con cursor.
- **Alternativas descartadas:** migrar ahora los tres a cursor. Toca servicios, GUI y herramientas al cierre, sin un fallo que lo justifique.
- **Motivo:** decisión de cierre del coordinador (drakter-33). Con los volúmenes de v1 funciona.
- **Impacto:** `contracts/api/routes.md`. Queda pendiente para después de v1.

## [2026-11-13] Modelos del contrato alineados con la API real
- **Contexto:** `contracts/python/drakter_contracts/models` (y `contracts/ts`, generado) describían campos que la API no devuelve ni acepta. Por ejemplo: `target_note` frente a `goal_note` en hábitos, `metadata` en entidades que no lo exponen, `location_id`/`relative_path` en carpetas, y la memoria con el origen plano frente a `provenance`.
- **Decisión:** el contrato se alinea con la API construida. Se añade la base `EntityCoreOut` sin `metadata`, y `EntityOut` la extiende para tareas y proyectos. Cambian hábitos (`goal_note`), proyectos (`objective`), asignaturas, sesiones, carpetas, recursos, eventos, bloques, etiquetas (`usage_count`), relaciones (`limit`/`cursor`), chat (`ChatSession.status`; `MessageOut` sin `client_message_id`) y memoria (`provenance`, alta/parche/búsqueda con los campos reales). `contracts/ts` se regenera; el `typecheck` del desktop pasa.
- **Alternativas descartadas:** cambiar la API para ajustarla al contrato antiguo. Rompería la GUI y las herramientas, que ya consumen la API.
- **Motivo:** decisión de cierre del coordinador (drakter-33). Lo construido y consumido manda.
- **Impacto:** `contracts/python/drakter_contracts/models/*`, `contracts/ts/index.ts`.

## [2026-11-13] API de copias montada; borrar por ActionService, restaurar sin ruta
- **Contexto:** `backend/app/services/backup_api.py` no estaba montado, usaba una puerta de confirmación propia (`restore-request`, `delete-request`, `confirmation_id` en el cuerpo) y no podía crear copias: `verify_backup` exigía un sidecar `.sha256` que un bundle no lleva.
- **Decisión:**
  - Se monta con `backend/app/api/backups.py`.
  - `DELETE /api/v1/backups/{name}` va sin cuerpo y responde 409. Se borra en `/confirmations/{id}/approve` mediante la acción `delete_backup` (`services/backup_actions.py`: permiso `backups.delete`, riesgo `confirm`, `external`, objetivo con el SHA-256 del archivo → `conflict` si cambia).
  - Se retiran la puerta propia y la ruta `restore`.
  - Una BD extraída de un bundle se verifica sin sidecar (`verify_backup(check_digest=False)`), porque `read_bundle` ya comprobó su SHA-256 contra el manifiesto. Una copia suelta sigue exigiéndolo.
- **⚠️ Restaurar:** sin ruta. `restore_bundle` llama a `database/backup.restore_backup`, que toma el bloqueo de instancia con un `flock` propio. Con el backend en marcha, ese bloqueo ya lo tiene el proceso, y nadie instala `post_restore_hooks` ni `restore_quiesce`. Necesita un diseño propio: dejar de servir, soltar el bloqueo, restaurar, invalidar confirmaciones y rearrancar. Hoy se restaura con el backend parado (`python -m app.database.cli restore`, copias SQLite).
- **Alternativas descartadas:** mantener la puerta propia, que contradice el camino único de README §5. Montar `restore` igualmente: fallaría siempre con `DatabaseInUse`.
- **Motivo:** decisión de cierre del coordinador (drakter-33): copias es de backend-base, por el pipeline único o sin montar.
- **Impacto:** `backend/app/api/backups.py`, `services/backup_api.py`, `services/backup_actions.py`, `services/backup_service.py`, `database/backup.py`, `permissions/wiring.py` (registro de la acción, drakter-34), `contracts/api/routes.md`. Checklist 2 y la parte de copias de la 16. `/settings/backups` (copias SQLite sueltas) sigue siendo lo que usa la GUI.

## [2026-11-13] Cableado del flujo de confirmaciones en main
- **Contexto:** la revisión adversarial encontró que `main.py` no llamaba a `install_security`/`start_security`/`stop_security` y que `install_security` rompía. Todo borrado respondía 503 `confirmation_unavailable`.
- **Decisión:** `backend/app/permissions/wiring.py` (`wire_security`) instala `ActionService`, registra las `ActionSpec` de calendario y asignaturas, da a tareas y proyectos una puerta real (`PendingConfirmationGate`) sobre `pending_confirmations` y sus ejecutores de lo aprobado, y pone esos puertos en `app.state.workspace_ports` y en `tool_state` del agente. `main.py` llama a `wire_security` en `_install_services`, a `start_security` tras `migrate` y a `stop_security` al apagar. `ActionService.add_executor` admite ejecutores hasta que el registro se congela.
- **Alternativas descartadas:** cablear cada módulo en `main.py` (más superficie en un archivo compartido).
- **Motivo:** `CLAUDE.md` §8: las acciones destructivas requieren confirmación, y debe poder confirmarse.
- **Impacto:** `backend/app/main.py`, `backend/app/permissions/`, `backend/app/services/actions.py`, Checklist 16.

## [2026-11-13] Endurecimiento de pending_confirmations (0012)
- **Contexto:** el banco red-team (CONF-03/04/06/07) mostró que por SQL directo una fila podía nacer aprobada, cambiar de id o de turno y reescribir su resultado una vez cerrada.
- **Decisión:** migración `0012_confirmation_hardening.sql` con `trg_pc_identity`, `trg_pc_born_pending`, `trg_pc_closed` y `trg_pc_decided_once`. Pasan a obligatorios en `check_migrations.py`.
- **Alternativas descartadas:** confiar solo en el código de `ActionService` (no protege de errores de otros módulos).
- **Motivo:** defensa en profundidad sobre la tabla que autoriza lo destructivo.
- **Impacto:** `backend/migrations/`, esquema v12.

## [2026-11-13] Una regla de caracteres invisibles para texto no confiable
- **Contexto:** el sobre de herramientas solo quitaba bidi y U+200B. La memoria comparaba sujetos y contenidos sin quitar invisibles (INJ-03/16/40/41).
- **Decisión:** `backend/app/core/text.py` (`strip_invisible`) quita Cc salvo `\n` y `\t`, Cf, Cs, Cn, CGJ, rellenos hangul, selectores de variante y el blanco braille. Lo usan `untrusted_envelope`, `sanitize_untrusted`, `content_hash`, `normalize_subject` y la deduplicación.
- **Alternativas descartadas:** listas por módulo (divergen).
- **Motivo:** un solo criterio para lo que "no se ve".
- **Impacto:** `tools/envelope.py`, `integrations/memory/`. Los emojis con ZWJ o VS16 se descomponen dentro del sobre (aceptado).

## [2026-11-13] Contradicción INJ-24 / CONF-54 del banco red-team
- **Contexto:** INJ-24 pide que `tool_action_spec` rechace herramientas WRITE sin `summarize`; CONF-54 pide que las adapte.
- **Decisión:** se adaptan con un resumen por defecto construido por el backend desde los argumentos validados ("El agente quiere ejecutar «x» con {…}"), saneado por `_displayable`. INJ-24 queda como BREACH conocida del banco.
- **Alternativas descartadas:** rechazar (rompe la adaptación de 38 herramientas WRITE).
- **Motivo:** el aprobador ve qué se ejecuta, y el texto lo pone el backend, no el modelo.
- **Impacto:** `backend/app/permissions/tool_gate.py`, `tests/security/`.

## [2026-11-13] Revisión adversarial de seguridad cerrada
- **Contexto:** `RUN_STATE.md` tenía pendiente la revisión adversarial de `drakter/seguridad`.
- **Decisión:** se da por hecha. Banco de 200 ataques: de 125/27/47/1 (BLOCKED/BREACH/N/A/ERROR) a 169/12/19/0. Quedan abiertas, de diseño: contaminación solo en memoria (CONF-46/INJ-26), canal de datos de `TurnRequest` y contaminación de `build_context` (INJ-11/14/25, no explotables mientras `build_context` no esté conectado), INJ-32, INJ-05 y FILE-DB-02 (TOCTOU, riesgo bajo). Las herramientas CONFIRM del agente siguen denegadas (`DefaultToolGate` en el runtime): falla cerrado. (Resuelto después: `b722aca` y `42a0a17` ponen `BackendToolGate` en el registro del agente.)
- **Motivo:** `CLAUDE.md` §8.
- **Estado posterior:** `build_context` ya está conectado (`df258b1`), así que INJ-11/14/25 INJ-14 se cierra en `1588c04`; INJ-11/25 quedan como diseño pendiente (campo de contexto aparte en `TurnRequest`), mitigadas porque tainted se propaga y fuerza confirmación (`df258b1`, `1588c04`).
- **Impacto:** `RUN_STATE.md` (quitar "Seguridad sin revisar"), Checklist 16.

## [2026-11-13] Empaquetado: backend PyInstaller con app.* explícito y electron-builder por npx
- **Contexto:** primera ejecución real del empaquetado (Checklist 17). El backend congelado no incluía `app.*` porque `collect_submodules` corre en un subproceso aislado sin `pathex`, y respondía 404 en todas las rutas. El `.deb` exigía `homepage`, y `electron-builder` no está en `desktop/package.json`.
- **Decisión:** el `.spec` añade `backend/` a `sys.path` antes de `collect_submodules("app")` y aborta si falta `app.api.health`. El `.yml` define `homepage` con `extraMetadata`. Se empaqueta con `npx --yes electron-builder@26.18.0 … -c.npmRebuild=false` y, si `/tmp` es un tmpfs justo, con `TMPDIR` en disco.
- **Alternativas descartadas:** listar a mano los `hiddenimports` de `app` (se desincroniza con cada módulo nuevo); añadir `homepage` a `package.json` (archivo compartido); dejar que electron-builder recompile `node_modules` (compartido entre worktrees).
- **Motivo:** que el instalador arranque un backend completo y que el build falle en voz alta si vuelve a perder módulos.
- **Impacto:** `desktop/electron-builder.backend.spec`, `desktop/electron-builder.yml`, `desktop/electron-builder.README.md`, `docs/installation/paquete-deb.md`, Checklist 17 «Crear instalador».

## [2026-11-13] La GUI no aplica ni revierte mejoras
- **Contexto:** al regenerar `ALLOWED_ROUTES` desde `contracts/api/routes.md` entraban `POST /api/v1/improvement/proposals/{id}/apply` (y potencialmente `/revert`), rutas que cambian producción.
- **Decisión:** el renderer (token `ui`) no puede llamarlas: `desktop/electron/scripts/generate-routes.mjs` las trata como solo `approver` y `desktop/electron/main/apiProxy.ts` aborta el arranque si aparecen en la lista. Aprobar y revertir siguen el flujo `approval-request`/`revert-request` → 409 → `/confirmations/{id}/approve`.
- **Alternativas descartadas:** marcarlas `(approver)` solo en `routes.md` (frágil si la marca se pierde).
- **Motivo:** CLAUDE.md §8: la automejora no modifica producción sin autorización. Decisión de drakter-33.
- **Impacto:** `desktop/electron/scripts/generate-routes.mjs`, `desktop/electron/main/apiProxy.ts`, `desktop/electron/shared/routes.generated.ts` (`89a87b5`). Checklist 1 y 15.

## [2026-11-13] Arranque de Electron en desarrollo y pruebas
- **Contexto:** en la máquina de desarrollo `chrome-sandbox` no es SUID root, y Drakter usa `requestSingleInstanceLock`.
- **Decisión:** en desarrollo y en e2e se arranca con `DRAKTER_DEV_NO_SANDBOX=1` y `--no-sandbox` en argv; las pruebas paralelas usan `--user-data-dir` propio. En producción el sandbox sigue siendo obligatorio (`sandbox.ts` aborta con `--no-sandbox`).
- **Alternativas descartadas:** `chown root` + `chmod 4755` de `chrome-sandbox` (requiere sudo y se pierde con cada reinstalación de node_modules).
- **Motivo:** sin estas dos cosas, Electron aborta (FATAL setuid sandbox) o sale sin ventana al haber otra instancia.
- **Impacto:** `tests/e2e/stack.py`, `scripts/dev.sh`, documentación de desarrollo. Checklist 1.

## [2026-11-13] Lo que propone el agente en sesión contaminada es de terceros
- **Contexto:** el red-team (INJ-32) mostró que el modelo podía repetir un documento con `propose_memory` y el recuerdo quedaba con trust `derived`.
- **Decisión:** `propose_memory` pasa la contaminación de la sesión al servicio; si está contaminada, o no se puede saber, el recuerdo entra `third_party`. Fuera de eso sigue `derived`. Solo el usuario puede subirlo con una corrección. La conversación también marca el turno como contaminado (INJ-14).
- **Alternativas descartadas:** todo lo del agente `third_party` (contradice INJ-31 y quita valor a lo derivado limpio); heurística por contenido (no distingue un documento de una frase legítima).
- **Motivo:** CONTRACT de memoria, regla 2: los terceros siempre `THIRD_PARTY`.
- **Comprobado:** `check_memory_rules.py` 40/40, smoke de memoria 21/21, INJ-31 sigue BLOCKED; banco 170 BLOCKED / 11 BREACH.
- **Impacto:** `backend/app/tools/memory.py`, `backend/app/integrations/memory/service.py`, `context/builder.py` (`1588c04`); sonda INJ-32 del banco a actualizar.

## [2026-11-13] Brechas del red-team conocidas al cierre
- **Contexto:** tras el cableado de seguridad y los arreglos del cierre, el banco `tests/security/run.py` deja 11 BREACH (cribado de drakter-42 y revisión de drakter-34).
- **Decisión (drakter-33):**
  - Falsos positivos: DESK-04 (permiso de micrófono solo de audio, intencionado) y DESK-16 (`target=` es una prop de React).
  - Resuelto: DESK-20 (`89a87b5`: el renderer ya no puede aprobar propuestas de automejora).
  - Ya decidido: INJ-24, contradicción del propio banco con CONF-54 (ver «Contradicción INJ-24 / CONF-54 del banco red-team»).
  - Arreglado en código, falta ajustar la sonda: INJ-32 (`1588c04`).
  - Quedan con ⚠️ de diseño: INJ-05 (título y URL de `read_resource` fuera del sobre; no se hizo en el cierre), CONF-46/INJ-26 (la contaminación de la sesión no persiste al reiniciar), INJ-11/25 (`TurnRequest` sin canal de datos aparte; mitigado porque tainted se propaga y fuerza confirmación, `df258b1`, `1588c04`) y FILE-DB-02 (TOCTOU en `connect`, bajo riesgo).
- **Alternativas descartadas:** cerrar las de diseño en este cierre (exigen migración nueva, cambiar el contrato `TurnRequest` y el runner: fuera de alcance).
- **Motivo:** el cierre solo termina lo empezado; lo que queda está mitigado o es de bajo riesgo.
- **Recuento final (drakter-34):** 169 BLOCKED / 12 BREACH / 19 N/A / 0 ERROR, con las 12 BREACH clasificadas arriba. Con el modelo real, el recuerdo trampa no se obedece y, con la sesión contaminada, `create_task` queda pendiente de confirmación.
- **Impacto:** Checklist 16 («Proteger operaciones destructivas», «Revisar datos sensibles»), `RUN_STATE.md`.

## [2026-11-13] Guiones del stub propios de la pasada integrada
- **Contexto:** los guiones de `tools/dev-llm-stub/scenarios` piden herramientas nativas de Hermes (`read_file`, `terminal`), que el runner de Drakter no ofrece (solo `mcp__drakter__*`); las comprobaciones de herramientas acababan "escenario no aplicable". `check_hermes.sh` sí los necesita así.
- **Decisión:** el arnés arranca el stub con `--scenarios tests/e2e/stub-scenarios`: `list_tags` (lectura), `forget_memory` (CONFIRM; la puerta decide antes del handler) y `search_resources` sobre una nota con inyección que crea la propia comprobación (`index_content=true`).
- **Alternativas descartadas:** cambiar los guiones del stub (rompe `check_hermes.sh`); ofrecer `file`/`terminal` a Hermes (viola la lista blanca).
- **Motivo:** probar las barreras con el catálogo real que ve el modelo.
- **Impacto:** `tests/e2e/stub-scenarios/`, `tests/e2e/harness/stack.py`, `tests/e2e/scenarios/conversation.py`, `tests/e2e/README.md`; Checklists 3, 13 y 16.

## [2026-11-13] Electron del arnés: sin sandbox, perfil propio y espera al agente
- **Contexto:** `main` rechaza `--no-sandbox` sin `DRAKTER_DEV_NO_SANDBOX=1`, y sin `--user-data-dir` propio el bloqueo de instancia única choca con la instancia del usuario; además Hermes arranca en segundo plano y los turnos inmediatos salen 503 `agent_unavailable`.
- **Decisión:** solo en `tests/e2e/harness/stack.py`: `--no-sandbox` + `DRAKTER_DEV_NO_SANDBOX=1` + perfil en el TMPDIR de la pasada; tras cada arranque del backend, esperar (≤150 s) a que `/api/v1/agent/status` deje `offline`. `main` no cambia (confirmado con drakter-48).
- **Alternativas descartadas:** relajar la regla de sandbox en `main`; reintentar turnos.
- **Motivo:** la restricción del sandbox es correcta para producción; el arnés es el que debe adaptarse.
- **Impacto:** `tests/e2e/harness/stack.py`, `tests/e2e/run.py`; Checklists 1, 3 y 5.

## [2026-11-13] Publicación en GitHub e higiene de repositorio open source
- **Contexto:** el usuario autoriza publicar `main` en `github.com/Lordi898/Drakter` (privado) y dejarlo listo para hacerse público. `.claude/` llevaba copiado contenido de terceros; las 19 skills de `LLMTooling/agent-skills@f096e2bc` no tienen licencia en ningún nivel del repositorio de origen, así que no hay permiso para redistribuirlas.
- **Decisión:**
  - Antes del push, escaneo de secretos de todo el historial de `main` con gitleaks 8.21.2 (checksum verificado): 7 hallazgos, todos falsos positivos (cebos de `tests/security/`, el nonce de ejemplo de RFC 6455 y ejemplos de documentación de terceros). Sin emails personales ni archivos `.env` reales en el historial. gitleaks no detecta rutas personales: el historial **sí conserva** `/home/imagana` en el contenido de `0b73313`, `dda565b` y `38b3b50` y en el mensaje de `f641964` (el árbol actual ya no la tiene). No se reescribe el historial ahora: limpiar esa ruta (`git filter-repo --replace-text` y `--replace-message`), en la misma pasada que sacaría del historial las skills de LLMTooling y los `.docx`, o publicar desde un historial nuevo, lo decide el usuario antes de hacer público el repositorio y es un punto bloqueante del informe de publicación.
  - Las 19 skills de LLMTooling salen del árbol y se ignoran; `scripts/install-agent-skills.sh` las descarga del commit fijado y las reproduce byte a byte (comprobado). El resto de `.claude/` tiene licencia permisiva (MIT o Apache-2.0) y se queda, con su `LICENSE` y su fila en `THIRD_PARTY_NOTICES.md`; se añaden los `LICENSE` que faltaban (`skill-creator`, `find-skills`) y los textos de VoltAgent, lst97 y shadcn/ui en `docs/third-party-licenses/`.
  - Origen identificado por hash de blob: `skill-creator` es `sentient-agi/meta-skill-creator@02cb1db9` (Apache-2.0); `categories/01–10` son `VoltAgent/awesome-claude-code-subagents@ed74d115` y `categories/11–17` + `agent-organizer.md` son `lst97/claude-code-sub-agents@96f5a506` (ambos MIT); `find-skills` es `vercel-labs/skills@b716f9dc` (MIT).
  - Se añaden `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1, traducción oficial al español), `SECURITY.md` (reporte privado por GitHub, que solo existe en repositorios públicos: hay que activarlo al hacerlo público y comprobar que `gh api repos/Lordi898/Drakter/private-vulnerability-reporting` da `{"enabled":true}`; el contacto de respaldo queda pendiente de que lo decida el usuario), `THIRD_PARTY_NOTICES.md`, `.editorconfig`, plantillas de issues y PR, `CODEOWNERS`, Dependabot y CI (`.github/workflows/ci.yml`: las cuatro comprobaciones críticas del backend y typecheck + build del escritorio, acciones fijadas por SHA, permisos de solo lectura, sin clave de API).
  - `writing-skills/references/anthropic-best-practices.md` (copia de la guía «Skill authoring best practices» de Anthropic que traía obra/superpowers) sale del árbol: ese texto es de Anthropic y no está bajo la MIT de superpowers. `writing-skills/SKILL.md` enlaza la página oficial.
  - Licencia: ver la entrada siguiente.
- **Alternativas descartadas:** mantener las skills de LLMTooling en el árbol (redistribución sin permiso); borrarlas sin script (rompe el flujo de desarrollo con Claude Code); reescribir el historial para sacarlas también de ahí (decisión del usuario antes de hacer público el repositorio).
- **Motivo:** que el repositorio pueda hacerse público sin redistribuir contenido sin licencia y con lo mínimo de un proyecto open source serio.
- **Impacto:** `.gitignore`, `.claude/skills/`, `scripts/install-agent-skills.sh`, documentos de la raíz, `.github/`, `docs/third-party-licenses/`. Tras actualizar un checkout existente hay que ejecutar `scripts/install-agent-skills.sh` para recuperar las 19 skills.

## [2026-11-13] Licencia Apache-2.0
- **Contexto:** el repositorio necesitaba licencia antes de poder hacerse público; la elige el usuario.
- **Decisión:** Apache-2.0. `LICENSE` con el texto oficial íntegro de apache.org (SHA-256 `cfc7749b…`), `NOTICE` con el titular («Copyright 2026 Lordi898 and the Drakter contributors»), campo SPDX `license = "Apache-2.0"` en `desktop/package.json` y en los `pyproject.toml` de `backend/`, `voice/` y `contracts/python/`. Sin cabeceras por archivo. Las contribuciones entran bajo Apache-2.0 (§5), sin CLA y con DCO opcional. La licencia no cede la marca «Drakter» (§6).
- **NOTICE de terceros:** ninguno de los componentes Apache-2.0 redistribuidos (`frontend-design`, `skill-creator`) trae `NOTICE` propio, así que el `NOTICE` del proyecto no necesita atribuciones adicionales; remite a `THIRD_PARTY_NOTICES.md`.
- **Alternativas descartadas:** MIT (sin concesión explícita de patentes ni cláusula de marca).
- **Motivo:** decisión del usuario; licencia permisiva compatible con todas las dependencias actuales.
- **Impacto:** `LICENSE`, `NOTICE`, `README.md`, `CONTRIBUTING.md`, `THIRD_PARTY_NOTICES.md`, `CHANGELOG.md`, `desktop/package.json`, `desktop/package-lock.json`, `pyproject.toml` de `backend/`, `voice/` y `contracts/python/`.

## [2026-11-13] Binario de Electron: postinstall propio e idempotente
- **Contexto:** con npm 11.19, `npm ci` en `desktop/` dejaba `node_modules/electron` sin binario y la app no arrancaba hasta lanzar `node node_modules/electron/install.js` a mano. Se atribuía a npm (y los docs y `dev.sh` decían «npm 12»).
- **Causa real (reproducida en un clon limpio):** no es `ignore-scripts` (`false`, sin `.npmrc`), ni `allowScripts` (en npm 11.19 es solo consultivo y `approve-scripts` dice «No packages with unreviewed install scripts»). El `package.json` de `electron@45.2.3` ya no declara ningún `scripts`: la descarga pasó a ser perezosa (`getElectronPath()` la lanza al primer uso, y `install-electron` es un bin aparte). Ningún npm tiene nada que ejecutar.
- **Decisión:** `desktop/package.json` añade `"postinstall": "node scripts/ensure-electron.cjs"`; ese script llama a `install.js` de Electron (que sale al instante si el binario ya existe) y se salta con `ELECTRON_SKIP_BINARY_DOWNLOAD`. `scripts/dev.sh` y `scripts/drakter-local.sh` lo ejecutan también, de modo que un checkout ya instalado o un `--ignore-scripts` se arreglan solos. La CI define `ELECTRON_SKIP_BINARY_DOWNLOAD=1` (solo hace typecheck y build). README, CONTRIBUTING e `instalar.md` quedan con `npm ci` a secas.
- **Alternativas descartadas:** `allowScripts`/`trustedDependencies` (no hay script que permitir); `.npmrc` con `ignore-scripts=false` (ya es el valor); documentar el comando manual (es lo que fallaba).
- **Motivo:** el camino estándar de npm (un `postinstall` del propio proyecto) más un paso idempotente que cubre los casos en que no corre.
- **Impacto:** `desktop/package.json`, `desktop/scripts/ensure-electron.cjs`, `scripts/dev.sh`, `scripts/drakter-local.sh`, `.github/workflows/ci.yml`, `README.md`, `CONTRIBUTING.md`, `docs/installation/instalar.md`. Un checkout con binario ya presente no necesita reinstalar.

## [2026-11-13] Los runtimes nunca viven en directorios temporales
- **Contexto:** una limpieza borró `/var/tmp/drakter-8`, que contenía el Python 3.12 del que colgaban `~/.local/bin/python3.12`, `backend/.venv` y el venv del SDK de Fish; la app dejó de arrancar. Seguían frágiles `~/.local/bin/python3.14` (en `/var/tmp/drakter-5-verif/py/`) y `hermes-python` (venv y clon editable en `/var/tmp/drakter-agente-hermes/hv/`, con ese mismo Python base). `/var/tmp` sobrevive a reinicios, pero no a limpiezas.
- **Decisión:** regla: los runtimes (intérpretes de Python, venvs, clones instalados en editable) nunca viven en `/tmp` ni `/var/tmp`. Python 3.12 y 3.14 son los gestionados por uv (`~/.local/share/uv/python/`), enlazados desde `~/.local/bin/`. Hermes (v0.22.7, `b200f5bc`, desde git) se instala con `scripts/install-hermes.sh`, idempotente y con tag y commit fijados: clon en `~/.local/share/drakter/src/hermes-agent`, venv en `~/.local/share/drakter/venvs/hermes`, `~/.local/bin/hermes-python` apuntando a él. `scripts/check-env.sh` da FALTA si `python3.12`, `python3.14`, `hermes-python`, `backend/.venv` o cualquier venv de `~/.local/share/drakter/venvs/` resuelven bajo `/tmp` o `/var/tmp` (también en `pyvenv.cfg`) o son enlaces rotos, con el comando de arreglo.
- **Alternativas descartadas:** seguir en `/var/tmp` documentándolo como provisional (ya falló); instalar Hermes con `pip` o desde PyPI (versión retirada, prohibido); venv no editable sin clon (el lock de Hermes se resuelve desde su árbol).
- **Motivo:** una limpieza de directorios temporales no debe poder romper el entorno; y el proyecto debe detectar el problema antes de que ocurra.
- **Impacto:** `scripts/install-hermes.sh` (nuevo), `scripts/check-env.sh`, `README.md`, `CONTRIBUTING.md`, `docs/installation/`, `docs/RUN_STATE.md`. Diferencia de dependencias frente al venv anterior: el nuevo no trae `aiohttp` (3.14.5) ni `aiohappyeyeballs`, `aiosignal`, `frozenlist`, `multidict`, `propcache`, `yarl`: sin gateway no hacen falta (CONTRACT.md). Pendiente: `scripts/drakter-local.sh` usa `/var/tmp/drakter-stub/sandbox` para el stub (datos de pruebas, no runtime).

## [2026-11-13] Perfiles de voz: IDs de Fish en un único archivo del usuario
- **Contexto:** la voz se rehará sobre Pipecat con TTS de Fish Audio (`s2.1-pro-free`: sin la cabecera `model`, o con una desconocida, Fish cobra con `s2.1-pro`). El usuario quiere poner los IDs de voz en un solo sitio y cambiarlos cuando quiera, y pedir otra voz hablando.
- **Decisión:** `~/.config/drakter/voces.toml` (XDG), fuera del repo, es el único sitio con IDs. Se crea desde `contracts/python/drakter_contracts/templates/voces.template.toml` (IDs vacíos, permisos 600, sin sobrescribir). Cargador y validación en `drakter_contracts/voice_profiles.py` (Pydantic + `tomllib`; en `contracts` para que lo compartan backend, `scripts/voces.sh` y el futuro proceso de voz Pipecat): alias únicos sin mayúsculas ni tildes, perfil por defecto existente, modelo en lista blanca (solo `s2.1-pro-free`, salvo `allow_paid = true` a mano), ID de 32 hex; recarga por (mtime, tamaño); un perfil sin ID es «sin configurar». El backend guarda el perfil activo en el ajuste `voice_profile` (por nombre, nunca el ID) y expone `voice_list_profiles` (`voice.read`, read) y `voice_set_profile` (`voice.write`, write, sin confirmación, auditada por el registro). Se publica `voice.profile_changed` (solo desde la herramienta). El mensaje IPC `voice.set_profile {profile}` queda definido en `contracts` pero NO se envía: `VoiceService` no está montado en `main.py` y lo cableará Pipecat. El resultado de `voice_set_profile` lleva `applied_to_voice: false` mientras ningún TTS use el perfil, para que el agente no diga que ya suena. `resolve` tolera artículo y «voz» («la neutral»). `scripts/voces.sh listar|comprobar|probar`. Dominio `voice` nuevo en `TOOL_DOMAINS`, y `voice.read`/`voice.write` en `agent/configuration/permissions.json`.
- **Alternativas descartadas:** IDs en `.env` o en la BD (dos sitios, y el `.env` es de secretos); IDs en el repo (el usuario los pone); confirmación para el cambio de voz (solo cambia un nombre de perfil; una sesión con contenido no confiable ya lo convierte en confirmación); guardar el ID en el ajuste (la fuente de verdad del ID es el archivo, y así cambiarlo no deja ajustes obsoletos).
- **Motivo:** un único sitio editable, validación que falle en voz alta (un modelo de pago saldría en la factura) y el backend como fuente de verdad del ajuste.
- **Impacto:** `contracts/python/drakter_contracts/{voice_profiles.py,events.py,tools.py,templates/}`, `contracts/ts/index.ts`, `contracts/tools/{catalog.json,README.md}`, `backend/app/{services/voice_profile.py,tools/voice.py,services/settings*.py,integrations/voice/service.py}`, `backend/tests/check_voice_profiles.py` (y un paso en CI), `agent/identity/BEHAVIOR.md`, `agent/knowledge/TOOL_GUIDE.md`, `agent/configuration/permissions.json`, `scripts/voces.{sh,py}`, `docs/usage/voces.md`. No se toca la interfaz ni se implementa Pipecat.


## [2026-11-13] Voz v2: transporte WebRTC loopback y proceso de voz sobre Pipecat 1.16.0 (V-01 a V-05, V-35)
- **Contexto:** la voz v1 (captura propia, faster-whisper, Kokoro/Piper) quedó cerrada al mínimo a la espera del rediseño sobre Pipecat. Hacen falta cancelación de eco con altavoces sin sudo ni compilador, y que cambiar de red no tire la sesión.
- **Decisión:** transporte B: el renderer captura con `getUserMedia` (AEC3, NS, AGC) y habla por WebRTC loopback con `SmallWebRTCTransport` (`ConnectionMode.SINGLE`, `ice_servers=[]`) en `voice/`, con `pipecat-ai[webrtc,fish,kokoro]==1.16.0` sin `[local]` ni pyaudio (`sounddevice` entra por `moonshine-voice`, no se importa). Cliente WebRTC propio (~100 líneas, sin `@pipecat-ai/client-js`), señalización renderer → `window.api` → main → backend → IPC → voz y data channel con `ping` (V-02). ICE por loopback: `channels/webrtc.py` añade 127.0.0.1 a `aioice.ice.get_host_addresses` y el lanzador pasa `--allow-loopback-in-peer-connection` (V-03, se verifica en un spike al inicio de WP8a; si falla se retiran las promesas «sin red»). Un `PipelineTask` por conexión con modelos cargados una vez por proceso y `SessionState` fuera del pipeline (V-04). Transporte A (pw-record/pw-play) aplazado y `voice/audio/` borrado (V-05). Sin descargas en ejecución: modelos en `~/.local/share/drakter/models/` (Kokoro incluido), venv en `~/.local/share/drakter/venvs/voice` con `contracts/python` instalado; se borra `/tmp/dr-at` (V-35).
- **Alternativas descartadas:** captura con PipeWire en el proceso de voz (sin AEC sin sudo); `@pipecat-ai/client-js` (rompe `connect-src 'self'`); STUN/LAN (el spike anterior no era representativo); transporte por conexión con recarga de modelos.
- **Motivo:** único AEC viable para altavoces en esta máquina; aiortc no detecta desconexiones sin tráfico de datos; aioice excluye el loopback (verificado en `aioice/ice.py:98-100`).
- **Impacto:** `voice/` (WP1), `desktop/electron/main`, `desktop/src/voice/` (WP8a), `scripts/drakter`, `scripts/install-voice.sh`; Checklist 14.

## [2026-11-13] Voz v2: STT, VAD, fin de turno y activación (V-06, V-07, V-16, V-17, V-18)
- **Contexto:** el STT de Pipecat es segmentado y descarga en ejecución; hay que dimensionar para CPU (i7-8665U).
- **Decisión:** STT streaming propio sobre `moonshine-voice==0.1.6` (`small-streaming-es`, `tiny` de respaldo en `VoiceConfig.stt_model`), inferencia en `to_thread`, `TranscriptionFrame(finalized=True)` y `ttfs_p99_latency`. VAD `SileroVADAnalyzer` (`stop_secs=0,2`) en un `VADProcessor`; fin de turno `TurnAnalyzerUserTurnStopStrategy(LocalSmartTurnAnalyzerV3(cpu_count=2), wait_for_transcript=True)` en un único `UserTurnProcessor`, sin agregador de LLM. Activación con `openwakeword==0.4.0` (`hey_jarvis_v0.1.onnx`, umbral bajo, prebúfer de 2 s en `WakeGate`, solo audio) y confirmación textual («jarvis»/«hey jarvis» al inicio) en el puente. Super+J como atajo de GNOME por gsettings que ejecuta `scripts/drakter activate` → `second-instance` → `POST /voice/activate` (UDS 0600 si tarda más de ~0,5 s). Modo `standby` → `conversation` → `standby` con un único dueño (`Ctl.set_mode`); ventana en bandeja con `backgroundThrottling:false`; con la app cerrada no hay escucha.
- **Alternativas descartadas:** STT de Pipecat (segmentado, descarga); openWakeWord 0.6.0 (no instala en py3.12); `globalShortcut` (Electron 45 en GNOME lo rechaza en silencio, electron #52218, dato de terceros).
- **Motivo:** cola final medida aquí de 0,13-0,29 s (Moonshine) y fin de turno de 111-308 ms; un solo dueño del modo.
- **Impacto:** `voice/providers/{stt,vad,turn,wake}` (WP2), `scripts/install-shortcut.sh` (WP8a); Checklist 14.

## [2026-11-13] Voz v2: barge-in, ducking y capa 0 local (V-08, V-09, V-10, V-34)
- **Contexto:** con altavoces hay eco; un «eh» no debe cortar ni desviar.
- **Decisión:** barge-in «bajar primero, decidir después» en una sola `DrakterStartStrategy(BaseUserTurnStartStrategy)` dentro del `UserTurnProcessor`: con el bot callado abre por VAD; con el bot hablando baja el volumen y solo abre turno si la transcripción parcial lo confirma (≥ N palabras que no sean eco). Bajada con `DuckMixer(BaseAudioMixer)` en `TransportParams.audio_out_mixer` (coste: silencio continuo en reposo, se mide en WP9). Capa 0 local, sin LLM, con listas cerradas en `voice/conversation/layer0.es.toml`: `para/calla/basta/silencio` cortan la voz; `descansa/deja de escuchar/eso es todo` vuelven a reposo también con el bot callado; los asentimientos se descartan. Las confirmaciones nunca se hacen por voz: se dice `confirm_on_screen` y se enfoca la ventana.
- **Alternativas descartadas:** procesador delante del `UserTurnProcessor` (más piezas y problema de orden; queda como alternativa si la estrategia no basta); `VolumeFrame` (llega tarde tras la cola); `UserBackchannelFrame` (solo lo consume el agregador de LLM, que no se usa).
- **Motivo:** una estrategia de inicio ya recibe VAD, parciales y `BotStarted/StoppedSpeakingFrame`; regla §8 de confirmaciones.
- **Impacto:** `voice/conversation/` (WP4); Checklist 14.

## [2026-11-13] Voz v2: TTS Fish s2.1-pro-free con respaldo Kokoro, texto por proveedor y caché de frases (V-11 a V-15)
- **Contexto:** el modelo por defecto de Pipecat es `s2.1-pro` (de pago) y Fish deja de ser gratis el 30-11-2026.
- **Decisión:** `FishAudioTTSService` con `Settings(model="s2.1-pro-free", latency="balanced", normalize=False)` [verificar `normalize`], lista blanca de modelo y corte por fecha `fish_free_until=2026-11-30` (después Kokoro salvo `allow_paid`). Respaldo `KokoroTTSService` (int8, `ef_dora`) tras un `ServiceSwitcher` con estrategia propia: conmuta con auth/autorización/cuota/petición inválida o 3 errores seguidos, con un único aviso; la fábrica comprueba los ficheros antes de construir. Piper se elimina. Texto por proveedor con `text_transforms` (Fish: `keep_allowed, StripMarkdown, lexicon, normalize_es`; Kokoro: `strip_tags, …`); `SpeechGuard` solo para lo que cruza frases (código, tablas, URL). Caché mínima de ~17 frases en PCM emitidas como `TTSAudioRawFrame` entre `TTSStarted/StoppedFrame`, textos en `agent/identity/voice_phrases.es.toml`, CLI `python -m voice phrases`, clave `sha256(perfil + hash(id) + modelo + texto)`. Etiquetas de expresión con sintaxis nativa de Fish `[etiqueta]` de una lista cerrada (`drakter_contracts/speech_markup.py`), limpiadas en deltas y en el texto terminal.
- **Alternativas descartadas:** modelo por defecto de Pipecat (de pago); estrategia base de `ServiceSwitcher` (solo conmuta con `is_usable=False`); Piper (GPL, peor calidad); `OutputAudioRawFrame` para frases (no pone al bot «hablando»).
- **Motivo:** si el 1-12 Fish cobra en vez de fallar no habría aviso; Kokoro descargaría si faltan modelos; hoy `_close_turn` guardaría las etiquetas en la BD. TTFA medido: 0,60-0,86 s.
- **Impacto:** `voice/providers/tts/`, `voice/speech/` (WP3), `agent/identity/voice_phrases.es.toml`, `contracts/python/drakter_contracts/speech_markup.py` (WP0); Checklist 14.

## [2026-11-13] Voz v2: streaming con Hermes, steer, prefijos y sesión compartida (V-19 a V-23, V-32)
- **Contexto:** Hermes vive fuera de Pipecat; hay que hablar mientras genera, poder corregir a mitad y que voz y chat compartan conversación sin romper la caché de prompt.
- **Decisión:** `TurnTap` no bloqueante en `AgentRuntime` (cola, traga errores); el puente emite `LLMFullResponseStartFrame/LLMTextFrame/LLMFullResponseEndFrame` y el TTS agrega por frases; cada tramo lleva un `speech_id`. Un `AIAgent` por turno; effort por carril (`low` primer plano, `medium` trabajadores). `agent/identity/VOICE.md` en las instructions estables; canal, nota de «lo oído» y bloque de trabajos como prefijo del `turn_prompt`, sin BD ni `chat.user_message`. Op `steer` en el runner (`agent.redirect`, `pending_steer`) con filtro previo (sin asentimientos ni menos de `bargein_min_words` mientras piensa). Sesión compartida con `runtime.current_session()`; el renderer adopta el `session_id` de `chat.user_message` y `agent.turn_started`. Lo oído: `PlaybackTracker` después de `transport.output()`; al interrumpir, la voz envía `heard_tail` (≤80) y `pending_head` (≤200) y el backend los usa tal cual en la nota efímera; el WS solo lleva `sentence_index`.
- **Alternativas descartadas:** effort por canal (invalida la caché); system por turno (rompe la caché); texto gris de lo no oído en el chat; contar lo sintetizado como oído.
- **Motivo:** `redirect` sigue con el mismo `turn_id`: sin `speech_id` la corrección quedaría muda o el turno cortado seguiría sonando. TTFT medido: 0,45 s (low) frente a 0,72 s (n=1).
- **Impacto:** `backend/app/integrations/hermes/` (WP6), `backend/app/integrations/voice/` (WP5), `agent/identity/VOICE.md`; Checklist 3 y 14.

## [2026-11-13] Drakter Jobs: carriles de trabajo en segundo plano (V-24 a V-27)
- **Contexto:** tareas largas no deben bloquear la conversación por voz.
- **Decisión:** carriles independientes (`Lane` = TurnTracker, ToolRegistry sin `jobs_*`, AgentToolsServer con token propio, Supervisor, home `hermes-w1`), N=1 sin cola (`jobs_full`). Herramientas `jobs_start/status/amend/cancel` (dominio `jobs`, permisos `jobs.read/jobs.write`). La clasificación nueva/modificación/estado/parar la hace el Hermes de primer plano con un bloque «Trabajos en curso» (eval de 20-30 frases). Confirmaciones de trabajos: la herramienta devuelve `confirmation_required`, el turno del trabajo termina y el trabajo acaba `completed` con `pending_actions`; la confirmación sigue su TTL en pantalla con `job_id`; no existe `waiting_confirmation`; con la sesión contaminada, `jobs_start` y `jobs_cancel` suben a confirmar. Fin de trabajo: notificación, frase `job_done` en silencio y resumen en el prefijo del siguiente turno con sobre de no confiable, sin insertar mensaje de asistente.
- **Alternativas descartadas:** `delegate_task(background=true)` de Hermes (el runner JSONL no vacía su `completion_queue` y las llamadas MCP de los hijos llegarían fuera del turno activo); estado `waiting_confirmation`; mensaje de asistente fuera de turno (desincroniza el transcript de Hermes).
- **Motivo:** la acción la ejecuta siempre el backend al aprobarla, nunca el agente (§8). KISS.
- **Impacto:** `backend/app/jobs/`, `backend/app/tools/jobs.py`, `backend/migrations/0014_jobs.sql`, `backend/app/integrations/hermes/lanes.py` (WP7); `contracts/python/drakter_contracts/jobs.py`, `contracts/tools/catalog.json`, `agent/configuration/permissions.json` (WP0); Checklist 3 y 13.

## [2026-11-13] Voz v2: estado del personaje, altavoz, ajustes y micrófono (V-28 a V-31, V-33)
- **Contexto:** había dos fuentes del estado del personaje y ningún evento al cambiar un ajuste.
- **Decisión:** `StatusArbiter` (lo crea `AgentRuntime`) es el único productor de `agent.status_changed`; `GET /agent/status` devuelve `arbiter.current`. Ajuste `voice_tts_enabled` (defecto `true`) como único punto de silencio: con `false` el backend no envía `speak.*` y manda `speak.stop{mute}`, sin cerrar el micrófono. Turnos escritos leídos hasta `speak_max_chars_text` (provisional 350) y cierre con `rest_on_screen`. Propagación de ajustes con `add_setting_listener(fn(key, value))`, llamado desde REST y `voice_set_profile`. Micrófono calculado en el renderer (`pista cerrada ? off : modo`), fuera de `voice.state`; apagarlo es `sender.replaceTrack(null)` + `track.stop()`, sin renegociar.
- **Alternativas descartadas:** leer `runtime._state` en el resync (segunda fuente); `mic` en `voice.state` (quien sabe si la pista está cerrada es el renderer).
- **Motivo:** un solo origen de verdad por dato. Decisiones por defecto que el usuario puede revertir: V-29, V-30 y V-26.
- **Impacto:** `backend/app/events/status.py` (WP6), `backend/app/services/settings.py` (WP5), `desktop/src` (WP8b); `SETTING_KEYS` (WP0); Checklist 14.

## [2026-11-13] Voz v2: alcance de la v1, aplazados y licencias (V-36, V-37, V-38)
- **Contexto:** el catálogo de experiencia tenía 47 features y Fish deja de ser gratis en 17 días.
- **Decisión:** en v1 entran las features 1-11, 15-32 y 34-36 salvo el texto gris de lo no oído. Aplazado: pausa por LLM, precalentamiento, avisos de calendario, hotwords, dictado, subtítulos, sonido ambiental, emoción, terceros, volumen por voz, palabras «Drakter» y «despierta», promoción automática a trabajo, selector de voz en la UI, panel de latencias, primer plano construido con `Lane`, transporte A. Descartado: turnos especulativos, backchannels del bot, speech-to-speech, identificación de hablante, RNNoise/Krisp, Piper, effort por canal, `globalShortcut`, `delegate_task`. Licencias en `THIRD_PARTY_NOTICES.md`: `hey_jarvis` (CC BY-NC-SA 4.0), Moonshine en castellano (ambigua), PyAV/FFmpeg (LGPL), scikit-learn y sounddevice; válidas para uso personal, a revisar si se distribuye.
- **Alternativas descartadas:** las aplazadas dependen de mediciones; las descartadas rompen el §8 o no compensan.
- **Motivo:** coherencia entre frentes y plazo de Fish.
- **Impacto:** Checklist 14 (ítem «Aplazado» sin casilla activa), `THIRD_PARTY_NOTICES.md`.

## [2026-11-13] WP0: contratos de la voz v2 congelados en código y ajustes de forma
- **Contexto:** WP0 congela la sección 4 del plan de voz v2 antes de lanzar WP1-WP8b en paralelo. Algunos nombres del plan no casaban con el código existente.
- **Decisión:**
  1. El plan habla de `EventType` y `PAYLOAD_CHECKS` en `events.py`; el código real usa el diccionario `EVENTS` (tipo → modelo Pydantic) y el TS genera `EventType`. Los eventos nuevos se registran en `EVENTS`.
  2. Modelos REST de voz (`VoiceOfferIn/Out`, `VoiceActivateIn`, `VoiceModeIn`, `VoiceStatusOut`) en `voice_ipc.py`, junto a los de IPC; `jobs.py` y `voice_ipc.py` entran en `gen_ts.py`. El payload de `voice.state` es `events.VoiceState`; el `evt` IPC equivalente es `EvtState` (sin `wake_enabled`).
  3. `voice.tts_fallback.from` es palabra reservada en Python: el atributo es `from_` con alias `from` (se serializa como `from`).
  4. `registry.create("*"→"null")` pasa `kind` como primer argumento a `voice.providers.null:create`, que necesita saber qué clase de objeto nulo devolver.
  5. `window.api.voice/jobs` son obligatorios en `DrakterApi`; para que `tsc` compile, el preload lleva una implementación provisional que pasa por `apiCall` (main valida la ruta contra `ALLOWED_ROUTES`) y el canal `voice:mic-toggle`. WP8a la sustituye. `operations.ts` exporta `OPERATIONS` (nombre de operación → método y ruta).
  6. `routes.md`: las rutas de voz v1 (`/voice/mic`, `/voice/wakeword`, `/voice/listen/*`, `/voice/interrupt`) se sustituyen por las cuatro de v2, y se añade la sección de trabajos.
  7. `SETTING_KEYS` gana las tres claves nuevas; `settings_models.py` exporta además `SETTING_DEFAULTS` y `SETTING_CHOICES` para que WP5 valide sin inventar valores.
  8. `voice/registry.py` se reescribe: `voice/manager.py` (v1, lo borra WP1) deja de poder construir motores; no lo usa nadie en ejecución.
  9. La rama es `ao/voice-contracts/root` (sesión AO) en vez de `voz-v2/wp0`, para que AO siga el PR.
- **Alternativas descartadas:** renombrar `EVENTS` (rompería el hub y el generador); `voice`/`jobs` opcionales en `DrakterApi` (obligaría a comprobaciones en toda la UI).
- **Motivo:** congelar lo más simple que cumple la sección 4 sin romper lo que ya funciona.
- **Impacto:** `contracts/**`, `voice/{ports,registry,CONTRACT}.*`, `backend/app/services/settings_models.py`, `backend/app/integrations/hermes/CONTRACT.md`, `desktop/electron/{shared,preload}`, `desktop/src/voice/contract.ts`.

## [2026-11-14] WP9: integración de la voz v2
- **Contexto:** fusión de WP1..WP8b en `ao/voice-integration/root` y primera ejecución de la voz v2 con la app integrada (arrancada con `scripts/drakter`, switch de loopback y `DRAKTER_DATA_DIR` sobre una copia de la BD real; altavoces y micrófono internos del portátil, frases sintéticas de Kokoro `em_alex` y, para «Hey Jarvis», `am_adam` en inglés inyectadas por una fuente virtual de PipeWire). Sin conflictos de fusión; `python -m voice check` «Todo en orden», check_pipeline 21 PASS, check_conversation OK, check_wp2 OK con modelos reales, check_sim 22/22, typecheck y build del escritorio limpios.
- **Decisión:** arreglos de integración aplicados:
  1. Fábricas `create()` de WP3 (guard, phrases, playback) y alias de config (`phrases_cache_dir`, `tts_threads`, campos `stt_*`/`vad_*` en `VoiceConfig`); `wake_models` con o sin `.onnx`; aioice por nombre (`use_ipv4`/`use_ipv6`).
  2. Fish no daba audio si una frase fija (`TTSSpeakFrame`) caía dentro de un contexto de respuesta abierto (se reproducía aislado): el puente abre el `LLMFullResponseStart` de forma perezosa con el primer texto y `speak.flush` cierra sin reabrir.
  3. Pipecat 1.16 suelta los `TTSTextFrame` de todo un contexto con su primer audio: `awaiting_answer` solo cuenta con el bot callado, y lo oído al interrumpir se estima por tiempo hablado (15 car/s).
  4. Barge-in en el hueco entre texto y audio: `Session.speech_open`; con tramo pendiente o agente pensando, el VAD no abre turno al instante (decide por transcripción). «para …» con turno en curso es parada. Un parcial «sí…» no descarta el tramo.
  5. Backend: sesión de los turnos ya terminados para registrar lo oído («siga»); `confirm_on_screen` una vez por `action_id` (dedupe del reanuncio de Jobs); un steer aceptado se guarda y sale como `chat.user_message` (voz); el supervisor pasa `DRAKTER_VOICE_<CAMPO>` leídos de `voice/config.py` y `DRAKTER_VOICE_PIPECAT_LOG`; layer0 de fuente única (TOML); auditoría real de la voz.
  6. Escritorio: switch de loopback en `npm run dev` (argv tras `--`) y `appendSwitch` de respaldo; etiqueta de bandeja Silenciar/Activar micrófono (canal `voice:mic-state`); `pc_id` se olvida ante cualquier rechazo; mensajes de voz por turno sin duplicar.
  7. `CAPABILITIES.md` decía que Drakter no trabaja en segundo plano: corregido. `VOICE.md` gana reglas de enrutado a `jobs_*` (eval `jobs_routing` 13/26 → 26/26).
  8. Eval `jobs_routing`: ejecutor nuevo `agent/evals/jobs_routing.py` (prompt = `SOUL.md` real del home de Hermes; `jobs_status` falso con UUID; hasta 4 rondas). Resultado 26/26 con `claude-haiku-5-5`.
  Además: `python -m voice phrases` toma `FISH_API_KEY` de `~/.config/drakter/.env`; borrados los eventos `voice.*` antiguos del contrato y `/tmp/dr-at` (574 MB, nada lo referenciaba).
- **Alternativas descartadas:** probar con voz real del usuario en esta pasada (no disponible: se anota como pendiente); micrófono simulado sin pasar por el bucle acústico (el bucle altavoz→micro llega a ~−28 dBFS, demasiado débil para el VAD, por eso se mezcla una fuente virtual con el micrófono real).
- **Motivo:** dejar la voz v2 funcionando de extremo a extremo en la app integrada con lo comprobable sin el usuario.
- **Impacto:** `voice/`, `backend/app/integrations/voice/`, supervisor y `main.py`, `desktop/electron/`, `agent/evals/jobs_routing.py`, `VOICE.md`, `CAPABILITIES.md`; Checklists 3, 13 y 14 (`IMPLEMENTATION_STATUS.md`). Pendientes ⚠️ en `RUN_STATE.md`.

## [2026-11-14] WP9: cifras medidas y umbrales
- **Contexto:** primera medición en la máquina de desarrollo (i7-8665U, 14 GB, sin GPU) con la app integrada.
- **Decisión:** cifras medidas (sin extrapolar):
  - Arranque en frío: pipeline de voz listo ~4,3 s; Hermes listo ~4,5 s.
  - Fin de voz → turno cerrado (endpointing): 375-388 ms con frase única; 1,2-2,3 s en otras (Smart Turn esperando). Smart Turn v3.2 devuelve COMPLETE en 92-145 ms.
  - STT final tras el fin de voz: 98-302 ms (Moonshine small).
  - Primer audio tras callar el usuario (`total_ms`, normalmente el acuse): 2,36-2,88 s.
  - Fish TTFA 0,71-0,96 s (picos de 1,1-1,6 s); Kokoro TTFA 0,72 s.
  - Haiku, primer delta (`voice_agent_ttft`): 0,93-8,0 s; típico 1,8-4,2 s (más con herramientas).
  - Super+J / `drakter activate` → modo conversación ~0,29 s. Barge-in: interrupción ~170 ms tras la transcripción final de «para», audio apagado ~0,66 s después; 83 s de TTS con micrófono abierto, 0 falsas interrupciones y 0 falsos duckings.
  - CPU (top, 8 hilos): voz en conversación media 79 % de un núcleo (p90 130 %, pico 425 % al cargar modelos); en reposo ~53 % de un núcleo constante (silencio continuo del mixer + Opus + openWakeWord); backend ~1 %; runners Hermes ~0,5 %; Electron ~24 %.
  - RAM (RSS): voz ~990 MB; backend ~110 MB; Hermes primer plano ~230 MB; Hermes w1 ~188 MB. Trabajo simple en w1 ~7 s.
  Umbrales **sin cambios**: `filler_after_ms` 1200, `wake_threshold` 0.3, `turn_stop_secs` 3.0, `followup_s` 20, `bargein_decide_ms` 700, `bargein_min_words` 3, `duck_gain` 0.25.
- **Alternativas descartadas:** mover umbrales con estas cifras: se midió con voz sintética y un bucle acústico débil, y no hay datos que justifiquen un cambio (p. ej. `filler_after_ms` 1200: el acuse suena antes que la respuesta casi siempre, con TTFT típico de 2-4 s). Reducir ya el CPU en reposo: se deja para otra fase.
- **Motivo:** no calibrar sobre una voz que no es la del usuario; la calibración fina queda pendiente con su voz real.
- **Impacto:** Checklist 14 («umbrales calibrados con cifras medidas»: cifras medidas, umbrales intactos); `voice/README.md`, `docs/usage/voz.md`, `README.md`, `docs/installation/voz.md`. Optimización del CPU en reposo (~53 %): Checklist 17.

## [2026-11-14] WP9: sin instalaciones de terceros nuevas
- **Contexto:** cierre de la integración de la voz v2.
- **Decisión:** WP9 no instala ni copia nada de terceros; usa el venv de voz, los modelos locales y las dependencias ya registradas (Pipecat 1.16.0, openWakeWord 0.4.0, Moonshine, Silero, Smart Turn v3.2, Kokoro, Fish Audio).
- **Alternativas descartadas:** ninguna.
- **Motivo:** no hacía falta.
- **Impacto:** ninguno en `THIRD_PARTY_NOTICES.md`.

## [2026-11-20] Voz: diagnóstico del STT y STT en la nube con respaldo Moonshine
- **Contexto:** el usuario probó la voz con su micrófono (Trust Headset USB mono): «Jarvis» → «y ya revish», «Drakter» → «dractead», STT «pésimo». Había que saber si el fallo era del audio o del modelo.
- **Decisión:** diagnóstico con voz sintética (Kokoro, frases con Drakter, Jarvis, Imanol, Magaña) pasada por una fuente virtual de PipeWire y capturada por Chromium (Electron) con y sin NS/AGC/AEC, y luego por WebRTC/Opus y el remuestreo 48k→16k de Pipecat (volcado del proceso real). Resultado, con WER y aciertos de nombres propios:
  | audio | Moonshine small | Moonshine tiny | faster-whisper small + léxico |
  |---|---|---|---|
  | limpio (24 frases) | 10,3 % · 16/40 | 11,5 % · 15/40 | 1,6 % · 36/40 |
  | Chromium sin procesar | 9,7 % · 12/34 | 10,2 % · 13/34 | 1,8 % · 30/34 |
  | Chromium NS+AGC+AEC | sin cambio medible (la diferencia era un corte vacío) | | |
  La cadena no degrada: AGC sube −40 dBFS a ~−23 dBFS (un pico a 0 dBFS en la primera frase, 0,003 % de muestras recortadas), NS baja el ruido de −55,6 a −73,7 dBFS, y lo que entra al STT tras WebRTC está a 16 kHz, ~−28 dBFS, sin recorte. **El problema es el modelo**: Moonshine falla sobre todo en nombres y no admite léxico. Se añade:
  1. `voice/providers/stt/cloud.py`: `stt = "auto"` (por defecto) elige Deepgram si hay `DEEPGRAM_API_KEY`, si no Groq si hay `GROQ_API_KEY`, si no Moonshine; `DRAKTER_VOICE_STT=deepgram|groq|moonshine` lo fuerza. Deepgram: `DeepgramSTTService` Nova-3, `language=es`, `keyterm` = `stt_keyterms`, `mip_opt_out=True` (fuera del programa de mejora del modelo), `base_url="api.eu.deepgram.com"` (región UE). Groq: `GroqSTTService` (`whisper-large-v3-turbo`, por tramos de VAD, `language=es`, prompt con el léxico, `finalized=True` en cada tramo, comprobación de la clave al arrancar). Nombres verificados en Pipecat 1.16.0.
  2. Respaldo: `ServiceSwitcher[nube, Moonshine]` con `SttFailover`: cualquier error del servicio en la nube (red, 401, cuota) pasa a Moonshine para el resto del proceso, con un único aviso `voice.error{code:"stt_fallback", stage:"stt"}`. Comprobado con claves falsas de Deepgram (401 al conectar) y Groq (`AuthenticationError` al arrancar): conmuta antes de hablar y transcribe con Moonshine. La clave sale `[REDACTED]` en el log.
  3. Volcado opcional `DRAKTER_VOICE_DUMP_AUDIO=1` (`voice/diagnostics.py`): wav por turno tal como entra al STT y `.json` con niveles (RMS, pico, % recorte, DC), en `~/.local/share/drakter/voice/dumps/` (0700/0600), borrado a las 24 h. Única excepción a «ni audio ni transcripciones se guardan», desactivada por defecto.
  4. Palabra de activación: `strip_wake_word` une hasta tres palabras y compara con clave fonética (j/ll/y→y, v→b, sh/z→s, sin h ni letras dobles) y distancia de edición ≤ 1 a «jarvis» (5+ letras). Acepta «y ya revish», «ya revish», «llarvis», «harvis»; 0 falsos positivos en 18 frases normales («y ya está», «ya veremos», «y a ver si…»).
  Con la clave real de Deepgram del usuario, 5/5 frases perfectas (nombres incluidos) y STT final 5-50 ms tras el fin de voz (Moonshine: 300-600 ms).
- **Alternativas descartadas:** quitar NS/AGC de Chromium (no degradan y el AGC ayuda con un micro bajo); whisper local (RTF ~1 en esta CPU: 3,5-4 s por frase); Moonshine con otro tamaño (tiny es peor).
- **Motivo:** el usuario necesita que entienda nombres propios; la nube con léxico lo resuelve y Moonshine queda como red de seguridad sin red.
- **Impacto:** `voice/providers/stt/cloud.py`, `voice/diagnostics.py`, `voice/config.py` (`stt`, `stt_keyterms`, `stt_deepgram_*`, `stt_groq_model`, `dump_audio`), `voice/registry.py` (`auto`, `deepgram`, `groq`), `voice/pipeline.py`, `voice/bridge.py`, `layer0.es.toml`, supervisor (`VOICE_SECRETS` + `DEEPGRAM_API_KEY`, `GROQ_API_KEY`), `.env.example`, lock de voz. Checklist 14.

## [2026-11-20] Voz: fin de turno con umbral de Smart Turn, regla de texto y margen
- **Contexto:** «en el mundo de la…» se envió cortado. Cadena: VAD Silero `stop_secs` 0,2 → Smart Turn v3.2 (umbral fijo 0,5 en Pipecat) → `wait_for_transcript` → `turn_final_timeout_s`.
- **Decisión:** medido sobre 80 cortes a mitad de frase (límites de palabra de whisper) y 10 frases completas: Smart Turn da «completo» al 81 % de los cortes con 0,5 (59 % aún con 0,9) y a todas las completas (p ≥ 0,92). Se añade `DrakterTurnStop` (`providers/turn/smart_turn.py`): umbral `turn_complete_threshold` 0,7, y antes de cerrar exige un silencio total que depende del caso: 0,2 + `turn_grace_s` 0,5 = 0,7 s si el texto no cuelga; `turn_hanging_secs` 2,0 s si acaba en preposición, artículo, conjunción o coma («… de la», «… y»); `turn_stop_secs` 3,0 s si Smart Turn dice incompleto. Con umbral 0,7 + texto colgante los cortes que cierran turno bajan de 81 % a 29 %, sin retener ninguna completa (los que quedan son frases con sentido completo, p. ej. «Drakter apunta una tarea»).
  De punta a punta (proceso real, WebRTC, Moonshine), `eot_ms` (fin de VAD → cierre) pasa de ~224 ms a ~504 ms; `endpointing_ms` de `metrics.jsonl` sigue en 200 (es el VAD). Frase con pausa de 1,2 s tras «… en el mundo de la»: un turno antes y después (con voz sintética Smart Turn ya la veía incompleta; con la del usuario no, y ahí entra la regla de texto). Frase completa + pausa de 0,6 s + continuación: antes 2 turnos; ahora en el límite (1 turno en 1 de 3 ejecuciones: con el silencio que añade Kokoro la pausa real ronda los 0,7 s). Pausa de 0,9 s tras oración completa: sigue partiendo (el backend lo trata como `steer` del turno en curso); se sube con `turn_grace_s` en `voice.toml` a costa de latencia.
  Fallo del puente encontrado al probar con Deepgram: si su respuesta a `Finalize` llega vacía (ya mandó el texto como `is_final`), no hay `TranscriptionFrame(finalized)`; el puente esperaba 1 s y, si el usuario volvía a hablar antes, `_on_user_started` **tiraba el turno pendiente con su texto** (se perdía «Quiero contarte que en el mundo de la… novedades»). Ahora el texto pendiente pasa al turno nuevo (la pausa queda en un solo turno) y, con texto pero sin `finalized`, el puente espera solo `turn_final_grace_s` 0,3 s.
- **Alternativas descartadas:** solo subir el umbral (no basta: 59 % con 0,9); `stop_secs` del VAD más alto (Smart Turn asume 0,2); un margen de 1 s en todos los turnos (+0,8 s de latencia siempre).
- **Motivo:** una pausa para pensar no debe cerrar el turno, con el menor coste de latencia posible (+0,28 s).
- **Impacto:** `voice/providers/turn/smart_turn.py`, `voice/bridge.py`, `voice/config.py` (`turn_complete_threshold`, `turn_grace_s`, `turn_hanging_secs`, `turn_final_grace_s`). Calibración fina con la voz real del usuario pendiente.

## [2026-11-20] Voz: nunca dos respuestas a la vez; el acuse se corta con el audio real
- **Contexto:** «a veces responde dos cosas a la vez o termina mal». En `backend.log` del 20-11 (18:15:23 y 18:15:24, 18:15:39 y 18:15:43) hay dos turnos de voz seguidos sin ninguna interrupción entre ellos: un turno partido en dos. El backend solo manda `speak.stop{new_turn}` si le consta que el bot habla (`voice.playback started`), y eso llega tarde (TTFA de Fish ~0,8 s); la respuesta nueva se abría con la anterior aún sonando. Fish asigna el audio que recibe al contexto activo (`get_active_audio_context_id`), así que dos respuestas seguidas comparten WebSocket y se mezclan. Reproducido con el proceso real: antes `101 started → 101 finished → 102 started` (la 1 entera y la 2 detrás).
- **Decisión:** el puente de voz corta en `speak_open` el tramo anterior si sigue abierto, pendiente o sonando (`Session.speech_playing`, que mantiene el `PlaybackTracker`) con `interrupt("new_turn")`; ahora `101 started → 101 interrupted → 102 started → 102 finished`. El acuse (`ack_*`, `tool_generic`) se emite a ritmo real en trozos de 100 ms con 0,3 s de adelanto y se corta en cuanto llega `TTSStartedFrame`/`TTSAudioRawFrame` de la respuesta (log `filler_cut`); antes se encolaba entero y retrasaba la respuesta. Una interrupción por turno nuevo no cancela el acuse ya armado para ese turno.
- **Alternativas descartadas:** `speak.stop` incondicional en el backend (cancelaría el acuse del turno nuevo y no cubre los turnos escritos ni los encolados); cola de respuestas (el usuario ya ha pasado a lo siguiente).
- **Motivo:** el proceso de voz es el único que sabe qué está sonando de verdad.
- **Impacto:** `voice/bridge.py`, `voice/session.py`, `voice/speech/playback.py`, `voice/speech/phrases.py`.

## [2026-11-20] Identidad en voz según la conversación real (PR #17)
- **Contexto:** en voz el agente se negó a decir «una frase muy larga», insistía en ofrecer agenda y tareas, usaba «la guarida» y corregía «Jarvis».
- **Decisión:** en voz, la petición explícita del usuario sobre longitud o contenido gana a la brevedad, sin comentarlo; no se ofrece la agenda, las tareas ni las asignaturas sin motivo; nada de dragón ni «guarida» en voz (`VOICE.md`, `SOUL.md`, `PERSONALITY.md`); «Jarvis» es la palabra de activación y no se corrige; lo que no puede hacer se dice en una frase, sin listas de capacidades. Eval nueva `agent/evals/voice_behavior.py` (5 casos, Haiku): 3/5 antes, 5/5 después.
- **Alternativas descartadas:** cambiar la personalidad de fondo (la personalidad Jarvis sigue pendiente de que la elija el usuario).
- **Motivo:** lo que pide el usuario manda sobre el estilo por defecto.
- **Impacto:** `agent/identity/VOICE.md`, `SOUL.md`, `PERSONALITY.md`, `agent/evals/voice_behavior.{py,jsonl}`. El PR #19 no toca `agent/identity/` (sus cambios propios se retiraron: con `voice_behavior.py` el caso «Hey Jarvis, ¿qué hora es?» empeoraba).

## [2026-11-20] Selector de salida de audio en el escritorio (PR #16)
- **Contexto:** el usuario usa un headset USB y la voz debe sonar por el dispositivo que elija, no siempre por el predeterminado.
- **Decisión:** selector de salida en Ajustes → Voz con `HTMLMediaElement.setSinkId` sobre el `<audio>` remoto de WebRTC, persistido en las preferencias del escritorio, con tono de prueba y aviso con los dispositivos elegidos (`desktop/src/voice/audioOutput.ts`, `VoiceSection.tsx`, `stores/preferences.ts`, `webrtcClient.ts`).
- **Alternativas descartadas:** cambiar el dispositivo predeterminado del sistema desde la app (afecta a otras aplicaciones).
- **Motivo:** elegir micrófono y salida desde Drakter sin tocar el sistema.
- **Impacto:** `desktop/src/voice/`, `desktop/src/settings/VoiceSection.tsx`, `desktop/src/stores/preferences.ts`.

## [2026-11-20] Voz: dependencia nueva `deepgram-sdk` 7.19.0
- **Contexto:** el STT de Deepgram de Pipecat 1.16.0 necesita el extra `deepgram` (`deepgram-sdk<8,>=6.1.1`). Groq usa el cliente `openai`, ya instalado (no hace falta el extra `groq`).
- **Decisión:** `pipecat-ai[webrtc,fish,kokoro,deepgram]==1.16.0`; el lock añade `deepgram-sdk==7.19.0`, `httpx==0.28.1` y `httpcore==1.0.9` sin mover ninguna otra versión. Se instala con `scripts/install-voice.sh`. Para el diagnóstico se usaron venvs aparte (`venvs/voice-vq`, `venvs/stt-bench` con `faster-whisper==1.2.1`), fuera del runtime.
- **Alternativas descartadas:** cliente WebSocket propio para Deepgram (Pipecat ya lo trae, con `Finalize` y reconexión).
- **Motivo:** reutilizar el servicio de Pipecat verificado.
- **Impacto:** `voice/pyproject.toml`, `voice/requirements.lock`, `THIRD_PARTY_NOTICES.md`.

## [2026-11-20] Palabras de activación propias en es-ES («Jarvis», «Drakter», «despierta») (PR #20)
- **Contexto:** `hey_jarvis_v0.1` (inglés) detecta mal la voz castellana. Hay que poder entrenar modelos propios compatibles con `openwakeword==0.4.0` y activarlos con `DRAKTER_VOICE_WAKE_MODELS` sin tocar el código de voz.
- **Decisión:** kit en `tools/wakeword/`: un cuaderno de Colab (GPU) con la receta oficial de openWakeWord (`automatic_model_training.ipynb` + `train.py`: clips de 2 s, DNN con entrada `(1,16,96)`, ejemplos difíciles, rampa del peso de negativos, ONNX opset 13), y un modelo por palabra (`jarvis_es`, `drakter_es`, `despierta_es`).
  - **Positivos:** se sintetizan con `piper-tts==1.8.0` (voces `es_ES`: carlfm, davefx, mls_9972, mls_10246 y sharvard ×2) y `kokoro-onnx==0.6.1` (`ef_dora`, `em_alex`, `em_santa` y mezclas de estilos). Piper hace el 65 % de los clips porque es ~5× más rápido en CPU.
  - **Negativos:** voz castellana real de MLS (split `train`), AudioSet, frases normales y palabras parecidas sintetizadas.
  - **Aumentación:** ruido de fondo con SNR aleatoria, RIR del MIT, ecualización y ganancia.
  - **Métricas:** FP/h contando activaciones (con 2 s de refractario) sobre MLS `test` (otros hablantes) y una parte reservada de AudioSet, más el recall.
  - **Embedding:** se usan el `melspectrogram.onnx` y el `embedding_model.onnx` **de la rueda `openwakeword==0.4.0`**, idénticos (sha256) a los de `~/.local/share/drakter/models/openwakeword/`. El `embedding_model.onnx` de la release v0.5.1, que descarga el cuaderno oficial, es otro archivo: con audio real sus salidas correlan ≈0,99 pero no coinciden, así que entrenar con él daría un desajuste respecto a lo que Drakter calcula.
  - **ACAV100M:** las 2000 h precalculadas (`davidscripka/openwakeword_features`, CC BY-NC-SA 4.0) quedan opcionales y apagadas (`USAR_ACAV`). Están calculadas con otro embedding y la licencia es no comercial: si se activan, el modelo es solo para uso personal.
  - **Fish:** no se usa (clave, red, modelo gratuito con caducidad).
  - **`tools/wakeword/grabar_muestras.py`:** graba muestras reales con `pw-record`/`arecord`, porque el sistema no tiene PortAudio y `sounddevice` no carga.
  - **Confirmación textual del puente:** `[wake].words` de `voice/conversation/layer0.es.toml` añade «drakter», «despierta» y las variantes que dio Moonshine `small-streaming-es` con 9 voces sintéticas (`dracter`, `draxter`, `dragter`, `drapter`, `tracter`…), y `lead` añade «venga». «tractor» y «carter» quedan fuera, por ser palabras reales que el STT también produce.
- **Fuentes y licencias (uso personal, nada se redistribuye ni se versiona):**
  - openWakeWord 0.4.0: Apache-2.0.
  - piper-tts: GPL-3.0, solo como herramienta en Colab.
  - Voces Piper: carlfm dominio público, davefx CC0, mls_* CC BY 4.0, sharvard CC BY 3.0.
  - Kokoro-82M: Apache-2.0.
  - MLS: CC BY 4.0.
  - AudioSet (`agkphysics/AudioSet`): CC BY 4.0, con audio de YouTube.
  - RIR del MIT: licencia no indicada en la copia de HF.
  - ACAV100M: CC BY-NC-SA 4.0, solo uso personal.
- **Alternativas descartadas:**
  - `piper-sample-generator`: solo inglés.
  - Usar el `embedding_model.onnx` v0.5.1 o ACAV100M por defecto: desajuste de embedding y licencia NC.
  - Un único modelo multiclase: openWakeWord 0.4.0 y la puerta trabajan con un modelo por palabra.
  - Comparación difusa nueva para «drakter»: la lista de variantes basta y no toca `bridge.py`.
- **Motivo:** que los modelos entrenados funcionen tal cual en el runtime de Drakter, con datos castellanos y licencias libres por defecto.
- **Impacto:** `tools/wakeword/**`, `docs/usage/palabras-activacion.md`, `docs/usage/README.md` y `voice/conversation/layer0.es.toml` (`[wake]`). Comprobado:
  - el cuaderno pasa nbformat y `ast`, y se ejecutó entero en CPU con pocas muestras (con 120 positivos el recall llega al 50-92 %);
  - `strip_wake_word` acierta los 24 casos (positivos y negativos);
  - `voice/conversation/check_conversation.py` da OK y `voice/tests/check_pipeline.py` da 21 PASS.
  - ⚠️ Sin ejecutar todavía en Colab con los valores reales, ni probado con la app.

## [2026-11-20] LAT-1: latencia del agente en voz (agente caliente, sin thinking en voz, hora en el turno, caché de 1 h)
- **Contexto:** en la app real, el primer fragmento de Hermes con Haiku 5.5 tardaba 1,8-4,2 s y era el cuello de botella de la voz. Se midió el desglose con el backend real (datos aparte, voz desactivada, turnos por REST con `[canal: voz]`), marcas en el runner y en el runtime, y Hermes b200f5b. Cifras en ms en el runner; el backend suma 30-40 ms.
  - **Antes** (`main`: un `AIAgent` por turno, thinking adaptativo `low`, venv sin `.pyc`, títulos de Hermes, caché de 5 min; 10 turnos): primer turno en frío 1593-2370, con 1050-1450 de preparación dentro de Hermes. Sin herramientas 622-649. Con herramienta 1725-3867, y la hora en 1773-2426. Desglose de un turno con herramienta: `build_agent` 15-31; preparación hasta la petición 146-261; cabeceras de Anthropic 400-540; el modelo genera la llamada (con thinking) 250-1360; herramienta 50-80; Hermes entre iteraciones 60-160; 2.ª petición 380-600; thinking antes del texto 0-810. La caché funcionaba: ~62K tokens leídos desde el 2.º turno.
  - **Después** (13 turnos): primer turno en frío 1138-1258, con ~440 de preparación. Sin herramientas 537-747. Con herramienta 593-810, porque sale antes una frase breve («Voy a mirarlas.»); un caso sin esa frase, 1773. El turno completo con herramienta pasa de 1,9-3,9 s a 1,8-2,5 s. La hora, 672 y sin herramienta. `build_agent` 0 en caliente; preparación 136-309. Tras una pausa de 370 s: 127.935 tokens leídos de caché y 736 escritos. Hermes listo al arrancar en 7,2 s (antes 11,8 s).
  - **Mejora:** primer delta con herramienta de ~2,4 s a ~0,7 s (mediana, −1,6 s). Hora de 1,8-2,4 s a 0,67 s. Primer turno en frío, −0,5 a −1,1 s. Sin herramientas, ~−50. Pausa de más de 5 min: se evita reescribir 62K tokens (cabeceras ~830 frente a ~450, −0,4 s).
- **Decisión:**
  1. **Agente caliente** (runner): tras un turno `completed` sin interrupción se conserva el `AIAgent` y se reutiliza si coinciden `session_id` e `instructions`, igual que la caché de agentes del gateway de Hermes. Tras una cancelación, un fallo o una excepción se cierra. El `usage` es la diferencia de los `session_*` del turno. Ahorra ~20 de construcción y ~60-100 de preparación por turno; no era el cuello de botella.
  2. **Sin thinking en voz:** `TurnRequest.source` llega al runner como `reasoning_effort: "none"` solo en turnos de voz (`HermesProvider.VOICE_REASONING_EFFORT`). El texto mantiene `low` y los trabajos, `medium`. Alternar texto y voz en una sesión funciona; solo se reescribe la caché de los mensajes (~12K tokens) y el sistema y las herramientas siguen en caché. Revierte el «effort por canal» descartado en V-38, ahora con cifras.
  3. **Hora local en el prefijo del turno** (`[ahora: viernes 20 de noviembre de 2026, 19:51 (Europe/Madrid)]`, de `default_timezone`): sin thinking, el modelo a veces se inventaba la hora en lugar de llamar a `get_system_status`, que además da UTC. Va en el `turn_prompt`, así que la caché no cambia.
  4. **Home:** `prompt_caching.cache_ttl: "1h"` (escribir cuesta 2× en vez de 1,25×, pero las pausas habituales en voz ya no obligan a reescribir el prefijo) y `auxiliary.title_generation.enabled: false` (una llamada a Haiku por sesión que competía con el primer turno, y Drakter no usa ese título).
  5. **`scripts/install-hermes.sh`:** `uv sync --compile-bytecode` y `compileall` del clon. El runner corre con `-B` y, sin `.pyc`, recompilaba `openai` y `anthropic` en cada primer turno (`compile()` ~1,15 s en el perfil). En el venv ya instalado se ejecutó `compileall` a mano.
  6. Por turno: una línea `drakter_runner: timing …` en `hermes.log`, y `first_delta_ms`, `total_ms` y `usage_*` en `turn_finished` de `backend.log`.
- **Evals con `claude-haiku-5-5`** (sin thinking, tal como queda la voz, frente a thinking `low`, la configuración de antes, con un envoltorio local que añade `thinking`/`output_config.effort`): `jobs_routing` 26/26 frente a 26/26; `voice_behavior` 5/5 frente a 5/5 (otra pasada sin thinking dio 3/5: es variable); `seleccion` 13/19 frente a 11/19 (los fallos son sobre todo `style.too_long` en texto; los de herramientas, 3 frente a 3); `encadenadas` 9/11 frente a 9/11. Sin thinking no empeora el uso de herramientas. `PREFLIGHT OK` con el agente caliente (historial, `system` y herramientas idénticos entre turnos, `steer`, `hard_interrupt`) y las comprobaciones del CI del backend en verde.
- **Alternativas descartadas:** (d) menos herramientas en voz: con caché caliente, 78 herramientas (45K tokens) dan un primer token de 411-935 y 15 herramientas (28K), 742-835; el tamaño no influye y domina el ruido de red. (e) Precalentar al activar la voz: Hermes no tiene forma de calentar la caché sin una petición de pago. Con el TTL de 1 h la caché casi siempre está caliente, y el agente caliente conserva su cliente HTTP. Importar al arrancar los 136 módulos perezosos del primer turno (~0,5 s) ataría el runner a nombres internos de Hermes. Thinking desactivado también en texto: nadie lo pidió y el texto no tiene la presión de la voz.
- **Motivo:** bajar el primer fragmento hablado sin tocar la seguridad ni las herramientas.
- **Impacto:** `backend/app/integrations/hermes/` (`runner/drakter_runner.py`, `runtime.py`, `provider.py`, `hermes_provider.py`, `supervisor.py`, `home.py`, `CONTRACT.md`) y `scripts/install-hermes.sh`. No se toca `voice/` ni `agent/identity/`. Checklist 17 (latencia del agente medida).

## [2026-11-20] Boca sincronizada y Rive: nivel de audio en el renderer, `@rive-app/canvas` y respaldo SVG
- **Contexto:** `setMouth` no hacía nada y el backend no publica `voice.playback_level`. Hay que mover la boca con el audio real y dejar lista la integración de Rive para cuando el usuario entregue el `.riv`.
- **Decisión:** (1) `voice/outputLevel.ts` mide el RMS con un `AnalyserNode` sobre la pista remota de WebRTC (umbral de silencio, curva perceptual, ataque/relajación, ~30 fps con `setInterval`); sin suscriptores no hay `AudioContext` ni temporizador, y el analizador no va al destino. `webrtcClient.ts` solo anuncia la pista (`setOutputStream`). `useMouthLevel` se suscribe solo en `speaking` y sin movimiento reducido (ajuste de la app o del sistema); el rig usa el nivel en lugar de su generador aleatorio (`Rig.setMouthLevel`). (2) `RiveCharacter` usa `@rive-app/canvas` 2.53.0 (MIT) fijado, con el wasm local (`?url`, CSP ya prevista con `wasm-unsafe-eval`). Contrato: state machine `Drakter` con inputs numéricos `state` (0..8) y `mouthOpen` (0..1). `AdaptiveCharacter` descarga el `.riv` y cae al SVG si falta o falla. (3) El proceso principal sirve el `.riv` del usuario en `app://drakter/__character/drakter.riv` desde `~/.local/share/drakter/character/drakter.riv` o `DRAKTER_CHARACTER_RIV`: una ruta fija, solo archivos `.riv`; el renderer no lee el disco.
- **Alternativas descartadas:** `@rive-app/react-canvas` (solo envuelve el runtime y añade una capa); consumir `voice.playback_level` (el backend no lo publica y añadiría latencia); `requestAnimationFrame` para medir (se pausa en segundo plano y ata el nivel al render); view models de Rive en lugar de inputs (más complejos de diseñar, migración posible).
- **Motivo:** la boca depende de lo que suena de verdad, sin tocar la conexión de voz ni el backend, y el `.riv` se enchufa sin cambiar el resto.
- **Impacto:** `desktop/src/character/**`, `desktop/src/voice/{outputLevel,webrtcClient}.ts`, `desktop/electron/main/rendererProtocol.ts` (ruta del `.riv`, fuera de la zona nominal pero necesaria), `desktop/package.json`, `THIRD_PARTY_NOTICES.md`, `docs/usage/personaje.md` (sustituye a `character/rive.md`). Checklists 5 y 14. «Crear proyecto Rive» sigue pendiente del usuario.

## [2026-11-20] Rive: verificación con un .riv real, CSP sin cambios y avisos en el log
- **Contexto:** la primera prueba de Rive solo cubrió un `.riv` inválido (cae al SVG). Quedaba por confirmar que el wasm compila bajo la CSP del renderer y que un fallo no es silencioso.
- **Decisión:** (1) La CSP compartida (`electron/shared/csp.ts`) ya incluía `'wasm-unsafe-eval'` en `script-src` (y no `'unsafe-eval'`): no se cambia. Se probó en Electron sin pantalla con el protocolo `app://` y la CSP reales y `rating.riv` (rive-app/rive-react, MIT, descargado solo en local, no versionado): se renderiza Rive (`<canvas>`), `state` pone 0/2/3/6/8 en `idle`/`thinking`/`speaking`/`error`/`offline` y `mouthOpen` sube hasta ~1 con un tono por un bucle WebRTC real y vuelve a ~0 en silencio (el archivo de prueba solo trae un input `rating`; se renombraron los inputs en el banco de pruebas, no en el código). Con ese mismo archivo sin la state machine `Drakter` se cae al SVG. (2) Los fallos de carga (HTTP distinto de 404, archivo vacío, error de Rive, excepción al arrancar, falta de state machine) hacen `console.warn('[drakter:personaje] …')`; `electron/main/window.ts` reenvía esas líneas al log con `logError('personaje', …)`. La ausencia de archivo (404) no avisa: es el caso normal.
- **Alternativas descartadas:** añadir `'unsafe-eval'` (no hace falta); canal IPC dedicado para el log (la consola del renderer basta).
- **Motivo:** que Rive no falle en silencio y sin ampliar la superficie de la CSP.
- **Impacto:** `desktop/src/character/{log,AdaptiveCharacter,RiveCharacter}.ts(x)`, `desktop/electron/main/window.ts`.

## [2026-11-20] Lanzamiento: backend empaquetado autosuficiente e instalador del AppImage sin sudo
- **Contexto:** el backend congelado resuelve su `REPO_ROOT` como el padre de `_internal` (`resources/backend/`). Ahí busca `agent/` (identidad, `permissions.json`), `voice/` (lo ejecuta el venv de voz con `-m voice`, cwd = `REPO_ROOT`) y `tools/catalog.json`, y necesita el runner de Hermes como archivo. Nada de eso iba en el paquete. Además, el lector aislado del almacén se relanza como `sys.executable -B -m app.services.readers.worker`, y en un binario PyInstaller eso arrancaba otro servidor. En esta máquina, Ubuntu 24 no trae `libfuse2` (el AppImage no se monta) y AppArmor restringe los user namespaces.
- **Decisión:**
  1. Arreglarlo solo desde el empaquetado, sin tocar `backend/app`. `electron-builder.yml` copia `agent/` (sin `evals/`), `voice/` (sin `tests/`) y `contracts/tools/catalog.json` a `resources/backend/`. El `.spec` mete el runner y `pyproject.toml` en el bundle y carga `electron-builder.rthook-module.py`, que ejecuta `drakter-backend [-B|-I…] -m <módulo>` con `runpy`. Gracias a eso, la CLI de copias también va en la app instalada.
  2. `scripts/install-appimage.sh` **extrae** el AppImage en `~/.local/opt/drakter/app` en lugar de ejecutarlo. Así no hace falta FUSE y la ruta es estable para un perfil AppArmor. Crea `~/.local/bin/drakter-app`: quita `ELECTRON_RUN_AS_NODE` y pasa `--allow-loopback-in-peer-connection`, que necesita la voz. Crea también `drakter.desktop` (con `desktopName` en `extraMetadata`). Comprueba Hermes, el venv y los modelos de voz, el `.env` (solo si existe, sus permisos y si cada clave tiene valor; nunca imprime nada) y el sandbox. Con `--runtimes` llama a `install-hermes.sh` e `install-voice.sh`.
  3. Si los user namespaces están restringidos, el instalador escribe un perfil AppArmor (`userns,` solo para `~/.local/opt/drakter/app/drakter`) y da el único comando con sudo para instalarlo. Nunca `--no-sandbox`.
  4. `scripts/package.sh` encadena los tres pasos con `TMPDIR` en disco (`~/.cache/drakter-build/tmp`), porque fpm llenaba el `/tmp` tmpfs. `electron-builder@26.18.0` se sigue llamando por `npx`, para no añadir ~300 paquetes al lock.
- **Alternativas descartadas:** cambiar las rutas en `backend/app` (fuera de la zona; la raíz empaquetada ya es coherente); ejecutar el AppImage montado (sin `libfuse2`, y el punto de montaje `/tmp/.mount_*` cambia en cada arranque); `APPIMAGE_EXTRACT_AND_RUN=1` como camino normal (extrae en cada arranque); empaquetar los venvs y los modelos (~2 GB, ligados al Python del sistema y a `uv`).
- **Motivo:** que el AppImage funcione de verdad (agente, voz y almacén) y se instale sin sudo.
- **Impacto:** `desktop/electron-builder.{yml,backend.spec,rthook-module.py,README.md}`, `scripts/{package,install-appimage}.sh`. Checklist 17 «Crear instalador».

## [2026-11-20] Actualización: `scripts/update.sh` por git; `electron-updater` descartado
- **Contexto:** el repositorio es privado y hay un solo usuario. La app depende de runtimes fuera del paquete (venvs de voz y Hermes, modelos) y de migraciones de SQLite.
- **Decisión:** `scripts/update.sh [--package] [--no-restart]` hace, por orden:
  1. Se niega si el árbol tiene cambios.
  2. `git pull --ff-only`, con las credenciales de git del usuario.
  3. Solo lo que cambió entre el HEAD viejo y el nuevo (o lo que falte): `uv sync --locked`, `npm ci`, `install-voice.sh` (si cambian `voice/requirements.lock`, `voice/pyproject.toml` o `contracts/python`) e `install-hermes.sh`. Después, `npm run build`.
  4. Para la app de `drakter-local.sh`.
  5. Copia con la CLI. Si la copia falla, no migra; si no hay base, no copia.
  6. `migrate`. Si la base está en uso por otra instancia, avisa de que se migrará, con copia `pre-migrate`, al reabrir.
  7. Vuelve a arrancar lo que paró (`DRAKTER_PROVIDER`, por defecto `anthropic`).
  `--package` reconstruye y reinstala el AppImage.
- **Alternativas descartadas:** `electron-updater` con releases privadas de GitHub. Obliga a guardar en la app un token con acceso al repositorio (`private: true` + `GH_TOKEN`), lo que choca con «secretos fuera de la app». Además solo actualiza el AppImage (no el `.deb`, los venvs, los modelos ni Hermes) y aplicaría migraciones sin copia previa explícita. Un servidor de actualizaciones propio sería excesivo para un solo usuario.
- **Motivo:** el mecanismo más simple que funciona con un repositorio privado.
- **Impacto:** `scripts/update.sh`, `docs/usage/copias-y-actualizacion.md`, `desktop/electron-builder.README.md`. Checklist 17 «Crear actualización de aplicación». ⚠️ El reinicio con `drakter-local.sh` no se ha probado, para no tocar la app del usuario.

## [2026-11-20] Skills de solo lectura compiladas en SOUL.md
- **Contexto:** las Skills de `agent/skills/` estaban inertes porque el toolset `skills` de Hermes v0.22.7 trae `skill_manage` junto a `skills_list` y `skill_view` («Skills de agent/ inertes en Hermes»). En `b200f5b`, Hermes solo excluye toolsets enteros (`disabled_toolsets` en `model_tools._select_tool_names`), no herramientas sueltas. Activar el toolset metería además el índice nativo de Skills, la sincronización de Skills incluidas y el hub.
- **Decisión:** `home.py` (`render_skills`) compila `agent/skills/<nombre>/SKILL.md` al final de `SOUL.md`, detrás de las reglas de seguridad y la identidad. Solo admite carpetas reales con nombre `^[a-z][a-z0-9-]{2,47}$`, `SKILL.md` regular sin symlink de como mucho 6000 caracteres y `name` del frontmatter igual a la carpeta. `drakter-basics` va primero y el resto por nombre. Un preámbulo fijo dice que son de solo lectura y que mandan las reglas de seguridad. El toolset `skills` sigue apagado. `SOUL.md` ya está en el manifiesto con su hash y se verifica antes de cada arranque. El preflight comprueba además que no hay herramientas `skill_*` y que las Skills están en el prompt. Se reescriben las 10 Skills con herramientas y campos reales del catálogo: `drakter-basics` es la primera, recoge las reglas comunes y absorbe `system-status`, que se elimina. `configuration` deja de citar herramientas PROPUESTA y usa las que existen (voz, estado y propuesta de mejora).
- **Alternativas descartadas:** activar `skills` y quitar `skill_manage` en el runner (depende de internos de `AIAgent`, choca con `checked_tools` y deja el índice nativo apuntando a una herramienta ausente); una herramienta MCP `get_skill` (es una herramienta nueva y añade una ida y vuelta por turno, que penaliza la voz); un plugin de Hermes que registre la vista (más código dentro de Hermes).
- **Motivo:** es la vía más simple y segura. Las Skills son de solo lectura por construcción, no añade herramientas ni latencia, y el prefijo sigue en caché (unos 16 KB más en `SOUL.md`, que pasa de ~52 KB a ~68 KB y sigue por debajo de los 120 KB del tope).
- **Comprobación:** preflight OK, con hash del system idéntico entre turnos y `SOUL.md` idéntico entre generaciones. Entre arranques cambian la línea `Conversation started` y el Session ID que añade Hermes. Con Claude Haiku 5.5 real, 8 turnos y 19 llamadas, desde un backend propio del worktree: usó la herramienta de cada dominio en el orden de su Skill (`check_availability` antes de `create_event`, `complete_task` en vez de editar, `delete_task` → `confirmation_required`, `search_resources` → `read_resource`, `propose_memory` pendiente) y se negó a crear o modificar Skills.
- **Impacto:** revoca «Skills de agent/ inertes en Hermes». Afecta a `backend/app/integrations/hermes/home.py` y `preflight.py`, a `agent/skills/**` y a las Checklists 3, 12 y 13. Editar una Skill cambia el hash de `SOUL.md` y, por tanto, el prefijo en caché: es un cambio de producción y pasa por revisión (CLAUDE.md §8).

## [2026-11-20] OPT-1: optimización de consultas SQLite, recuperación de memoria y carga de la interfaz
- **Contexto:** Checklist 17 pide «Optimizar consultas SQLite», «Optimizar recuperación de memoria» y «Optimizar carga de interfaz». Se midió con una base sembrada por la API (5.000 tareas, 200 proyectos, 3.000 eventos, 1.000 bloques, 40 hábitos con 14.600 registros, 3.000 relaciones y 3.000 recuerdos). Se capturó con `trace_callback` todo el SQL de 29 rutas y se pasó `EXPLAIN QUERY PLAN` a cada sentencia. Para comparar, el mismo banco se ejecutó sobre `f82dda9` y sobre la rama, tomando el mínimo de 15 repeticiones en dos rondas alternas, porque la máquina estaba cargada (load ~5 en 8 núcleos). En las rutas que no se tocan las cifras varían ±25 % por ruido; solo se citan cambios que superan ese margen.
- **Decisión:**
  1. **Migración `0015_query_indexes.sql`**, solo con índices:
     - `habit_records (occurrence_date)`, para «Hoy»: de 3,5 ms a 0,04 ms. Antes recorría la tabla entera.
     - `tasks (status, due_date)`, para los recordatorios de tareas con fecha sin hora: de 1,35 ms a 0,04 ms.
     - `memory_records (created_at, seq)` y `(status, created_at, seq)`, que sustituye a `(status)` (es su prefijo), para el listado de memoria: de 12,9 ms a 0,23 ms y sin B-tree temporal.
  2. **`relations.entities_by_ids`:** la etiqueta pasa a sacarse con una subconsulta correlacionada sobre `v_entity_labels` en lugar de `LEFT JOIN`. Con `LEFT JOIN`, SQLite materializaba la vista entera (las 9 tablas) en cada llamada; con la subconsulta empuja `id = ?` a cada rama del `UNION ALL` y busca por clave. Pasa de 15,7 ms a 0,3 ms con resultado idéntico, y relacionados baja de 12–14 ms a 8 ms por petición.
  3. **«Hoy»:**
     - `available_timezones()` se llamaba en cada petición (~25 ms recorriendo tzdata); ahora se llama una vez por proceso.
     - Las tareas que seguro no son de hoy se descartan en SQL: `due_at` con un día de margen y `due_date <= hoy`. Lo que no tiene forma ISO sigue llegando a Python, que lo cuenta como ilegible.
     - La ruta pasa de 62 ms a 41 ms. La salida es idéntica (mismo hash de JSON) en tres instantes distintos.
  4. **PRAGMA sin cambios.** WAL y `synchronous=NORMAL` ya estaban. El coste fijo de cada conexión es analizar el esquema en la primera sentencia (~2,3 ms). Fijar o leer `journal_mode` no lo cambia, y `cache_size` y `mmap_size` no ayudan con una conexión por petición (medido).
  5. **Memoria por turno:** `SqliteMemoryAdapter.search_with_text` devuelve la búsqueda y el texto del nivel en una consulta y una conexión. Antes eran 9 conexiones: una búsqueda y un `read` por recuerdo. Es una capacidad opcional del adaptador: el puerto `MemoryAdapter`, que está congelado, no cambia, y `memories_for_context` vuelve al camino anterior si el adaptador no la tiene. Usa los mismos filtros (`approved`, `valid_until`), el mismo orden bm25 y la misma auditoría `memory.search`. Pasa de 44–62 ms a 14–30 ms, con resultados idénticos en 18 consultas comparadas (6 textos × 3 niveles).
  6. **`build_context`:** los niveles 2-4 se cachean por identidad de archivo (`lstat`: modo, inodo, tamaño, mtime y ctime de los 14 archivos). La clave se toma antes de leer. Un symlink cambia el modo y deja de ser válido, la falta de una regla de nivel 2 lanza error en cada turno (los errores nunca se cachean) y los avisos de archivos ausentes se repiten como antes. Sanear `agent/context/` costaba ~5 ms por turno. Pasa de 7–9 ms a 3–4 ms; `check_memory_rules` da 40/40.
  7. **Interfaz:**
     - electron-vite fija `minify: false` en el renderer, y salía un solo chunk legible de 1.660 kB. Ahora va `minify: true`.
     - `navigation/pages.ts` carga con `React.lazy` cada sección salvo «Hoy», la primera pantalla.
     - Las demás secciones se precargan 1,5 s después del montaje, en reposo, para no competir con los datos de «Hoy».
     - El `Suspense` usa `fallback={null}`: sin cambio visual.
     - El chunk principal pasa a 362 kB.
     - Electron real (Xvfb, mediana de 7 recargas, 3 rondas): DOMContentLoaded de 74–109 ms a 42–60 ms, primer pintado de 112–152 ms a 88–120 ms y heap de 16,0 a 15,0 MB. El tiempo hasta «Hoy» con datos lo marca la respuesta del backend y no cambia de forma medible.
- **Alternativas descartadas:**
  - Una conexión SQLite reutilizada por hilo, que quitaría los ~2,3 ms por petición: cambia el modelo de conexiones endurecidas de `connection.py` y afecta a todo el backend. Queda para cuando haga falta.
  - Indexar `relationships (source_type)` y `(target_type)`: es un filtro poco usado y la consulta ya tarda <1 ms.
  - Sustituir el `LIKE '%q%'` de tareas por FTS: cambiaría resultados.
  - Rehacer `reconcile_structured`, que cuesta 20–33 ms por búsqueda: es lineal con índice, se cerró en «Optimizar FTS5» y quitarlo exige rastrear cambios con disparadores.
  - Acelerar la expansión de recurrencias de la agenda: es coste Python, no consulta.
  - `ANALYZE` en la migración: con una base recién creada fijaría estadísticas engañosas.
- **Comprobación:**
  - Migración sobre una **copia** de la base real (abierta con `mode=ro&immutable=1`; el original queda con el mismo SHA-256): versión 14→15, solo se aplica la 0015, integridad y claves foráneas OK, mismas filas (salvo `schema_version` +1), una segunda pasada no aplica nada y la restauración de la copia `pre-migrate` devuelve la versión 14 sin los índices nuevos y con las mismas filas.
  - `check_migrations`, `check_database` (76/76), `check_relations`, `check_tags_search`, `check_memory_rules` (40/40), `check_memory_confirm` (14/14), `critical/check_confirmations` y `check_security` (145/145): todo OK.
  - E2E de escritorio (`--only desktop`, stub): navegación por las 10 secciones, calendario, configuración, notificaciones y 0 errores de consola. `conexion_backend` falla igual en `f82dda9`: es del entorno sin Hermes.
- **Impacto:** `backend/migrations/0015_query_indexes.sql`, `backend/app/repositories/relations.py`, `backend/app/services/today_sources.py`, `backend/app/integrations/memory/{store_sqlite,service}.py`, `backend/app/integrations/memory/context/builder.py`, `desktop/electron.vite.config.ts`, `desktop/src/navigation/pages.ts` y `desktop/src/app/AppShell.tsx`. Checklist 17.

## [2026-11-20] DEP-OWW: PR #13 de Dependabot, solo anthropic 2.10.0; openWakeWord se queda en 0.4.0
- **Contexto:** el PR #13 sube `anthropic` 2.8.0 → 2.10.0 (`agent/evals`) y `openwakeword` 0.4.0 → 0.6.0 (`voice/`). La CI no instala la voz, por eso salía en verde. Con la 0.6.0, `uv pip compile` falla: en Linux exige `tflite-runtime>=2.8`, que no tiene ruedas para cp312 (la última, 2.14, llega a cp311). El venv de voz es Python 3.12 por Pipecat 1.16.0. Además la 0.6.0 cambia la firma de `Model` (`wakeword_models`, `melspec_model_path`, tflite por defecto) y deja de traer modelos en el paquete. La 0.6.0 es la última versión publicada.
- **Decisión:** se fusiona solo `anthropic==2.10.0`. `openwakeword` sigue en 0.4.0 y `voice/requirements.lock` no cambia. `.github/dependabot.yml` ignora `openwakeword>=0.5`. `scripts/install-voice.sh` admite `DRAKTER_VOICE_VENV` (por defecto `venvs/voice`), para probar dependencias en un venv aparte sin tocar el de la app, y rechaza rutas en `/tmp`.
- **Alternativas descartadas:** instalar la 0.6.0 con `--no-deps` y `inference_framework="onnx"`: rompe la idempotencia del lock y no aporta nada que la voz use. Las mejoras de la 0.5.1 (entradas que no son múltiplo de 1280) ya las cubre `WakeGate`, que puntúa en bloques de 1280. La de la 0.6.0 (debounce) la sustituye la confirmación textual.
- **Motivo:** la 0.6.0 no se puede instalar en el runtime de voz.
- **Impacto:** `agent/evals/requirements.txt`, `.github/dependabot.yml` y `scripts/install-voice.sh`. Comprobado en un venv aparte (`venvs/voice-cpu`): `install-voice.sh`, `python -m voice check` («Todo en orden»), `check_pipeline.py --real` 21/21 PASS y `check_conversation` OK. Con anthropic 2.10.0, `Anthropic(...)`, `messages.create` y `AnthropicError` se comportan igual. Ojo: `check_pipeline --real` necesita una frase corta sin palabra de activación. Los wavs de `research/wakeword/stt` dicen «despierta» o «Drakter», y los MLS largos siguen sonando tras cerrar el turno: se usó una frase de Kokoro de 1,9 s («¿Qué tiempo hace hoy en Madrid?»).

## [2026-11-20] CPU-1: CPU de la voz en reposo (openWakeWord con puerta de energía, recuperación del prebúfer y un hilo)
- **Contexto:** WP9 midió unos 53 % de un núcleo en reposo con `top` sobre la app. Para comparar el antes y el después hace falta una medida repetible, y se hizo con un banco propio: `python -m voice run` con los proveedores reales (Kokoro y Moonshine, sin Fish), un par WebRTC de aiortc como el de `check_pipeline` y un micro con ruido gaussiano débil. Se mide `utime+stime` de `/proc/<pid>` en tramos de 5 s, con 15 s de calentamiento y 60 s de medida, y se desglosa por hilo con `/proc/<pid>/task`. Se perfiló con py-spy 0.4 en el venv aparte `voice-cpu`, lanzado como hijo porque `ptrace_scope=1`. La máquina tenía loadavg 5-7 por otras sesiones. El proceso de voz de la app del usuario daba 22 % en ese momento.
  - **Antes** (`origin/main`, ruido −64 dBFS): reposo 25,5 % (tramos 23-29), 760 MB RSS, 62 hilos. Lo que se lleva el CPU:
    - openWakeWord, ~17 %: una predicción cada 80 ms en el pool de `asyncio.to_thread`, que rota entre 12 hilos a ~1,3 % cada uno. Aislado cuesta 6,3 ms por bloque, un 7,9 %; el resto es el salto entre hilos y la contención.
    - Hilo principal, ~10 %: aiortc (RTP, DTLS, ICE), la entrada de Pipecat y los observadores.
    - Codificador Opus de la salida, ~3-4 %.
  - Descartado por las cifras:
    - Silencio continuo del `DuckMixer`: con `DRAKTER_VOICE_MIXER=null` solo baja 1-2 puntos, y quitarlo haría perder el ducking instantáneo.
    - Opus: codificar silencio cuesta ~2 % aislado, igual a 24 kHz que a 48 kHz.
    - Silero, STT y Smart Turn no funcionan en reposo: la `WakeGate` no deja pasar audio y Moonshine abre un stream por tramo de VAD.
    - Los hilos de ONNX ya están limitados: openWakeWord 1, Silero 1, Smart Turn 2 y Kokoro 2.
  - **Después** (misma metodología, mismo ruido, ejecutados uno tras otro): reposo **16,1 %** (tramos 14-20), 739 MB RSS, 53 hilos. Con ruido por encima del umbral (−40 dBFS, la puerta siempre abierta): 22,3 %. Conversación callada: 26,5 % frente a 24,7 %, dentro del ruido de medida y sin cambios en ese camino.
- **Decisión** (`voice/providers/wake/openwakeword_gate.py` y `wake_energy_dbfs` en `voice/config.py`):
  1. **Puerta de energía:** en reposo solo se puntúa si el frame supera `wake_energy_dbfs`, −50 dBFS por defecto, y durante 1 s tras el último frame con sonido. El renderer captura con `noiseSuppression` y `autoGainControl`, así que el silencio de una habitación queda muy por debajo y la voz muy por encima. `-120` deja la puerta siempre abierta.
  2. **Recuperación:** al volver el sonido se puntúan de una vez los 2 s del prebúfer. Esos 2 s renuevan entera la ventana del modelo (16 embeddings de 76 frames de mel), así que el arranque de «hey jarvis» no se pierde. El prebúfer que se suelta al STT es el mismo de antes.
  3. **Bloques de 160 ms** mientras hay sonido: con varios bloques, `Model.predict` de la 0.4.0 puntúa cada ventana de 80 ms y devuelve el máximo, así que no se pierde ningún pico.
  4. **Un único hilo** (`ThreadPoolExecutor(max_workers=1)`, compartido por las conexiones) en lugar del pool de `to_thread`. El modelo es compartido y así nunca se llama dos veces a la vez.
- **Alternativas descartadas:**
  - VAD de Silero delante de openWakeWord: cuesta más que una RMS y añade otro modelo en reposo.
  - El `vad_threshold` de openWakeWord: ejecuta Silero en cada bloque.
  - Quitar el mixer o generar silencio solo con TTS: 1-2 puntos a cambio de perder la bajada de volumen inmediata del barge-in.
  - Parchear aiortc para no codificar silencio: toca una librería por ~2 puntos.
- **Motivo:** quitar el mayor consumo en reposo sin perder ninguna función.
- **Impacto:** `voice/providers/wake/openwakeword_gate.py` y `voice/config.py` (`wake_energy_dbfs`). Comprobado con el código nuevo:
  - Activación de punta a punta por WebRTC con `research/wp2/hey_jarvis.wav` y ruido de fondo: 1,14 s frente a 1,13 s antes, y 1,08 s con ruido a −40 dBFS. `check_wp2` puntúa 0,91 en la puerta y suelta los 126 frames.
  - Barge-in de punta a punta: «Para, para» sintético corta la voz del bot a los 0,81 s.
  - `check_pipeline.py --real` 21/21 PASS y `check_conversation` OK.
  - ⚠️ Queda en 16 %, algo por encima del objetivo orientativo del 15 %, con la máquina cargada; el resto es el coste base de aiortc y Pipecat. Falta repetirlo con la máquina descargada, con la app real y con el micro del usuario. Si el ruido de su habitación supera −50 dBFS, la puerta queda abierta y el consumo sube a ~22 %, sin perder ninguna función.

## [2026-11-20] Verificación de casillas pendientes y desconexiones
- **Contexto:** quedaban sin marcar casillas con código ya hecho (Checklists 3, 11, 13, 14, 16 y 17), varias porque «requieren la UI» o porque probarlas «cortaría la sesión del integrador» (red caída, cambio de red). La app del usuario seguía en marcha y no se podía tocar.
- **Decisión:** se verifican en un stack propio, aislado del usuario:
  - **Fase A, solo backend:** backend lanzado con los tokens en mano, datos, config y `XDG_RUNTIME_DIR` propios bajo `~/.local/share/drakter/verify-79`, con la voz desactivada y Claude Haiku 5.5 real. Sirve para los trabajos, las confirmaciones, el esfuerzo por carril, el runner muerto y las latencias de Hermes.
  - **Fase B, stack completo:** Electron (con su backend, Hermes y voz) dentro de `unshare -rnm`, es decir, con espacio de red y de montaje propios y solo `lo`. Un `/etc/hosts` montado encima apunta `api.anthropic.com`, `api.fish.audio` y `api.eu.deepgram.com` a 127.0.0.2-4. Allí escucha un reenviador TCP propio que, por un socket unix, sale al host real (el TLS va de extremo a extremo). «Red caída» es matar el reenviador exterior; «sin red», el propio espacio; «cambio de red», añadir y quitar interfaces `dummy` con ruta por defecto.
  - **Audio:** dos nodos nulos de PipeWire con prioridad 0 (no cambian los dispositivos predeterminados del usuario). El micro es el monitor de `drk79_mic`, alimentado con frases de Kokoro (`em_alex`); la salida, `drk79_out`, que se graba y se transcribe con faster-whisper small local. Nada suena por los auriculares del usuario.
  - **Control y limpieza:** CDP en el renderer (clics de confianza con `Input.dispatchMouseEvent`) e inspector de Node en `main`. Fish con `s2.1-pro-free` y sin `reference_id`, porque la plantilla de voces es propia y no lleva IDs. Al acabar se borran los nodos y `verify-79`, que tenía la copia de las claves.
  - **Pasada de referencia:** `scripts/verify-all.sh --headless` 45/45 PASA.
  **Hallazgos arreglados en este PR:** faltaba la herramienta `update_relationship` (ver la entrada siguiente), y los resúmenes de confirmación de `delete_relationship` y `delete_task` citaban el UUID en lugar de los títulos: `configure_summary_source` no se llamaba nunca.
  **Hallazgos sin arreglar** (fuera de mi zona o no pequeños):
  1. ✅ *(escritorio: deduplica, ver «Escritorio: .riv ausente y avisos de fallo de voz»; backend: un solo aviso con `job_id`, ver «Un solo aviso por confirmación y aviso de modelo inalcanzable»)* **Aviso doble de cada confirmación.** `confirmation.requested` sale una vez de `ActionService.announce_pending` (sin sesión ni `job_id`) y otra del observador del runtime o del carril. El escritorio se queda con el primero, así que pierde el `job_id`; hoy no se nota.
  2. ✅ Arreglado (ver «Un solo aviso por confirmación y aviso de modelo inalcanzable»). **Silencio con la red caída.** Hermes reintenta solo y el usuario no recibe ningún aviso de que el modelo no responde: ~58 s con el turno «en curso» y, en voz, solo el acuse.
  3. ✅ Arreglado (ver «Voz: etiquetas inventadas, dominios sueltos y `voice.error` en ejecución»). **Kokoro y las etiquetas.** `strip_tags` (Kokoro) solo quita las etiquetas de la lista, así que una etiqueta inventada como `[risa]` se leería; `keep_allowed` (Fish) sí la borra.
  4. ✅ Arreglado (misma entrada). **Dominios sin `http`/`www`.** Se leen en voz alta: quedan fuera del diseño del guard.
  5. ✅ Arreglado en la voz (misma entrada): emite `voice.error` con `message`; el escritorio ya lo muestra (PR #32). **Fallo de arranque silencioso.** Si faltan los modelos de voz, el pipeline falla al construirse y la interfaz sigue mostrando «Esperando "Jarvis"». Le pasó a esta prueba antes de enlazar `models` en sus datos.
- **Alternativas descartadas:**
  - Cortar la red de la máquina: cortaría la app y la sesión del usuario.
  - Probar sobre la app del usuario: prohibido.
  - `pasta` o `slirp4netns`: no están instalados, y el reenviador propio basta y deja cortar solo esos tres servicios.
- **Motivo:** marcar solo lo que se ha visto funcionar, sin tocar al usuario.
- **Impacto:** `docs/IMPLEMENTATION_STATUS.md` (checklists 3, 11, 13, 14, 16 y 17); `backend/app/tools/relations.py`, `backend/app/tools/tasks.py`, `backend/app/main.py`, `contracts/tools/catalog.json` (+ README), `agent/knowledge/TOOL_GUIDE.md`, `agent/skills/workspace-relationships/SKILL.md`. Los scripts de la prueba son material de trabajo y no se versionan.

## [2026-11-20] Herramienta `update_relationship` y resúmenes legibles en las confirmaciones
- **Contexto:** `MASTER_PLAN.md` §«Relationships» pide `update_relationship`, pero el catálogo solo tenía `create`, `delete`, `get_related_items` y `search`. El servicio (`svc.update_relationship`) y la ruta REST ya existían. Además, la confirmación de `delete_relationship` decía «Delete relationship <uuid>» y la de `delete_task`, «Vas a eliminar 1 tarea: «<uuid>»».
- **Decisión:**
  - `update_relationship` (`relationships.write`, `write`, sin confirmación) solo sustituye `metadata` y reutiliza `RelationshipUpdate` del backend, que la exige. Los extremos y el tipo no cambian: para eso se borra y se crea otra.
  - `app/main.py` llama a `configure_summary_source(db_path)` de `app.tools.relations` y de `app.tools.tasks` al arrancar. `delete_task` lee el título de la tarea para su resumen, igual que ya hacía `relations`.
- **Alternativas descartadas:** pasar el contexto al `summarize` de `ToolSpec`, que cambiaría el contrato de todas las herramientas.
- **Motivo:** la herramienta que faltaba era trivial, y una confirmación que solo muestra un UUID no deja decidir.
- **Impacto:** Checklist 11 («Crear herramientas Hermes»). `agent/evals/schemas/tool_inputs.json` no se regenera, porque ya iba desfasado (74 de 88).

## [2026-11-20] Carriles de trabajo: N=1
- **Contexto:** la casilla pide medir el RSS del runner trabajador y decidir si hacen falta 2.
- **Decisión:** se mantiene un solo carril trabajador (`w1`). Su RSS es de 221-231 MB tras un trabajo, con el agente caliente de LAT-1 (188 MB en WP9). Un trabajo típico dura 8-9 s y hace 6 llamadas a herramientas.
- **Alternativas descartadas:** N=2. Añadiría ~230 MB fijos (otro intérprete de Hermes) en una máquina de 14 GB con la voz en ~0,8 GB, y lo único que ganaría es atender dos encargos largos a la vez, algo que no se ha observado.
- **Motivo:** el coste fijo de memoria no compensa.
- **Impacto:** `backend/app/jobs/manager.py` sin cambios (`[Lane("w1", "hermes-w1", "medium", 900)]`). Checklist 3.

## [2026-11-20] Mediciones de RAM, CPU y latencias (Checklist 17)
- **Contexto:** faltaban las casillas de medición de la Checklist 17. Se parte de WP9, LAT-1 y PR #19 y se completa con el stack de la fase B (ver «Verificación de casillas pendientes y desconexiones»).
- **Decisión:** cifras medidas, sin extrapolar. Había otros workers en la máquina (loadavg 4-9) y Electron iba en Xvfb con `--disable-gpu`.
  - **RSS:** voz ~800 MB; Hermes primer plano ~215 MB; `hermes-w1` ~221 MB; backend ~111 MB; Electron ~630 MB entre main, renderer, GPU, utilidad y zygote. Total sumado ~2,0 GB, con las páginas compartidas contadas más de una vez.
  - **CPU (% de un núcleo, 30 s):**
    | | voz | renderer | backend | runners | total |
    |---|---|---|---|---|---|
    | reposo, esperando «Jarvis» | 24 | 37 | 0,6 | 0 | ~73 |
    | conversación | 31 | 40 | 0,8 | 0,6-0,9 | ~84 |
    El renderer está inflado porque dibuja por CPU en Xvfb. La voz en reposo baja del ~53 % de WP9, pero aquí sin el micrófono real. Todo esto se midió con el código de antes de CPU-1 (`665de20`, que ya está en `main`). Con CPU-1, la voz sola en reposo baja a ~16 % en su banco.
  - **STT:** Deepgram, final a 27-52 ms tras el fin de voz (5 turnos); Moonshine de respaldo, 491 ms. Fin de turno de 200 ms en 7 de 12 turnos; los de 1,7-4,2 s son frases sintéticas con pausas largas.
  - **TTS:** Fish TTFA 736-930 ms (9 turnos); frases en caché, 315-337 ms.
  - **Hermes:** en voz, primer fragmento a 573-1594 ms (12 turnos, mediana ~760) y primer audio (`total_ms`) a 2,6-3,2 s en los turnos con fin de turno corto. En texto con herramientas y thinking `low`, 6,1-7,7 s (2-4 llamadas a la API). Runner relanzado tras SIGKILL: ~6 s.
- **Alternativas descartadas:** medir sobre la app del usuario (prohibido) o con la ventana real en su escritorio (la abriría en su pantalla).
- **Motivo:** cerrar las casillas de medición con cifras reales.
- **Impacto:** Checklist 17. La optimización del CPU en reposo sigue pendiente.

## [2026-11-20] Sin `.riv`, `app://drakter/__character/drakter.riv` responde 204, no 404
- **Contexto:** la comprobación e2e `desktop.errores` fallaba en `main`: «Failed to load resource: … 404 [app://drakter/__character/drakter.riv]». Que no haya `.riv` es lo normal hasta que el usuario lo diseñe, y el renderer ya pasa al SVG, pero Chromium anota cualquier 404 como error de consola.
- **Decisión:**
  - El protocolo `app://` responde **204 No Content** cuando falta el `.riv` o no tiene extensión `.riv`.
  - `AdaptiveCharacter` trata el 204 como «sin .riv» y usa el SVG sin avisar. Sigue aceptando el 404 por compatibilidad y avisando ante otros fallos o un `.riv` vacío.
  - El arnés e2e añade la URL a los errores de consola de `Log.entryAdded` (`tests/e2e/harness/cdp.py`), para saber qué recurso falla.
- **Alternativas descartadas:**
  - Meter el mensaje en la lista de ruido del arnés: escondería 404 reales.
  - Preguntar a `main` por IPC si existe el `.riv`: añade un canal nuevo para nada.
- **Motivo:** la ausencia esperada no es un error, y la consola limpia vuelve a servir de señal.
- **Impacto:**
  - Código: `desktop/electron/main/rendererProtocol.ts`, `desktop/src/character/AdaptiveCharacter.tsx`, `tests/e2e/harness/cdp.py`.
  - Comprobado: `scripts/verify-all.sh --headless` da 45/45 PASA (`desktop.errores` con 0 errores y `desktop.personaje` PASA), y typecheck y build sin errores.

## [2026-11-20] Voz: etiquetas inventadas, dominios sueltos y `voice.error` en ejecución
- **Contexto:** la verificación del 2026-11-20 («Verificación de casillas pendientes y desconexiones») dejó tres fallos de voz sin arreglar. Kokoro leía en voz alta las etiquetas inventadas (`[risa]`), porque `strip_tags` solo quita las de `TAGS`. Los dominios sin `http`/`www` se leían tal cual. Y si el pipeline fallaba, la interfaz no recibía ningún aviso.
- **Decisión:**
  - **Etiquetas:** `voice/speech/tags.py` trata como etiqueta cualquier `[..]` con forma de etiqueta: letras, espacios y `-_'`, hasta 5 palabras y 40 caracteres, y que no sea texto de un enlace Markdown. Kokoro, Fish con la expresión apagada y las frases no expresivas usan `strip_all`, que las quita todas. Fish con expresión usa `keep_known`, que deja solo las de `TAGS`, normalizadas en minúsculas, y quita el resto. Así Fish tampoco recibe las de más de 3 palabras que `keep_allowed` dejaba pasar. `speech_markup.strip_tags` no cambia, porque es lo que el backend usa para el chat y la BD, y ahí `[1]` o `[nota]` del usuario deben seguir.
  - **Dominios:** `SpeechGuard` retiene la palabra mientras solo tenga caracteres de URL y decide al terminarla. Un dominio con TLD conocido (`_TLDS`) se dice por el nombre del sitio («ejemplo», «github»), y si lleva ruta, «el enlace de github». El TLD tiene que ir en minúsculas en el texto, y quedan fuera a propósito las extensiones de archivo habituales (`py`, `md`, `sh`, `js`, `ts`…) y los TLD que son palabras corrientes (`no`, `me`, `se`, `de`, `it`, `at`, `be`, `us`). Así, «listo.No» o «ahora.Es» (frases sin espacio tras el punto), `3.5`, `v2.1.3`, `1.000`, `p. ej.`, `EE.UU.` y `main.py` no cambian. Los correos (`@`) no se tocan.
  - **`voice.error`:** `Session.report_error(code, stage, recoverable)` emite el aviso con un `message` corto y fijo (`voice/errors.py`), como mucho una vez por código cada 60 s, y nunca lanza. Fuentes:
    - `on_pipeline_error` del `PipelineWorker`: error fatal, procesador inservible o fallo que el `ServiceSwitcher` reporta como propio por quedarse sin respaldo. Da `stt_unavailable`, `tts_unavailable`, `service_failed` o `pipeline_failed`.
    - `DrakterFailover`: el último TTS falla 3 veces seguidas aunque siga «usable», y da `tts_unavailable`.
    - Montaje de la conexión: `models_missing` si falta un modelo (`FileNotFoundError`); si no, `pipeline_build_failed`.
    - Excepción del pipeline en marcha: `pipeline_failed`.
    El proceso de voz sigue vivo en todos los casos. El backend ya reenvía `voice.error` al WebSocket (`VoiceOrchestrator._evt_error`) y el `message` pasa sin tocar `backend/`.
  - **Contrato:** `message: str | None` (≤160) opcional en `EvtError` (`voice_ipc.py`) y `VoiceError` (`events.py`), con `contracts/ts/index.ts` regenerado. Es compatible: quien no lo conoce lo ignora.
- **Alternativas descartadas:**
  - Cambiar `strip_tags` en `speech_markup`: borraría corchetes legítimos del chat y de la BD.
  - Detectar dominios con cualquier `palabra.palabra`: rompería números, abreviaturas y nombres de archivo.
  - Avisar con cada `ErrorFrame`: un servicio roto falla en cada frase, y los errores que el switcher resuelve conmutando no son fallos para el usuario.
  - Mapear el código a texto solo en el escritorio: el contrato ya lleva el texto, y el escritorio puede ignorarlo.
- **Motivo:** que la voz no diga cosas raras y que un fallo se vea en la interfaz sin cortar la app.
- **Impacto:**
  - Código: `voice/speech/tags.py` y `voice/errors.py` (nuevos); `voice/speech/guard.py`, `voice/providers/tts/_common.py`, `voice/speech/phrases.py`, `voice/providers/tts/failover.py`, `voice/session.py`, `voice/pipeline.py` y `voice/__main__.py`; `contracts/python/drakter_contracts/{voice_ipc,events}.py`, `contracts/ts/index.ts` y `voice/CONTRACT.md`.
  - Comprobado: `voice/tests/check_pipeline.py` da 21 PASS. Una prueba rápida con un pipeline real de Pipecat (Fish y Kokoro simulados que fallan con error de autenticación) emite `voice.tts_fallback` y un único `voice.error{tts_unavailable}` válido contra el contrato. El guard da el mismo resultado troceado carácter a carácter que entero.
  - Pendiente: que la interfaz muestre el aviso (otro worker, `desktop/`). Ojo: el venv de voz enlaza `drakter-contracts` al checkout del usuario, así que `message` no llega hasta que ese checkout tenga este cambio.

## [2026-11-20] Escritorio: .riv ausente y avisos de fallo de voz
- **Contexto:** `desktop.errores` fallaba en main por un «Failed to load resource: 404» de `/__character/drakter.riv` cuando el usuario no tiene .riv; y la interfaz no avisaba de `voice.error` ni de `voice.state` con `connected=false`.
- **Decisión:** (1) El .riv ausente lo arregló en paralelo otra rama ya fusionada (protocolo responde 204, `AdaptiveCharacter` lo trata como «sin archivo»); me quedé con esa versión, sin duplicarla. Los errores reales (HTTP ≠ 200/204/404, archivo vacío, fallo al cargar) siguen avisando. (2) `stores/voice.ts` fija un fallo de voz con `voice.error` o con `connected` pasando de true a false; muestra un toast con `notify` (tono error) y deja `mic = 'error'` (`MicState` gana `'error'`; «Voz con error» con icono de micrófono apagado y punto `bg-destructive` en `SpeakerToggle`). El fallo se limpia con un `voice.state` conectado. Dedup: misma clave (`stage|code` o «disconnected») dentro de 30 s no repite el toast. No avisa si la voz nunca llegó a conectarse (evita un toast en cada arranque sin voz); ese caso depende del `voice.error` que emita el backend. (3) `confirmations.ts` ya ignoraba un `confirmation.requested` repetido por `action_id`; además ahora completa los campos opcionales (sesión, turno, herramienta) que el primer aviso no traía, en vez de descartar el segundo por completo.
- **Alternativas descartadas:** avisar en cada `connected=false` inicial (ruido en cada arranque); un toast por cada `voice.error` (llena la pantalla).
- **Motivo:** el usuario debe enterarse de un fallo de voz sin saturarlo, y la consola debe poder verificarse en limpio.
- **Impacto:** `desktop/src/stores/voice.ts`, `voice/contract.ts`, `components/status/DrakterStatus.tsx`, `chat/SpeakerToggle.tsx`, `stores/confirmations.ts`. Comprobado: tsc y build limpios; `verify-all --headless` con `desktop.errores` en verde (queda `desktop.conexion_backend` en FALLA, ya fallaba antes y no es de esta zona); con `voice.error` inyectado ×3 sale un solo toast y el estado muestra «Voz con error», y se recupera con `voice.state` conectado.
  - Actualización: el aviso de `voice.error` muestra `message` si viene y, si no, un texto por código (`stt_unavailable`, `tts_unavailable`, `models_missing`, `pipeline_build_failed`, `pipeline_failed`, `service_failed`, `stt_fallback`); `protocol.ts` valida `message` como opcional.

## [2026-11-20] Un solo aviso por confirmación y aviso de modelo inalcanzable
- **Contexto:** hallazgos 1 y 2 de la verificación del PR #30. `confirmation.requested` salía dos veces: primero desde `ActionService.announce_pending` (sin `session_id` ni `job_id`) y después desde el observador del runtime o del carril. Además, con la red caída Hermes reintentaba durante ~58 s sin que el usuario supiera nada.
- **Decisión:**
  - **Confirmaciones:** `ActionService` es el único emisor. `ActorContext` lleva `job_id` (en memoria, sin migración), `tool_gate._actor` lo copia del `ToolContext`, y `_request` guarda `(session_id, job_id)` antes del `COMMIT`, para que el barrido de 1 s nunca vea la fila sin su origen. Los observadores de `runtime.py` y `jobs/manager.py` ya no publican; el de trabajos solo cuenta `pending_actions`. Las filas creadas por otros módulos se siguen anunciando igual, sin sesión.
  - **Modelo inalcanzable:** el `DrakterAgent` del runner sobrescribe `_invoke_api_request_error_hook`, al que Hermes llama una vez por fallo de llamada al modelo (`agent/turn_api_error.py`), y con `retryable` y un motivo de transporte (`timeout`, `server_error`, `overloaded`, `unknown`) emite `{"ev":"retrying"}`. `HermesProvider` lo traduce a `ModelRetrying`. El runtime, al primer reintento de cada turno, pasa el estado a `offline` con `reason="model_unreachable"` (prioridad máxima del arbiter); cuando llega un delta o una herramienta, vuelve el estado normal. Por cada corte (no por turno) guarda y publica un único `notification.created` (`kind="agent"`, `severity="warning"`, «Sin conexión con el modelo; reintentando…»). En un turno de voz suena la frase de caché `offline` mediante `runtime.on_model_unreachable` → `VoiceOrchestrator.say_phrase` (`main.py`), sin tocar `voice/`.
  - **Voz más corta:** con `quick_retry` (lo envía `HermesProvider` en los turnos de voz), el runner fija ese turno con `_api_max_retries=2` y `_auto_recovery_cycles=0`, y salta la reconstrucción del cliente (`_try_recover_primary_transport`, 5 s más). Los turnos de texto recuperan los valores de la home (3 y 5).
- **Alternativas descartadas:**
  - Quitar `announce_pending` de `_request`: el barrido de 1 s anunciaría igual la fila sin `job_id`.
  - Que los observadores marquen la fila como ya anunciada: llegan después del anuncio síncrono.
  - Un vigilante de silencio en el backend: no distingue un modelo lento de uno inalcanzable.
  - `status_callback`: Hermes no lo llama en los reintentos normales, solo en la escalera final.
  - Acortar también los turnos de texto: allí se puede esperar y cancelar, y ya hay aviso.
- **Motivo:** un emisor, un aviso con el `job_id` correcto, y el usuario sabe enseguida que no hay conexión con el modelo.
- **Impacto:**
  - Código: `backend/app/permissions/{models,tool_gate}.py`, `backend/app/services/actions.py`, `backend/app/jobs/manager.py`, `backend/app/integrations/hermes/{events,hermes_provider,supervisor,runtime}.py`, `runner/drakter_runner.py`, `backend/app/main.py` y `CONTRACT.md`. Sin cambios en `contracts/`.
  - El gancho y los atributos `_api_max_retries`, `_auto_recovery_cycles` y `_try_recover_primary_transport` están atados a Hermes v0.22.7, como `_repair_tool_call`.
  - **Para que una actualización de Hermes no los anule en silencio:**
    - `preflight.py` comprueba, en el venv de Hermes, `RUNNER_HOOKS`: que `AIAgent` siga teniendo `_repair_tool_call`, `_invoke_api_request_error_hook` y `_try_recover_primary_transport`, y que los módulos que los usan (`agent.turn_tool_validation`, `agent.turn_api_error`, `agent.conversation_loop`, `agent.turn_recovery_autorecover`) sigan nombrándolos, igual que `_api_max_retries` y `_auto_recovery_cycles`. Si falta alguno, el preflight FALLA, nombrando cuáles faltan, justo después de la comprobación del commit.
    - Además, el runner escribe al arrancar `WARNING Hermes lacks overridden hooks: …` en stderr, que el supervisor lleva al log, si algún método sobrescrito no existe. No tumba el agente.
    - Comprobado contra el venv real: 0 faltan; con dos nombres renombrados, los detecta.
  - Comprobado:
    - Dos peticiones reales por `BackendToolGate`, una desde un trabajo y otra desde el chat, dan un aviso cada una, con su `job_id` y su `session_id`, y el barrido no repite. `check_confirmations` da 0 fallos y pasan también las demás comprobaciones de la CI del backend.
    - Hermes real contra un puerto local cerrado salta el gancho con `reason=timeout` y `retryable=True`. En modo voz, primer aviso a los ~3,3 s y fallo a los ~8,9 s (antes 23 s con la reconstrucción del cliente, y ~58 s medidos).
    - Runtime con eventos simulados: 3 reintentos dan 1 notificación, 1 frase y `offline`/`model_unreachable`; el mismo corte en otro turno no repite; cuando vuelve el modelo el estado sale de `offline`, y un corte nuevo vuelve a avisar.
  - Red de seguridad en el escritorio: `stores/confirmations.ts` ya deduplica por `action_id` (PR #32, entrada «Escritorio: .riv ausente y avisos de fallo de voz»). No hace falta tocar `desktop/`.

## [2026-11-20] e2e `desktop.conexion_backend`: 403 `forbidden_origin` no reproducible en main
- **Contexto:** el worker de escritorio veía fallar `desktop.conexion_backend` con un 403 `forbidden_origin` en `/health` (backend.log) y se sospechaba de una regresión de los PR #28 o #29.
- **Decisión:** no se toca el backend ni la comprobación de origen. En un checkout limpio de `main` (c6b956a: `uv sync`, `npm ci` y build), `scripts/verify-all.sh --headless --only desktop` da PASA en `desktop.conexion_backend` y en otras 9 comprobaciones del bloque; `desktop.confirmacion` sale NO COMPROBADO, como siempre. No hay ningún `forbidden_origin` en el log.
- **Causa:** `SecurityGuardMiddleware` (`core/security.py`, sin cambios desde `dd3a8e1`) rechaza por diseño cualquier petición con cabecera `Origin`: al backend solo le habla el proceso main de Electron, con `http` de Node, que no la envía (`backendProcess.ts`). El 403 significa que en ese entorno alguien llamó a `/health` con `Origin`: el renderer (`fetch` desde `app://` o desde `localhost:5173` con `npm run dev`), `net.fetch`/`session.fetch` de Electron, o una herramienta o pestaña apuntando a ese puerto. Hay que buscarlo en la rama o el entorno de ese worker, no en el backend ni en el arnés de `main`.
- **Alternativas descartadas:** aceptar el origen `app://` o el del servidor de desarrollo, porque relajaría una medida de seguridad.
- **Motivo:** lo verificado en `main` contradice la hipótesis de la regresión.
- **Impacto:** ninguno en el código. Avisado a drakter-1.

## [2026-11-20] Skills de agente para el nuevo avatar animado
- **Contexto:** el worker de concepto del avatar necesita guía de diseño de personaje, rigging y expresiones, principios de animación, máquinas de estados, SVG, Three.js/R3F/GLSL, GSAP y dirección de arte.
- **Decisión:** se versionan en `.claude/skills/` 16 skills con licencia permisiva y commit fijado: `character-design-continuity` y `2d-character-rig-animation` (calesthio, MIT), `animation-principles` y `svg-animation` (iart-ai, MIT), `rive-interactive` (freshtechbro, MIT), `three-best-practices` y `r3f-best-practices` (emalorenzo, MIT), `threejs-shaders` y `threejs-animation` (CloudAI-X, MIT), `gsap-core`, `gsap-timeline`, `gsap-plugins`, `gsap-react` y `gsap-performance` (GreenSock, MIT), y `canvas-design` y `algorithmic-art` (Anthropic, Apache-2.0). `scripts/install-agent-skills.sh` gana la lista `AVATAR_SKILLS` y las opciones `--dest` y `--only-avatar`, para instalarlas en otro checkout desde los mismos commits. Se revisaron todos los `SKILL.md` y scripts: no hay descargas, telemetría ni comandos de red. Solo `rive-interactive` trae scripts (generadores de código locales), y `algorithmic-art/templates/viewer.html` carga p5.js desde un CDN al abrirse.
- **Alternativas descartadas:** `svg-animations` de supermemoryai y `three-best-practices`/`gsap` de LLMTooling, porque no tienen licencia y duplican a las elegidas. `svg-character-animation` de OpenMontage, porque su repositorio es AGPL-3.0 aunque el frontmatter dice MIT, y porque es corta y la cubre `2d-character-rig-animation` + `gsap-*`. `theme-factory` de Anthropic, orientada a temas de diapositivas y documentos. Las de lip sync de los registros, porque son clientes de servicios de vídeo de pago (fal, Sync Labs, Kling). Para los visemas basta con `2d-character-rig-animation` y los morph targets de `threejs-animation`. Tampoco se instalan las variantes de animación de owl-listener ni las de 12 principios, porque son resúmenes cortos.
- **Motivo:** cubrir los seis frentes pedidos con las skills de más calidad (las oficiales de GreenSock y Anthropic, las más instaladas de Three.js y las guías de producción de rig 2D), sin relleno.
- **Impacto:** `.claude/skills/<16 nuevas>/`, `scripts/install-agent-skills.sh`, `THIRD_PARTY_NOTICES.md` y `.claude/skills/drakter-toolkit/SKILL.md`. No afecta a la app.


## [2026-11-26] Avatar 3D Three.js sustituye al placeholder; Rive queda como alternativa
- **Contexto:** el `.riv` de Drakter no puede generarse por código y el usuario no lo ha diseñado. El concurso de avatares 3D (Three.js 0.180, todo procedural) dio tres finalistas (Ascuario, Filamento y El Relojero) con la misma API: `createAvatar(canvas, opts) → { setState, setAudioLevel, setViseme?, lookAt, notify, setReducedMotion, resize, dispose }`. Además hay en marcha una ronda nueva de avatares holográficos, con la misma API, de la que saldrá el definitivo.
- **Decisión:**
  - El personaje por defecto es un **avatar 3D en Three.js 0.180.0** (MIT, versión fija), con un único lienzo WebGL2. Orden en `AdaptiveCharacter`: primero el `.riv` del usuario, si existe (Rive queda como **alternativa**, no se borra); si no, el avatar 3D; y, sin WebGL2 o si falla la carga, el SVG provisional. El SVG se dibuja desde el primer momento y se retira cuando el lienzo ya se ve, tras su fundido.
  - **Anfitrión genérico**: `avatars/types.ts` (contrato común), `avatars/registry.ts` (carga diferida de cada avatar; **cambiar de avatar es cambiar `ACTIVE_AVATAR`**), `ThreeCharacter.tsx` (cableado) y `activity.ts` (aviso de escritura). Fuera de `avatars/<nombre>/` no hay nada específico de un avatar.
  - Cableado: prop `state` → `setState`; `useMouthLevel` (nivel real de `voice/outputLevel`) → `setAudioLevel`; la mirada sigue al ratón por defecto (no se llama a `lookAt`); `focus`/`blur` de la ventana y la escritura en `ChatComposer` (como mucho un aviso cada 400 ms) → `notify`; el ajuste «Reducir movimiento» o `prefers-reduced-motion` → `setReducedMotion`; `ResizeObserver` → `resize`; el desmontaje → `dispose`. El bucle es del avatar, a 30 fps, y se para con `document.hidden`. `pixelRatio` tiene un tope de 1,5.
  - **Avatar provisional: Ascuario**, portado sin cambios de lógica a `desktop/src/character/avatars/ascuario/` (TypeScript estricto; compila con el `tsconfig.web.json` de la app). Su malla horneada (`ascuario-geo.json`, 2 MB, generada por su `sculpt.ts`) va como asset de Vite (`?url`). Three, Ascuario y la malla van en un chunk aparte (549 KB + 2 MB) que no pesa en el arranque. Único cambio en el port: `setReducedMotion(false)` reactiva los micro-gestos.
  - **CSP sin cambios.** Three/WebGL no necesita `eval` ni workers, y la malla se pide con `fetch` a `'self'`. Comprobado en la build de producción (`app://drakter`), sin violaciones. La comprobación de origen del backend no se toca.
  - De paso: en desarrollo Vite responde a `/__character/drakter.riv` con `index.html` (200) y Rive avisaba «Bad header»; ahora una respuesta `text/html` cuenta como «no hay `.riv`».
- **Alternativas descartadas:** esperar al `.riv` (bloquea el personaje sin plazo). Usar React Three Fiber (los avatares ya traen su propio bucle y su API imperativa; añadiría una capa sin beneficio). Importar `.mjs` precompilados con un `.d.ts` (Ascuario ya está en TypeScript estricto y portarlo tal cual es más limpio). Relajar la CSP «por si acaso» (no hace falta).
- **Motivo:** dar ya un personaje expresivo y vivo, sin bloquear la elección del avatar definitivo, que se enchufa tocando una línea.
- **Impacto:**
  - Código: `desktop/src/character/{AdaptiveCharacter,ThreeCharacter}.tsx`, `character/{activity,plug}.ts`, `character/avatars/**`, `chat/ChatComposer.tsx`, `desktop/package.json` y el lockfile, y `THIRD_PARTY_NOTICES.md`. Checklist 5 (notas en «Crear proyecto Rive» y «sincronización labial»).
  - Comprobado en Electron (instancia aparte, sin backend) en un i7-8665U con UHD 620. Los 9 estados cambian luz y expresión, la mandíbula sigue a una pista sintética inyectada en `outputLevel` y la cabeza sigue al cursor. El respaldo SVG funciona: al forzar un fallo del cargador no hay lienzo, se ve el SVG y queda aviso en el log. Arranque del avatar en 178 ms. En reposo, a ~22-30 fps: renderer 5,3 % y 6,7 % de CPU (dos medidas de 20 s) y proceso GPU 4,3 % y 7,5 %, con 0,4-0,9 ms de JS por fotograma, 20 llamadas de dibujo y 107 k triángulos. Con `document.hidden`, 0 % en ambos.
  - Pendiente: probar la boca con la voz real, y sincronizar el port cuando drakter-93 cierre su pulido o cuando se elija el avatar holográfico.

## [2026-11-26] Avatares 3D con fondo transparente (`AvatarOptions.transparent`)
- **Contexto:** el avatar final saldrá de la ronda de avatares holográficos y debe flotar sobre la interfaz, no ir dentro de una tarjeta oscura.
- **Decisión:**
  - El contrato (`avatars/types.ts`) suma `transparent?: boolean`: lienzo con alfa premultiplicado y sin fondo propio.
  - Cada entrada de `avatars/registry.ts` declara `transparent`. `ThreeCharacter` se lo pasa al avatar y, si es transparente, no lo enmarca (sin esquinas redondeadas).
  - Ascuario lo soporta: limpia con alfa 0, usa `premultipliedAlpha` y oculta su halo. Aun así se queda en `transparent: false`, porque se diseñó sobre su halo: sin él se notan el corte plano del busto y el humo cortado en el borde del lienzo.
- **Alternativas descartadas:**
  - Detectarlo en tiempo de ejecución, leyendo el alfa del lienzo: es frágil y cuesta una lectura de la GPU.
  - Una máscara de bordes genérica en CSS: puede recortar contenido propio de cada avatar.
- **Motivo:** que un avatar holográfico se enchufe con una línea y flote sin tocar el anfitrión.
- **Impacto:**
  - Código: `desktop/src/character/{ThreeCharacter.tsx,avatars/{types,registry}.ts,avatars/ascuario/{index,scene}.ts}`.
  - Comprobado en Electron con Ascuario forzado a `transparent: true`, en el tema claro (el actual) y en el oscuro: sin tarjeta, bordes limpios y sin halos oscuros. En el tema claro el contraste es alto; en el oscuro es más justo con un avatar negro, aunque legible gracias a las vetas y los reflejos.
  - Cuidado para los avatares transparentes: lo que se salga del lienzo (partículas, humo) se corta en el borde.

## [2026-11-26] Avatar 3D desactivado por defecto (`ACTIVE_AVATAR = null`)
- **Contexto:** el PR #35 tiene que fusionarse ya, porque el modo Jarvis depende de él, y lo que ve el usuario no debe cambiar hasta que elija el avatar holográfico.
- **Decisión:** `avatars/registry.ts` admite `ACTIVE_AVATAR = null`, que queda como valor por defecto. Sin avatar activo, `AdaptiveCharacter` hace lo de antes: el `.riv` del usuario si existe y, si no, el SVG. Ascuario sigue registrado, pero inactivo. Activar un avatar sigue siendo cambiar esa línea (p. ej. `'ascuario'`). `ThreeCharacter` recibe ahora la entrada del avatar como prop.
- **Alternativas descartadas:** quitar Ascuario del registro, porque se perdería el avatar de prueba del anfitrión. Un ajuste en la interfaz, porque el usuario aún no ha elegido avatar.
- **Motivo:** fusionar sin cambiar lo que ve el usuario.
- **Impacto:**
  - Código: `desktop/src/character/{AdaptiveCharacter,ThreeCharacter}.tsx`, `avatars/registry.ts` y `plug.ts`.
  - Con `null`, el build no genera el chunk de Three ni la malla (el import diferido queda como código muerto y se elimina).
  - Comprobado en Electron: con `null` se ve el SVG, sin lienzo y sin pedir nada de Three; con `'ascuario'`, el avatar 3D, sin avisos. Esto matiza la entrada «Avatar 3D Three.js sustituye al placeholder»: el anfitrión está listo, pero hoy no hay avatar activo.
## [2026-11-26] Modo Jarvis: segundo shell de interfaz sobre una sola capa de datos
- **Contexto:** el usuario pide un modo Jarvis (HUD holográfico, 3D, maximalista), con Drakter como interfaz por defecto. El MASTER_PLAN no lo contempla. El diseño completo está en el artefacto `jarvis-arquitectura.md` (sesión drakter-100).
- **Decisión:** el modo Jarvis es un segundo shell completo en `desktop/src/jarvis/`, con carga diferida (`import()`) y fuera de `preloadPages()`, que comparte con Drakter los stores, `services/{api,ws,protocol}.ts`, la API y los hooks de `modules/*`, la voz y los avatares. En `jarvis/` solo hay presentación y adaptadores para los gráficos, nunca peticiones, caché ni reglas propias. Solo se monta un shell a la vez. La voz, el feed de notificaciones y los atajos suben a un `SessionHosts` común, porque desmontar `AppShell` cortaría WebRTC. La sección actual (hash) se comparte entre modos. El modo vive en `stores/uiMode.ts` (chunk principal, sin importar nada de `jarvis/`). Nada fuera de `jarvis/` importa de `jarvis/`, salvo el `import()` de `ModeRoot`. La personalidad (`agent/identity/`) no cambia con el modo.
- **Alternativas descartadas:** un tema CSS sobre el shell actual (no da para el HUD pedido); un segundo `BrowserWindow` (duplica la sesión de voz, el enlace y la memoria); repetir la lógica de datos dentro de `jarvis/` (dos fuentes de verdad).
- **Motivo:** dar el modo pedido sin duplicar datos ni lógica, y sin que Drakter cargue con su peso.
- **Impacto:** amplía MASTER_PLAN §5 a petición del usuario. Contratos J0: `desktop/src/stores/uiMode.ts`, `stores/preferences.ts` (`jarvisStartup`, `lastUiMode`, `jarvisQuality`). Implementación en los paquetes W1-W10 del diseño.

## [2026-11-26] Activación del modo Jarvis: cinco vías, voz doble y evento `ui.mode`
- **Contexto:** el modo debe activarse desde la interfaz y por voz («modo Jarvis», «activa el modo Jarvis», «vuelve a Drakter»), y Drakter debe ser siempre el modo de arranque.
- **Decisión:**
  - Todas las vías llaman a `requestUiMode(mode | 'toggle', source)`: botón, `Ctrl+Shift+J`, bandeja (canal main→renderer `ui:mode-toggle`, `window.api.ui.onModeToggle`), capa 0 de la voz y herramienta de Hermes.
  - El store ignora repeticiones del mismo modo, cambios a menos de 1 s del anterior y peticiones durante una transición.
  - Voz por las dos vías. (1) Capa 0 local: frases cerradas → `voice.local_command` con los comandos nuevos `ui_jarvis` y `ui_drakter` (`EvtLocalCommand`). No hay LLM ni turno, y el backend audita como ya hace. (2) Herramienta `ui_set_mode` para el chat de texto, las paráfrasis y las órdenes compuestas.
  - Las dos publican el evento WS `ui.mode` (`UiModeRequested{mode, source, utt_id?}`, versión 1), que es una petición: el renderer decide si la aplica.
  - El backend no guarda el modo y el evento no se reenvía tras un resync.
  - La herramienta se registra con permiso `ui.write`, riesgo `WRITE` y sin confirmación, porque solo cambia el aspecto, es reversible y no toca datos. La audita el registry.
  - Arranque: siempre Drakter. Recordar el último modo es opcional (`jarvisStartup: 'last'`, desactivado por defecto).
- **Alternativas descartadas:** solo la herramienta (unos 3 s de latencia, y depende de Hermes y de la clave); solo la capa 0 (el chat de texto y las frases libres no funcionarían); guardar el modo en el backend (es una preferencia de la interfaz y daría estado que sincronizar).
- **Motivo:** que la orden habitual sea instantánea y que cualquier otra forma de pedirlo también funcione, con las reglas de herramientas de CLAUDE.md §8.
- **Impacto:** `contracts/python/drakter_contracts/{events,voice_ipc}.py`, `contracts/ts/index.ts` y `desktop/src/services/protocol.ts` (J0). Pendiente: W5 (`voice/conversation/layer0*`, `voice/bridge.py`, `backend/app/integrations/voice/policy.py`, `backend/app/tools/ui.py`, `agent/configuration/permissions.json`, `contracts/tools/catalog.json`), W6 (bandeja) y W1 (botón, atajo y `ModeRoot`). Trampa conocida: en reposo, «activa el modo Jarvis» acaba en la palabra de activación y `bridge._finish` lo descartaría como falso positivo; W5 acepta la frase `ui_*` completa antes de esa rama.
- **Riesgo aceptado:** un documento o un recuerdo podría inducir al agente a llamar a `ui_set_mode`. El efecto es solo visual, queda auditado y está limitado a un cambio por segundo.

## [2026-11-26] Modo Jarvis: un único lienzo WebGL y avatar como capa (`createAvatarLayer`)
- **Contexto:** Jarvis dibuja mucho 3D (retículas, partículas, grafo, avatar) en una UHD 620. Cada lienzo WebGL añade contexto, compositor y bucle, y `createAvatar` (PR #35) crea su propio `WebGLRenderer` y su propio `rAF`.
- **Decisión:**
  - Jarvis tiene un solo lienzo WebGL2 a pantalla completa bajo el HUD en DOM. Todas las capas comparten renderer y bucle (contrato `desktop/src/jarvis/stage/types.ts`: `Stage`, `StageLayer`, `StageFrame`, `QualityProfile`).
  - React no corre por fotograma: las capas reciben instantáneas de datos.
  - El contrato del avatar gana, de forma aditiva, `AvatarLayer` y `CreateAvatarLayer(renderer, opts)`. La capa dibuja en el renderer compartido dentro de un `AvatarViewport`, sin limpiar y restaurando el estado global que cambie. `AvatarEntry.loadLayer?` es opcional.
  - Si un avatar no tiene capa, Jarvis lo monta con `createAvatar` en un segundo lienzo.
  - `createAvatar` puede pasar a ser un envoltorio de la capa, de modo que el autor escribe una sola implementación.
  - El audio para el osciloscopio llega por `desktop/src/voice/levels.ts` (`readSpectrum`, `readWaveform`, `acquireAudioTaps`, `setInputStream`). Se lee en cada fotograma y `VoiceClient`, que está congelado, no cambia. J0 deja un stub que siempre devuelve «sin señal»; la implementación es de W7.
- **Alternativas descartadas:** un lienzo por efecto (más contextos y sin composición en profundidad); React Three Fiber (ya descartado para el avatar 3D); cambiar `createAvatar` en lugar de añadir (rompería Ascuario y la ronda holográfica en curso).
- **Motivo:** el menor coste posible en la iGPU y que el avatar holográfico se integre sin tocar Drakter.
- **Impacto:** `desktop/src/character/avatars/{types,registry}.ts`, `desktop/src/jarvis/stage/types.ts` y `desktop/src/voice/levels.ts` (J0). Implementación en W3 (Stage), W4 (capa de Ascuario y del avatar holográfico) y W7 (audio). Los avatares de la ronda `holo-*` deben ofrecer `createAvatar` y `createAvatarLayer`.

## [2026-11-26] Modo Jarvis: niveles de calidad Cine / Equilibrado / Ahorro y regulador
- **Contexto:** objetivo de 30-60 fps, con CPU del renderer en reposo ≲ 20 % en Cine y ≲ 10 % en Ahorro, en un i7-8665U con UHD 620. Además, un monitor 4K o un DPR de 2 multiplican el coste de pintar.
- **Decisión:**
  - Tres niveles, más `auto` (preferencia `jarvisQuality`, por defecto `auto`):
    | | fps máx. / en reposo | píxeles | bloom | partículas | parallax |
    |---|---|---|---|---|---|
    | Cine | 60 / 30 | 2,1 MP | media resolución | unas 20 k | sí |
    | Equilibrado (UHD 620 por defecto) | 30 / 20 | 1,3 MP | no | unas 6 k | suave |
    | Ahorro | 30 / a demanda | 0,8 MP | no | ≤ 1 k | no |
  - Detección al montar con `gl.getParameter(RENDERER)` de ANGLE: SwiftShader o llvmpipe → Ahorro; Intel HD, UHD o Iris → Equilibrado; GPU dedicada → Cine. Sin WebGL2 → «HUD sin lienzo» (solo DOM).
  - Regulador por p90 del tiempo de fotograma en ventanas de 3 s. Baja primero la escala, luego las partículas y por último el nivel. En `auto` no sube por encima del nivel inicial.
  - El bucle se para con `document.hidden` y va a la mitad de fps con la ventana sin foco.
  - «Reducir movimiento» (la preferencia de la app o `prefers-reduced-motion`): sin secuencia de arranque, parallax ni cámara viva, y con fundidos de 150 ms.
  - Nunca hay destellos de más de 3 Hz. `backdrop-filter` está prohibido en Jarvis.
- **Alternativas descartadas:** fps y resolución fijos (fallan en 4K o en una iGPU cargada); `EffectComposer` con `UnrealBloomPass` (5 mips, demasiado caro).
- **Motivo:** cumplir los presupuestos medibles en el hardware real.
- **Impacto:** `QualityTier` y `QualityProfile` en `jarvis/stage/types.ts` y `jarvisQuality` en las preferencias (J0). Las cifras son objetivos: las mide W3 en la UHD 620 dentro del lock de medición.

## [2026-11-26] Modo Jarvis: la CSP no cambia
- **Contexto:** el 3D, los shaders, las fuentes y los recursos de Jarvis deben convivir con la CSP única del renderer (`desktop/electron/shared/csp.ts`).
- **Decisión:**
  - No se toca la CSP. Three.js, los shaders y las texturas procedurales no necesitan nada más (comprobado con el avatar 3D).
  - Prohibido en Jarvis: workers `blob:` (troika-three-text, `DRACOLoader`), que bloquea `default-src 'none'`; fuentes y recursos remotos; y librerías con `eval` o `new Function`.
  - El texto 3D, si hace falta, va con fuentes MSDF precalculadas servidas desde `'self'`. Un worker propio desde un archivo de `'self'` sí está permitido.
  - Los títulos de documentos y los recuerdos se pintan siempre como texto plano, también en texturas.
- **Alternativas descartadas:** abrir `worker-src blob:` o recursos remotos «por si acaso».
- **Motivo:** mantener la superficie de seguridad del renderer.
- **Impacto:** todos los paquetes W de Jarvis. La comprobación se hace en la build `app://`, no solo en desarrollo.

## [2026-11-26] W4: el avatar como capa del Stage (`createAvatarLayer`)
- **Contexto:** el modo Jarvis dibuja todo en un único lienzo WebGL (jarvis-arquitectura.md §2.5 y §4.4). El avatar no puede crear su propio renderer ni su propio bucle.
- **Decisión:**
  - **Una sola implementación por avatar**: la capa es el núcleo y `createAvatar` es su envoltorio. En Ascuario, `layer.ts` (`createAscuarioLayer`) cumple `AvatarLayer`; `index.ts` pone el renderer, el bucle de 30 fps con pausa por `document.hidden` y la entrada de ratón, y llama a la capa con el lienzo completo. `scene.resize` ya no toca el renderer. `entry.ts` exporta `create` y `createLayer`, y el registro gana `loadLayer`.
  - En `render(dt, viewport)`, la capa fija su viewport y su scissor (convirtiendo el origen arriba-izquierda del contrato a la convención de Three) y limpia **solo la profundidad** dentro de su recuadro, para que las capas de debajo no la tapen. Aplica su tone mapping (ACES, exposición 1,15) y al terminar restaura viewport, scissor, scissor test y tone mapping. No limpia el color.
  - `jarvis/stage/layers/avatar.ts`: `createAvatarStageLayer({ load, viewport, order?, transparent? })` es un `StageLayer` genérico, sin saber qué avatar es. El recuadro se pide en cada fotograma, porque lo decide el HUD. El puntero del Stage (y hacia arriba) se convierte en `lookAt` respecto al recuadro, y `reducedMotion` sale del fotograma. Expone `controls` estables, que guardan el último estado hasta que la capa existe, y `failed()`. Si el avatar no carga, el Stage sigue y queda aviso. Por defecto `transparent: true` y `order` 50.
  - `avatars/wiring.ts` (`useAvatarWiring`): los mismos cables que `ThreeCharacter` (estado, voz real, foco y blur, escritura) para cualquier anfitrión. `ThreeCharacter` no se toca.
  - `types.ts` aclara que la `y` de `lookAt` es positiva hacia abajo (lo que ya hacía Ascuario). `avatars/README.md` documenta cómo debe exponer la capa un avatar nuevo (el holográfico).
- **Alternativas descartadas:**
  - Que el Stage fije viewport y scissor y la capa confíe en ello: el contrato no lo garantiza, y fijarlos en la capa es barato y robusto.
  - Bajar el avatar a 24 fps en Ahorro dentro de la capa: con un solo bucle, saltarse fotogramas dejaría el hueco vacío tras el `clear` del Stage. Lo decide el Stage.
- **Motivo:** el avatar holográfico se escribe una vez y sirve en Drakter y en Jarvis.
- **Impacto:**
  - Código: `desktop/src/character/avatars/{types,registry,wiring}.ts`, `avatars/README.md`, `avatars/ascuario/{layer,index,entry,scene}.ts` y `desktop/src/jarvis/stage/layers/avatar.ts`. Sin cambios en `jarvis/stage/types.ts` ni en el resto del Stage (W3).
  - Comprobado en Electron con un Stage mínimo temporal (renderer compartido, `autoClear = false`, fondo, avatar en un recuadro de 420 px y una capa de primer plano a pantalla completa):
    - Ascuario se dibuja en su recuadro, cambia de estado, abre la boca con nivel 1 y sigue al puntero. Arranque de la capa en 843 ms, con la malla y la compilación incluidas.
    - Después de la capa, `toneMapping` = 0, `scissorTest` = false y el viewport a lienzo completo.
    - El modo Drakter se ve igual: con `ACTIVE_AVATAR = null`, SVG y sin Three; con `'ascuario'`, la misma imagen que antes del cambio, sin avisos.

## [2026-11-26] Modo Jarvis W1+W6: shell, activación y bandeja
- **Contexto:** primer paquete de implementación del modo Jarvis sobre los contratos J0 (PR #36).
- **Decisión:**
  - `App` monta `SessionHosts` (voz, feed de notificaciones, atajos comunes y peticiones de modo), `ModeRoot` (un solo shell salvo en la transición), `ConfirmationHost` y `Toaster`. Los dos últimos son comunes, porque una confirmación puede llegar estando en Jarvis.
  - `AppShell` conserva solo lo suyo: `Ctrl+\`, `Ctrl+K` (su paleta) y la precarga de secciones. `Ctrl+0…9` y `Ctrl+Shift+J` pasan a `useGlobalShortcuts`.
  - Jarvis se superpone en `fixed inset-0 z-40`, por debajo de diálogos y avisos, y Drakter queda `inert` hasta que desaparece. Al volver, el foco va al botón de cabecera. El cambio se anuncia con `role="status"`.
  - Si el chunk o el shell de Jarvis fallan, `JarvisBoundary` vuelve a Drakter con aviso: `settleUiMode('failed')`, o `resetUiMode()` si ya estaba en Jarvis. `resetUiMode()` es un añadido a `stores/uiMode.ts`.
  - `JarvisShell` es un stub: fondo CSS estático (sin lienzo ni bucle), estado real del agente y «Volver a Drakter».
  - Entradas: botón de cabecera (precarga al pasar por encima), `Ctrl+Shift+J`, acción «Abrir modo Jarvis» en `Ctrl+K`, sección «Modo Jarvis» en Configuración (abrir, al arrancar y calidad gráfica) y bandeja «Alternar modo Jarvis» (`ui:mode-toggle`, que además enfoca la ventana).
  - El texto de la bandeja es fijo, porque el renderer no informa a main del modo.
- **Alternativas descartadas:** dejar `ConfirmationHost` dentro de `AppShell` (en Jarvis no se verían las confirmaciones); una etiqueta de bandeja dinámica (otro canal IPC renderer→main sin necesidad).
- **Motivo:** que cambiar de modo no corte la voz ni pierda confirmaciones, con Drakter igual que antes.
- **Impacto:**
  - Código: `desktop/src/app/{App,AppShell,ModeRoot,SessionHosts,JarvisModeButton,useGlobalShortcuts,useAppShortcuts}`, `desktop/src/jarvis/JarvisShell.tsx`, `desktop/src/settings/{JarvisSection,SettingsPage}.tsx`, `desktop/src/modules/search/SearchPalette.tsx`, `desktop/src/stores/uiMode.ts` y `desktop/electron/main/tray.ts`.
  - Lo que se carga al arrancar crece +1,0 KB de JS y +0,46 KB de CSS con gzip (+7,8 KB sin comprimir). El stub va en un chunk aparte de 1,96 KB.
  - Comprobado en Electron real (`DISPLAY=:0`), en una instancia aislada con perfil, datos y `HOME` propios y la voz desactivada: 13 de 13 pasos, sin excepciones ni errores de consola.
  - Sin comprobar de extremo a extremo: que la voz no se corte al cambiar de modo. Está garantizado por estructura (`VoiceHost` vive fuera de `ModeRoot`) y falta probarlo con la voz real.
