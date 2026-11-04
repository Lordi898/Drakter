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
- **Comprobado el 2026-11-04 en esta máquina:** `lspci` solo lista la Intel UHD 620, `nvidia-smi` no existe, `MemTotal` da 15.589.436 kB y `lscpu` da 8 CPU. La rama `drakter/verificacion` no tiene commits propios, así que no sirve de evidencia.
- **Sin comprobar:** si el destino final es otra máquina con 32 GB y GPU. Esto solo puede confirmarlo el usuario; si lo es, se reabre esta entrada.
- **Alternativas descartadas:** conservar 32 GB y 4 GB como objetivo (llevaría a elegir modelos que aquí no se pueden medir).
- **Motivo:** la orden del usuario fija estos frenos, y dimensionar con datos que no se han medido produce decisiones falsas.
- **Impacto:** `CLAUDE.md` §2 y §5, `MASTER_PLAN` Parte IX, `IMPLEMENTATION_STATUS.md` Checklist 17.

## [2026-11-04] Python 3.12 para el backend, con Hermes y OpenViking en entornos propios
- **Contexto:** ningún plan fijaba versión. El sistema trae Python 3.14.4 y 3.12.16. `drakter/backend-base` declara `requires-python = ">=3.12,<3.13"`. El dossier verificó en el código de Hermes v0.22.7 que Hermes se instala con Python 3.14 mediante su gestor (3.14.9) y que el servidor privado de OpenViking excluye 3.14.
- **Decisión:** Python 3.12 es obligatorio para `backend/` y para todo el código propio que corra en su entorno. Hermes tiene un entorno propio con su versión fijada y OpenViking otro, en 3.12 o 3.13. Ningún entorno se comparte.
- **Sin comprobar:** el instalador de Hermes no se ha ejecutado, y en esta máquina faltaba `curl`, que es requisito suyo.
- **Alternativas descartadas:** forzar 3.12 en todo (Hermes solo tiene soporte en 3.14); un solo entorno para todo (mezcla dependencias de licencias y ritmos distintos).
- **Motivo:** 3.12 es la versión que usa el código ya escrito, y la separación por proceso es la que exige la integración con Hermes.
- **Impacto:** `CLAUDE.md` §1 y §9, `ROADMAP`, `backend/pyproject.toml` (ya alineado).

## [2026-11-04] Los 14 archivos de identidad viven en agent/identity/
- **Contexto:** `MASTER_PLAN` y `ROADMAP` los repartían en `identity/`, `context/` y `knowledge/`. `PLAN_DISEÑO` los ponía en `~/.hermes/` y `config/`, y `CLAUDE.md` §8 solo cita `agent/identity/`. El commit `c487985` de `drakter/identidad-personaje` los creó los 14 en `agent/identity/` (C-14).
- **Decisión:** los 14 archivos están en `agent/identity/`: `SOUL`, `PERSONALITY`, `BEHAVIOR`, `COMMUNICATION`, `EMOTIONAL_STYLE`, `VALUES`, `USER`, `ENVIRONMENT`, `PREFERENCES`, `CURRENT_CONTEXT`, `CAPABILITIES`, `WORKSPACE_GUIDE`, `TOOL_GUIDE` y `SYSTEM_GUIDE`, todos `.md`. `agent/context/` y `agent/knowledge/` no existen. La fuente es el repositorio: un cargador compone esos archivos y los publica en el `HERMES_HOME` de un perfil propio, y comprueba el tope de 20.000 caracteres de los archivos de contexto de Hermes, porque un recorte podría eliminar reglas del centro.
- **Sin comprobar:** la carga real en Hermes.
- **Alternativas descartadas:** mantener tres carpetas (rompería lo ya escrito sin beneficio); `~/.hermes/` como fuente (dejaría la personalidad fuera del repositorio).
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
- **Decisión:** se mantiene el orden, y se aclara su lectura como hace `agent/identity/SYSTEM_GUIDE.md`: los niveles 1 a 5 enmarcan la instrucción actual; la memoria y los datos no confiables solo informan y nunca dan órdenes; el nivel 7 es lo que hay que hacer dentro de ese marco. Si la memoria contradice al usuario, vale lo que dice ahora y se señala la discrepancia. Para datos operativos, la fuente es el Workspace.
- **Alternativas descartadas:** intercambiar los niveles 6 y 7 (cambiaría una regla de `CLAUDE.md` §8 que no está mal, solo mal explicada).
- **Motivo:** cerrar la lectura peligrosa sin alterar la regla.
- **Impacto:** `CLAUDE.md` §8, `MASTER_PLAN` §8.3. La barrera real la impone el backend, no este texto.

