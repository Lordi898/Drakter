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

El venv de Hermes es propio, con Python >= 3.14 y `aiohttp`, y debe tener instalado el commit `b200f5bc`. El preflight lo comprueba por commit (`direct_url.json`), no por texto de versión. Un venv incorrecto es FALLA; sin venv, NO COMPROBADO. En ambos casos no se ejecuta ninguna conversación.

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

Cada pasada usa datos, configuración, `HOME` y puertos propios en `$TMPDIR/verify-*`. El entorno se construye por lista blanca, así que ni `~/.config/drakter/.env` ni las claves del entorno llegan a los procesos.

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
