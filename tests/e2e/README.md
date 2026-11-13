# Pasada integrada final

`scripts/verify-all.sh` arranca backend, stub LLM y Electron, recorre conversación, una operación por módulo, confirmación destructiva, copia y restauración, y genera un informe con cada casilla de `docs/IMPLEMENTATION_STATUS.md` como PASA, FALLA o NO COMPROBADO.

**El stub no prueba Claude Haiku 5.5.** Un PASA «con stub» solo prueba el cableado. Lo que depende del modelo real lleva `blocked = "haiku"` en `coverage.toml` y nunca sale PASA aquí.

## Cuándo lanzarla

Al final, con todo integrado en un checkout y los recursos libres. Se niega a arrancar con menos de 1500 MB disponibles (`--min-mem-mb`).

```bash
cd backend && uv sync && cd ..
cd desktop && npm ci && cd ..
scripts/verify-all.sh --hermes-venv /ruta/al/venv-de-hermes
```

El venv de Hermes es propio, con Python >= 3.14 y el commit `b200f5bc` instalado. El preflight lo comprueba por commit (`direct_url.json`), no por texto de versión, y exige el runner `backend/app/integrations/hermes/runner/drakter_runner.py`. No hay gateway. Un venv incorrecto es FALLA; sin venv o sin runner, NO COMPROBADO. En ambos casos no se ejecuta ninguna conversación.

El stub se arranca con los guiones de `tests/e2e/stub-scenarios/`, no con los suyos: estos piden herramientas nativas de Hermes (`read_file`, `terminal`) que el runner de Drakter no ofrece. Los del arnés usan el catálogo real: `list_tags` (lectura), `forget_memory` (CONFIRM) y `search_resources` sobre una nota con inyección que crea la propia comprobación.

`agent.tools` se comprueba desde fuera: un proxy del arnés entre backend y stub registra los `tools[]` de cada petición al modelo, y `conversacion.lista_blanca` exige que todos cumplan `tool_pattern` de `config.toml`.

Si `desktop/out` es anterior a las fuentes, ejecuta `npm run build`, que es una compilación pesada. Con Electron se abre una ventana real en el escritorio mientras dura la pasada, salvo con `--headless`.

| Salida | Significado |
|---|---|
| 0 | Sin ningún FALLA. Puede haber NO COMPROBADO: lee el informe |
| 1 | Algún FALLA |
| 2 | No se ejecutó: falta un requisito, memoria o el mapa no es válido |

El informe queda en `$TMPDIR/report-<fecha>/` (`report.md`, `report.json`, `capturas/`). `TMPDIR` nunca es `/tmp`: por defecto, `/var/tmp/drakter-e2e`. Si algo falla se conservan los logs de la pasada.

## Opciones

| Opción | Uso |
|---|---|
| `--validate` | Valida catálogo y mapa sin arrancar nada |
| `--only PREFIJO` | Solo esas comprobaciones, repetible (`--only data --only parada`) |
| `--no-desktop`, `--no-build`, `--headless` | Sin Electron, sin recompilar o sin ventana en el escritorio |
| `--backend-dir`, `--desktop-dir`, `--stub-dir`, `--backend-python`, `--hermes-venv` | Probar piezas sueltas de otros árboles |
| `--status-file`, `--coverage`, `--out` | Otro documento, otro mapa u otra carpeta de informe |
| `--keep-work` | Conserva datos y logs aunque todo pase |

## Aislamiento

Cada pasada usa datos, configuración, `HOME` y puertos propios en `$TMPDIR/verify-*`. El entorno se construye por lista blanca, así que ni `~/.config/drakter/.env` ni las claves del entorno llegan a los procesos. La configuración del stub va en un `.env` propio de la pasada, porque el host de Electron solo hereda una lista blanca de variables.

## Arranque (D-14)

En la fase sin ventana, el arnés hace el papel de Electron: pasa los tokens `ui` y `approver` por stdin, recibe el puerto por stdout y apaga con EOF. La instancia es exclusiva, así que lo para antes de abrir Electron, que lanza su propio backend sobre los mismos datos. Por eso las comprobaciones de escritorio no usan la API del arnés.

`--no-sandbox` y `--remote-debugging-port` se usan solo aquí: `chrome-sandbox` no es SUID en esta máquina y no hay sudo. Están prohibidos en artefactos, y el sandbox real queda sin probar en esta pasada.

## Reglas del veredicto

- PASA solo sale de una comprobación ejecutada que acertó.
- Una casilla pasa si **todas** sus `checks` pasan. Sin entrada en `coverage.toml` es NO COMPROBADO.
- Un `FALLA` manda sobre un bloqueo; un bloqueo impide el PASA.
- Una ruta ausente en el primer paso de un flujo, o en uno con `unrouted_ok`, es NO COMPROBADO. En los demás pasos es FALLA.
- `[x]` en el documento no cuenta como evidencia; el informe lista las marcadas sin PASA.

## Añadir o ajustar

- **Rutas:** `catalog.toml`. Las marcadas `# PROVISIONAL` hay que confirmarlas con el contrato real.
- **Variables del proveedor del stub:** `config.toml`.
- **Comprobaciones:** `@check` en `scenarios/`.
- **Casillas:** `coverage.toml`. Mapea solo lo que la comprobación prueba entero; un PASA falso es peor que un NO COMPROBADO.