## [2026-11-04] Huecos de MASTER_PLAN §19: borrar o mover archivos y listar hábitos
- **Contexto:** `MASTER_PLAN` §19 no tiene herramienta para eliminar o mover recursos ni para listar hábitos, aunque §24 clasifica esas acciones. `agent/identity/TOOL_GUIDE.md` lo señala como hueco (C-09 y dossier de contratos C-05).
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

## [2026-11-04] agent/identity/USER.md es plantilla; el USER.md vivo es el de Hermes
- **Contexto:** los datos del usuario tenían varias fuentes: `agent/identity/USER.md` y `PREFERENCES.md` en el repositorio, `USER.md` nativo de Hermes y perfil y preferencias de OpenViking (C-15).
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
- **Decisión:** Hermes corre como proceso aparte, supervisado por FastAPI: `hermes gateway run` con API server en loopback, venv y `HERMES_HOME` propios, versión fijada (v0.22.7) y un `AgentProvider` por encima para que el proveedor siga siendo intercambiable. Las herramientas las sirve el backend por MCP en loopback, en un servidor delgado sin lógica de negocio que usa los mismos servicios que la API; Hermes es solo cliente. El perfil lleva lista de permitidos. El backend entrega mensaje y contexto de sesión, y la recuperación de memoria ocurre dentro de Hermes. Skills e identidad tienen su fuente en `agent/` y se publican al perfil. Sigue sin importarse `AIAgent` en FastAPI.
- **Sin comprobar:** nada de esto se ha ejecutado; proviene de leer el código de v0.22.7. Quedan por probar la lista de permitidos real, el nombre visible de las herramientas MCP, si puede bloquearse del todo la escritura de Skills y la RAM consumida.
- **Alternativas descartadas:** importar `AIAgent` en FastAPI (rompe la separación de procesos y mezcla dependencias); Skills que llaman a la API (no valen como frontera de herramientas).
- **Motivo:** el modelo y Hermes se tratan como no confiables; la frontera real es el backend. Esto invierte `MASTER_PLAN` §28.
- **Impacto:** `CLAUDE.md` §2, `MASTER_PLAN` §28 y Parte XII, `ROADMAP`. `agent/identity/SYSTEM_GUIDE.md` (paso 2 del flujo) dice aún que el backend recupera los recuerdos: lo corrige su propietario.

## [2026-11-04] Memoria sin pipeline propio ni recuerdos en el repositorio
- **Contexto:** `MASTER_PLAN` §11, `ROADMAP` y la Checklist 12 seguían pidiendo archivos de recuerdos en `memory/` y una extracción propia, en contra de la decisión de memoria nativa + OpenViking (C-05, C-11, C-12, C-16, C-17).
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
  - **Alcance v1:** paneles y automatizaciones avanzadas quedan fuera, con un mínimo local que dispara recordatorios. Sin Recharts ni Docker hasta necesitarlos. SQLAlchemy + Alembic para el modelo de datos.
  - **Credenciales:** un único origen, `~/.config/drakter/.env`.
  - **Rive:** el personaje provisional cubre el trabajo por código, y las casillas del `.riv` llevan ⚠️ hasta que el usuario lo diseñe.
- **Alternativas descartadas:** marcar el paso 5 como hecho con el mock (`ROADMAP` lo prohíbe y `CLAUDE.md` §2 también).
- **Motivo:** `CLAUDE.md` §2 pide anotar lo bloqueado y seguir, y §8 no admite excepciones en automejora.
- **Impacto:** `IMPLEMENTATION_STATUS.md`, `MASTER_PLAN` Partes X y XI, `ROADMAP` Fases 18 y 19, `PLAN_DISEÑO`.

