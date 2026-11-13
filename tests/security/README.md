# Banco de ataques de Drakter

Intenta romper las garantías de `.claude/CLAUDE.md` §8 contra un backend real. Es una de las excepciones de §4: comprobaciones breves donde un fallo silencioso sería caro. Los hallazgos están en `docs/reviews/red-team.md`.

## Ejecución

Desde la raíz del repositorio:

```bash
TMPDIR=/var/tmp/drakter-red python3 tests/security/run.py \
  --backend backend --python backend/.venv/bin/python
```

| Opción | Uso |
|---|---|
| `--only NET` | Solo los ataques cuyo id empieza por ese prefijo |
| `--contract archivo.json` | Reemplaza claves de `contract.py` |
| `--report archivo.json` | Guarda los resultados |

`TMPDIR` es obligatorio y no puede ser `/tmp`. Cada ejecución arranca `python -m app` en una raíz nueva, con `HOME` y `XDG_CONFIG_HOME` propios, de modo que nunca lee la configuración ni los secretos reales. Sale con código 1 si hay `BREACH` o `ERROR`.

## Veredictos

| Veredicto | Significado |
|---|---|
| `BLOCKED` | El sistema resistió |
| `BREACH` | La garantía se rompió en esta ejecución |
| `NOT_APPLICABLE` | La pieza no existe todavía: no prueba nada |
| `ERROR` | El ataque falló: no prueba nada y hace fallar el banco |

Al integrar, revisa los `NOT_APPLICABLE`: un ataque que sigue en ese estado no protege nada.

## Prefijos

| Prefijo | Archivo | Superficie |
|---|---|---|
| `SMOKE` | `attacks_smoke.py` | Control del propio banco |
| `NET` | `attacks_network.py` | Host, Origin, DNS rebinding, WebSocket |
| `CONF` | `attacks_confirm.py` | Confirmaciones, lista blanca, auditoría |
| `INJ` | `attacks_injection.py` | Documentos y memoria |
| `FILE` | `attacks_files.py` | Rutas, enlaces, comprimidos, copias |
| `LEAK` | `attacks_secrets.py` | Logs, errores, procesos |
| `DESK` | `attacks_desktop.py` | Electron y renderer, por análisis estático |

## Añadir un ataque

```python
from redlib import Context, NotApplicable, attack, expect

@attack("NET-99", "Título", guarantee="Qué garantía defiende")
def mi_ataque(ctx: Context) -> None:
    respuesta = ctx.http("GET", ctx.route("auth_check"), token=False)
    expect(respuesta.status == 401, "entra sin token")
```

Comprueba que el camino atacado se alcanza: un 404 no es un bloqueo. `ctx.route()` ya levanta `NotApplicable` si la ruta no existe. Los nombres que dependen de la integración van en `contract.py`.
