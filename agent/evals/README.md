# Evaluaciones del agente (`agent/evals/`)

Escenarios de **selección de herramientas**, **operaciones encadenadas** (Checklist 13) y **consistencia de personalidad** (Checklist 4). El mismo juego corre contra el stub de desarrollo, sin clave, y contra Claude Haiku 5.5 cuando exista.

> **Con el stub se prueba la tubería, no el modelo.** El stub repite un guion escrito aquí: que un caso pase solo dice que identidad, catálogo, bucle de herramientas y calificador funcionan. Ningún resultado del stub es evidencia de selección de herramientas, de encadenado ni de personalidad. Las casillas de modelo siguen ⚠️ hasta ejecutar con clave.

## Qué se ejecuta

```bash
# Sin clave. Intérprete con el SDK de requirements.txt.
python agent/evals/run.py --check            # valida escenarios, no ejecuta nada
python agent/evals/run.py                    # stub: casos + controles negativos

# Con clave, cuando exista. Exporta la clave en tu shell; el arnés no lee ningún .env.
python agent/evals/run.py --provider anthropic --repeat 3
python agent/evals/run.py --provider anthropic --suite personalidad --case <id>
```

Salida: `report.json` y `report.md` en un directorio bajo `$TMPDIR` (o `--out`). Códigos: `0` bien, `1` algún fallo, `2` bloqueado (sin credenciales o escenarios inválidos).

Cada caso ofrece al modelo las herramientas de `schemas/tool_inputs.json` (esquemas reales; regenerar con `tools/extract_schemas.py`) y como `system` las reglas de seguridad más `agent/identity/` en el orden de `home.py`. Antes de integrar, catálogo, stub y reglas se leen de sus ramas (`git show`); después, del árbol.

## Por qué los casos llevan controles negativos

Un caso guionizado acierta por construcción, así que su `ok` no demuestra nada. Por eso cada caso trae `controls`: guiones que se portan mal a propósito. La tubería solo está bien si el calificador **falla cada control por la regla esperada**, y además toda regla de `grader.py` debe tener al menos un control que la haga saltar.

## Etiquetado de la evidencia

`evidence` se decide por lo que vuelve (cabecera `X-Drakter-Dev-Stub` o modelo `drakter-dev-stub`), no por un parámetro: un stub nunca figura como modelo, tampoco con `--provider anthropic --base-url <loopback>`. Lo que una regla no puede decidir (humor, criterio, tono) va en `rubric`: se imprime para lectura humana y **nunca cuenta como aprobado**.

## Formato de un caso

`scenarios/<suite>.json`: `{"suite", "checklist", "cases": [...]}`.

```json
{
  "id": "sel-crear-tarea",
  "title": "Texto corto",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "user": "Apúntame entregar la práctica el viernes",
  "tools": {"search_tasks": [{"status": "ok", "data": {"items": [], "total": 0}}]},
  "expect": {
    "sequence": [{"tool": "create_task", "args": {"title": {"$contains": "práctica"}}}],
    "any_of": [[{"tool": "..."}], [{"tool": "..."}]],
    "exact": false,
    "forbidden": ["delete_task"],
    "no_tools": false,
    "must_include": [["viernes", "13"]],
    "must_not_match": ["(?i)hecho"],
    "max_sentences": 2,
    "style_off": ["style.tech_leak"]
  },
  "rubric": ["Línea para el lector humano."],
  "script": [{"text": "...", "tool_calls": [{"name": "create_task", "input": {"title": "..."}}]}, {"text": "Anotado. Vence el viernes."}],
  "controls": [
    {"id": "tool-errada", "why": "Qué mal comportamiento simula", "expect_rule": ["tool.expected"],
     "steps": [{"text": "...", "tool_calls": [{"name": "create_event", "input": {}}]}, {"text": "..."}]}
  ]
}
```

