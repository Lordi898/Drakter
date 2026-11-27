# dev-llm-stub

Servidor local **solo de desarrollo** que imita la API Anthropic Messages con respuestas guionizadas. Permite probar Hermes de extremo a extremo sin red y sin clave.

> **No es un modelo.** Un resultado obtenido aquí demuestra el cableado de Hermes, nunca el comportamiento de Claude Haiku 5.5. Esa verificación sigue pendiente hasta tener clave real.

## Garantías

- Escucha solo en `127.0.0.1`; no hay opción para cambiarlo. Rechaza con `403` cualquier cabecera `Host` que no sea de loopback.
- Marca DEV en todo: texto con `[DEV-STUB]`, modelo `drakter-dev-stub`, cabecera `X-Drakter-Dev-Stub: true`, identificadores `msg_devstub_*` y `toolu_devstub_*`, y logs con `[DEV-STUB]`.
- No arranca con `DRAKTER_ENV=production` o `prod` (código de salida 3). Solo mira el entorno del proceso: no lee `.env` a propósito, porque ahí viven los secretos.
- `{{sandbox}}` debe ser una ruta absoluta simple de dos o más niveles; si no, no arranca.
- No contiene ni pide claves. Ignora las cabeceras de autenticación y no registra cabeceras ni cuerpos.
- Determinista: la misma petición produce la misma respuesta. Solo usa la biblioteca estándar de Python.

## Uso

```bash
python3 tools/dev-llm-stub/server.py --var sandbox=/ruta/de/pruebas
```

Configura Hermes con un `HERMES_HOME` propio, nunca el del usuario:

```bash
hermes config set model.provider custom
hermes config set model.api_mode anthropic_messages
hermes config set model.base_url http://127.0.0.1:28500
hermes config set model.default drakter-dev-stub
```

No uses `provider: anthropic` con este `base_url`: Hermes lo descarta si la ruta no acaba en `/anthropic` y la petición iría a `api.anthropic.com`.

Elige el escenario con una marca en el mensaje del usuario:

```bash
hermes chat -q "[stub:herramienta-permitida] prueba" -t file
```

Sin marca se usa `conversacion` (cámbialo con `--default-scenario`).

## Escenarios

| Escenario | Qué hace | Toolsets |
|---|---|---|
| `conversacion` | Respuesta de texto | cualquiera |
| `herramienta-permitida` | `read_file` y respuesta con el resultado | `file` |
| `herramienta-no-permitida` | Pide `terminal` sin que Hermes la ofrezca | `file` |
| `accion-destructiva` | `rm -rf {{sandbox}}/canario` | `terminal` |
| `inyeccion-documento` | Lee un documento con inyección y simula un modelo que obedece | `file,terminal` |

Los dos últimos solo afectan a `{{sandbox}}`, que es obligatorio pasar con `--var`. Si un escenario responde `FALLO`, una barrera no actuó.

## Formato

Cada `scenarios/<nombre>.json` lleva `description` y `steps`. El paso se elige por el número de rondas de herramienta desde el último mensaje del usuario.

```json
{
  "text": "Texto del paso. {{tool_result}} es el último resultado.",
  "tool_calls": [{"name": "read_file", "input": {"path": "{{fixtures}}/nota.md"}}],
  "branches": [{"contains": "BLOCKED", "text": "Sustituye al paso si el resultado contiene ese texto."}]
}
```

- Cada paso necesita `text` o `tool_calls`. Las ramas admiten lo mismo.
- `allow_missing: true` emite la llamada aunque Hermes no ofrezca esa herramienta.
- Sin `allow_missing`, una herramienta no ofrecida produce un aviso de escenario no aplicable, no un falso bloqueo.
- Variables: `{{fixtures}}`, `{{tool_result}}`, `{{result_<clave>}}` (el primer `"clave": "valor"` del último resultado, por ejemplo `{{result_guide_id}}`) y las de `--var`.
- Las peticiones sin herramientas, como las de título de sesión, reciben una respuesta auxiliar y no avanzan el guion.

## Comprobación con Hermes real

```bash
tools/dev-llm-stub/check_hermes.sh <venv-de-hermes> <directorio-de-trabajo>
```

Corre los cinco escenarios con un `HERMES_HOME` temporal y comprueba que el canario sigue intacto.

## Límites

- No emula bloques `thinking`, firmas, reglas de parámetros ni rechazos de Haiku 5.5.
- `hermes chat -q` deniega por no haber nadie presente, de modo que el `BLOCKED` es el bloqueo desatendido, no una confirmación mostrada al usuario. Este banco no prueba el camino en que un usuario aprueba una acción y esta se ejecuta.
- Las barreras probadas son las de Hermes. Las del backend de Drakter deben comprobarse cuando existan sus herramientas.