## [2026-11-04] Contratos de datos que resuelve drakter/contratos
- **Contexto:** quedan conflictos de esquema y de catálogo que son decisiones de contrato: catálogo de herramientas y Skills (C-09, C-10), entidades y campos (C-23, C-24), pertenencia (C-25), estados (C-26), tipos de relación (C-27), calendario (C-28), asignaturas (C-29), hábitos (C-30), auditoría (C-31), permisos (C-34) y FTS (C-18).
- **Decisión:** los planes no los resuelven: remiten al contrato. Cuando `drakter/contratos` publique, su entrada en este archivo y su contrato prevalecen sobre las listas de los planes. Criterios fijos ya: fuente única de pertenencia, toda eliminación confirma, y el agente no modifica permisos.
- **Estado:** RESUELTA EN PARTE por la entrada "Eventos WebSocket resueltos en contracts/". Sigue pendiente lo que allí se indica.
- **Alternativas descartadas:** decidir el esquema desde documentación (un frente lo tiene asignado, y haría dos contratos).
- **Motivo:** evitar dos fuentes.
- **Impacto:** cabecera de los tres planes.

## [2026-11-04] Eventos WebSocket resueltos en contracts/
- **Contexto:** `drakter/contratos` publicó el commit `061975a` con `contracts/README.md`, `contracts/python/drakter_contracts/events.py` y las migraciones `0001` a `0010`. Cierra la entrada de eventos pendiente y parte de los contratos de datos.
- **Decisión:** el catálogo de eventos es `contracts/python/drakter_contracts/events.py`, con 32 tipos, y sustituye a las listas de `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4. Hay un único flujo, `WS /api/v1/events`, solo de servidor a cliente. `agent.status_changed` lleva `state` con los 9 estados; `offline` lo deriva la GUI si cae el socket o llega por `system.health_changed`. `agent.confirmation_required` pasa a ser `confirmation.requested`. Esquema, formatos, errores, reglas de datos, confirmaciones y migraciones siguen `contracts/README.md` y `backend/migrations/`. Si contradicen esta bitácora, manda la bitácora, como dice ese README.
- **Expresiones:** el objeto que genera el modelo sigue sin campo `expression` y la elige en `animation`. El evento `agent.expression_changed` la transporta en `expression`, de modo que el backend hace esa traducción.
- **Pendiente:** a fecha de `061975a` no existen `contracts/tools/catalog.json`, `contracts/api/routes.md`, `contracts/python/drakter_contracts/models/` ni `contracts/ts/`, que el README anuncia. El catálogo de herramientas y Skills sigue abierto, y con él los huecos de `MASTER_PLAN` §19.
- **Sin comprobar:** `contracts/` no está fusionado en `drakter/docs`, y esta entrada procede de leer la rama. `expression` es `str` y no un enumerado, así que el catálogo cerrado de 7 aún no lo impone el contrato. La traducción de `animation` a `expression` no se ha visto implementada.
- **Alternativas descartadas:** copiar el catálogo a los planes (crearía una segunda fuente).
- **Motivo:** un solo contrato.
- **Impacto:** remisiones de `MASTER_PLAN` §6.5, `PLAN_DISEÑO` §6.4 y `ROADMAP` §5.4.

## [2026-11-04] Interfaz del renderer y confirmación por REST
- **Contexto:** el orquestador comunica cómo queda el puente Electron frente al borrador. Las referencias D-13 y D-14 solo constan en comentarios de `desktop/electron/shared/` de las ramas `drakter/electron-host` y `drakter/chat-personaje`, no en este archivo.
- **Decisión:** la interfaz del renderer es `window.api.call(method, path, body)`, en lugar del `api.call(opId, args)` del borrador, y conserva la lista cerrada `ALLOWED_ROUTES` de D-14: main rechaza lo que no esté en ella y el renderer no conoce puerto ni credenciales. Se añaden `getConnection` y los resultados `conflict` y `failed` (D-13). En REST, una operación que necesita confirmación responde 409 con `error.code = "confirmation_required"`, igual que `contracts/python/drakter_contracts/errors.py`, nunca 2xx.
- **Estado:** el token HMAC de confirmación es PROVISIONAL, pendiente del plan definitivo. `contracts/` no lo define.
- **Alternativas descartadas:** `api.call(opId, args)`, el borrador anterior.
- **Motivo:** decisión del orquestador; no se han recibido más motivos.
- **Impacto:** `desktop/electron/`, contrato de rutas. No se ha comprobado en ejecución.