- `history` es opcional, y los mensajes que trae son de texto plano.
- `tools`: resultados por herramienta, en orden; el último se repite. Sin entrada, el backend falso responde por `risk` del catálogo: `read` lista vacía, `write` `ok` con id, `confirm` `confirmation_required`. Un resultado es un `ToolOutcome` (`ok{data}`, `error{error{code,message,retryable}}`, `confirmation_required{action_id,summary,expires_at}`) o `{"$untrusted": {"source_type", "source_id", "content"}}`, que se expande al sobre `UntrustedEnvelope`. Una herramienta `confirm` jamás devuelve `ok`.
- `sequence`: subsecuencia ordenada, porque un modelo real puede añadir lecturas. `exact: true` exige esas llamadas y ninguna más. `tool` admite una lista de nombres. `any_of` da caminos válidos alternativos, en lugar de `sequence`.
- `args` compara solo las claves indicadas: valor literal, `{"$contains": "x"}` sin distinguir mayúsculas, `{"$any": [...]}`, `{"$present": true}` o `{"$from": "search_tasks.data.items.0.id"}`, que exige el valor de ese camino en el último resultado de esa herramienta.
- `must_include`: lista de grupos; cada grupo necesita una de sus opciones. `must_not_match`: expresiones regulares prohibidas en la respuesta final.
- `script` y `steps` usan el formato del stub (`text`, `tool_calls`, `branches`, `allow_missing`). El último paso debe ser texto. El guion del caso debe pasar el calificador y sus llamadas deben validar contra el esquema real.
- `expect_rule`: reglas que deben saltar en ese control. Lista en `RULES` de `grader.py`.
- Los identificadores en resultados son UUID ficticios; se usan tal cual en el guion, porque `tool.invented_id` comprueba que vinieran de un resultado o del usuario.
- El reloj es fijo: lunes 9 de noviembre de 2026, 10:00, Europe/Madrid.

## Límites

- **No pasa por Hermes ni por MCP.** Es un bucle directo sobre la API de Messages con el mismo `system` y los mismos esquemas. Mide la decisión del modelo, no `mcp_bridge.py`, el `drakter_guard` ni el backend real. Hermes expone los nombres con prefijo `mcp__drakter__`, y aquí son canónicos.
- **El backend es falso.** Devuelve resultados guionizados y solo valida campos obligatorios y desconocidos del primer nivel. La puerta de confirmación que simula no prueba la real; eso se comprueba en `backend/tests/critical/`.
- **Prompt compuesto.** Imita `compose_soul` de `home.py`, más el reloj fijo. Sin `CURRENT_CONTEXT` real, memoria ni contexto por turno. Cuando exista captura del prompt real, úsala con `--system-file`.
- **Sin voz.** No hay aún forma de señalar el canal, así que las reglas de voz de `COMMUNICATION.md` no se evalúan.
- **Consistencia.** Con `--repeat N` cada caso corre en N sesiones nuevas y el informe da los caminos de herramientas distintos. Con el stub siempre sale 1: no significa nada.
- **Reglas de texto.** `style.*` y `must_not_match` son búsquedas de texto: detectan lo prohibido, no prueban que la voz sea buena. Un aprobado mecánico en personalidad no sustituye a leer las respuestas.
- **Esquemas.** 71 de 78 herramientas: las 7 sin código no se ofrecen. `generated_from` indica de qué commits salieron; algunos worktrees estaban sin commitear, así que hay que regenerar tras la integración.

## Coste con clave

Cada turno envía el prompt completo y 71 esquemas. El `system` lleva `cache_control`; el informe da tokens de entrada, salida y caché. Haz antes una pasada con `--suite` y `--case`. Sin cifras hasta medir.

## Estado

| Qué | Estado |
|---|---|
| Tubería con stub | Ver el último `run.py` |
| Selección de herramientas con Haiku 5.5 | ⚠️ pendiente de clave |
| Operaciones encadenadas con Haiku 5.5 | ⚠️ pendiente de clave |
| Consistencia de personalidad con Haiku 5.5 | ⚠️ pendiente de clave y de lectura humana de las rúbricas |
| Paso real por Hermes y MCP | ⚠️ fuera de este arnés |
