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
- **Contexto:** en el cierre se comprobó que `memories_for_context` + `build_context` no los llama el runner de Hermes, y que olvidar usa `DenyAllGate` (GUI) y `DefaultToolGate` (agente).
- **Decisión:** se cierra la v1 con la memoria accesible al agente solo por herramientas (`search_memory`, `get_memory_item`) y con el olvido fallando cerrado. Quedan con ⚠️ "recuperación selectiva", "límites de contexto" y "memoria de trabajo".
- **Alternativas descartadas:** conectarlo en el cierre (integración nueva en `app/integrations/hermes/` y en el flujo de confirmaciones, fuera del alcance de cierre).
- **Motivo:** el protocolo de cierre solo termina lo empezado.
- **Impacto:** Checklist 12; siguiente paso: llamar a `build_context` en el runner y enchufar `memory.forget` a `app/services/actions.py`.

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
- **Impacto:** `agent/configuration/permissions.json`, `backend/app/tools/improvement.py` (`5dd55b1`, pendiente de fusión); Checklists 13 (permisos, confirmaciones) y 15.

## [2026-11-13] Cierre del almacén: arreglos de integración
- **Contexto:** al integrar `drakter/integracion`, el almacén no funcionaba: `Settings` ya no tiene `runtime_dir`, `untrusted_envelope` se movió a `app.tools.envelope`, el registro de herramientas rechaza claves de `audit` que no son argumentos y `uv.lock` no incluía pypdf.
- **Decisión:** `denied_roots` usa `runtime_dir` solo si existe; `tools/storage.py` importa de `envelope` y filtra `audit` por los campos de cada `args_model`; se regenera `uv.lock` con pypdf; el agente necesita `storage.write` para crear notas (DECISIONS «Almacén en v1»).
- **Alternativas descartadas:** añadir `runtime_dir` a `Settings` (es un archivo compartido y nadie más lo usa); quitar la validación de `audit` del registro (es un control de seguridad).
- **Motivo:** dejar el almacén operativo sin tocar contratos compartidos.
- **Comprobado:** `check_storage_paths.py` 127/127, `check_storage_archives.py` 35/35, `check_storage_catalog.py` y `check_storage_api.py` OK, flujo REST de extremo a extremo 19/19 (rutas denegadas, symlinks fuera de la raíz, SSRF, límites de comprimidos).
- **Impacto:** `backend/app/services/storage_ports.py`, `backend/app/tools/storage.py`, `backend/uv.lock`, `agent/configuration/permissions.json`, Checklist 10.

## [2026-11-13] Prefijo workspace_ en las confirmaciones de los servicios de tareas y proyectos
- **Contexto:** `wiring.py` registraba los ejecutores de `TASK_CONFIRMABLE`/`PROJECT_CONFIRMABLE` con los nombres `delete_task`, `update_task` y `complete_task`, que también son herramientas del agente. `ActionService.approve` prefiere los ejecutores al registro, así que un `delete_task` del agente aprobado nunca llegaba a borrar.
- **Decisión:** las filas de `PendingConfirmationGate` y las claves de los ejecutores de servicio llevan el prefijo `workspace_` (`workspace_delete_task`, `workspace_delete_project`, …). Las herramientas del agente siguen con sus nombres y las ejecuta el registro.
- **Alternativas descartadas:** renombrar las herramientas del agente (rompe el catálogo y la lista blanca); una puerta propia del módulo (segundo camino paralelo a `ActionService`).
- **Motivo:** un nombre identifica una sola acción en `pending_confirmations`.
- **Impacto:** `backend/app/permissions/wiring.py` (`b531106`, pendiente de fusión); Checklist 7 (eliminar tareas, herramientas Hermes).
