---
name: agent-forge
description: Crea, instala o adapta agentes y subagentes de Drakter, y redacta los briefs de delegación. Úsala siempre que vayas a lanzar un subagente con trabajo no trivial, crear un archivo en .claude/agents/, instalar un agente de la comunidad o decidir cómo repartir trabajo entre agentes.
---

# Agent Forge

## Elegir qué desplegar

| Situación | Qué usar |
|---|---|
| Rol puntual | `general-purpose` con el rol en el brief |
| Se repite 3 o más veces | Agente nuevo en `.claude/agents/` |
| Frente con piezas paralelas | `drakter-lider` |
| Ya existe en el catálogo | Reutilízalo; comprueba qué copia se carga si el nombre está duplicado |
| Hay uno mejor en la comunidad | Instálalo con la higiene de `CLAUDE.md` §5 |

## Brief de delegación

El brief es lo único que sabe el agente.

```text
OBJETIVO: resultado concreto, en una frase.
CONTEXTO: lo que necesita saber y lo ya descartado.
CONTRATO: archivo y sección que debe cumplir.
TE PERTENECE: archivos y carpetas que puede editar.
NO TOQUES: zonas de otros agentes.
HECHO CUANDO: comprobación concreta (CLAUDE.md §4).
DEVUELVE: en ≤10 líneas, qué hizo, qué comprobó, qué decisiones tomó.
```

Da al agente el material, no tu conclusión, si lo que quieres es una opinión independiente.

## Crear un agente

Archivo `.claude/agents/<nombre>.md`:

```markdown
---
name: nombre-en-kebab-case
description: Qué hace y cuándo usarlo, con detalle suficiente para distinguirlo.
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

Prompt de sistema: rol, reglas, zona y formato de salida.
```

- `name` debe ser único en todo `.claude/agents/`, subcarpetas incluidas; no puede contener `:` ni empezar por `-`. Si dos archivos comparten nombre, solo se carga uno.
- Da las herramientas justas. Si omites `tools`, hereda todas.
- Para que el agente pueda delegar, incluye `Agent` en `tools`. Si lo omites de la lista, no puede lanzar subagentes.
- Campos útiles: `isolation: worktree`, `background: true`, `effort`, `maxTurns`, `skills`, `memory`.
- `Agent(a, b)` limita a qué tipos puede lanzar, pero solo se respeta en el hilo principal. Dentro de un subagente se ignora.
- Un agente lanzado con `--agent` sustituye el prompt de Claude Code: debe llevar sus propias reglas.
- Los archivos nuevos se detectan en segundos, salvo que `.claude/agents/` no existiera al arrancar la sesión.

## Profundidad

Por defecto hay hasta 3 niveles de subagentes bajo el hilo principal; en el último nivel desaparece `Agent`. Cada nivel debe tener una razón: un sublíder solo compensa si dirige varias piezas paralelas.

## Comprobar

Tras crear un agente: el frontmatter abre y cierra con `---`, el nombre no colisiona (`grep -rn '^name: <nombre>' .claude/agents`) y las herramientas existen. Los agentes y skills nuevos se registran en `docs/DECISIONS.md`.
