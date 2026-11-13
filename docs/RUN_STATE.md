# RUN_STATE — Estado de la ejecución de Drakter

Foto operativa de la construcción. El detalle por tareas está en `IMPLEMENTATION_STATUS.md` y los motivos, en `DECISIONS.md`.

## Estado actual (2026-11-13)

- **Rama de integración:** `drakter/integracion`, creada desde `drakter/build` (`815976f`) con las 22 ramas `drakter/*` fusionadas (contratos, backend-base, seguridad, tareas-proyectos, hábitos-calendario, almacén-relaciones, memoria-contexto, agente-hermes, identidad-personaje, voz, automejora, desktop-shell, búsqueda, hoy-ajustes, docs, guías, electron-host, evals, red-team, e2e, verificación, revisión-ux). Ninguna rama `drakter/*` tiene commits fuera de ella. `main` no se ha tocado. Nada publicado.
- **La app arranca** en el escritorio (Electron + backend + Hermes) y las pantallas Hoy, Drakter (chat), Hábitos, Tareas, Proyectos, Almacén, Calendario, Asignaturas, Relaciones y Configuración cargan sin errores de consola.
- **Modelo:** el chat funciona de extremo a extremo con `tools/dev-llm-stub` (respuestas `[DEV-STUB]`). La `ANTHROPIC_API_KEY` de `~/.config/drakter/.env` es rechazada por Anthropic (401 `invalid x-api-key`), así que **no hay prueba con Claude Haiku real**.

## Cómo arrancar y parar

```bash
scripts/drakter-local.sh start          # stub de LLM + app, desacoplados de la terminal
scripts/drakter-local.sh start anthropic  # con Haiku real (necesita clave válida)
scripts/drakter-local.sh status
scripts/drakter-local.sh stop
```

Logs: `/tmp/drakter-dev.log` (Electron y backend, prefijo `[drakter:backend]`), `/tmp/drakter-stub.log`, `~/.local/share/drakter/logs/hermes.log`. Datos: `~/.local/share/drakter/`.

`scripts/dev.sh all` sigue siendo la orden de primer plano; `drakter-local.sh` le añade el stub y las variables de la máquina de desarrollo.

### Requisitos de esta máquina

- `backend/.venv` (Python 3.12): `cd backend && uv sync --frozen`. `uv` está en `~/.local/bin` (instalado con `pip --user`).
- `desktop/node_modules`: `cd desktop && npm ci && node node_modules/electron/install.js` (npm 12 no ejecuta el script que descarga Electron).
- Hermes v0.22.7 (`b200f5b`, Python 3.14) en `/var/tmp/drakter-agente-hermes/hv/venv`, expuesto como `~/.local/bin/hermes-python` (envoltorio de una línea). `/var/tmp` sobrevive a reinicios, pero no es una ubicación definitiva.
- Sandbox de Electron desactivado solo en desarrollo (`DRAKTER_DEV_NO_SANDBOX=1`, `ELECTRON_DISABLE_SANDBOX=1`): AppArmor restringe userns y `chrome-sandbox` no es `root:4755` (requiere `sudo`, ver README).

## Comprobado el 2026-11-13

- `GET /health` → `{"status":"ok"}`; 30 peticiones concurrentes a los módulos → 200.
- Chat desde la GUI: mensaje del usuario y respuesta del agente vía Hermes en ~2 s (con el stub).
- Crear tarea desde el renderer (proxy de Electron) → 201 y aparece en la lista; archivar → 200.
- `backend/tests/critical/check_confirmations.py` (en `drakter/seguridad` antes de fusionar) → 0 fallos.
- `npm run typecheck` sin errores.

## Bloqueos y desajustes abiertos

- **Clave de Anthropic inválida:** sustituirla en `~/.config/drakter/.env` y arrancar con `start anthropic`.
- **Borrar tareas y proyectos desde la GUI:** 503 `confirmation_unavailable` (falla cerrado). Falta cablear `tasks_ports.ConfirmationGate` a `ActionService` y registrar sus ejecutores en `load_confirmed_executors`.
- **Búsqueda global:** `SearchPalette` sigue sin montarse en `AppShell` (Ctrl+K no hace nada).
- **Calendario:** el selector de zona horaria arranca en el primer valor de la lista (`Africa/Abidjan`) mientras `default_timezone` no esté fijado en Configuración.
- **Deriva de catálogo:** el backend avisa (`tool_catalog_drift`) de herramientas que difieren de `contracts/tools/catalog.json`. No bloquea.
- **OpenViking (U-1):** desactivado en v1, con memoria SQLite + FTS5; falta que lo confirme el usuario.
- **Rive:** solo el personaje sustituto.

## Cambios sin commit que no se integraron

Ninguno. Los cambios pendientes de drakter-12, 16, 20, 22, 24, 30 y 31 se revisaron, se comprobaron (py_compile, JSON, check crítico de confirmaciones) y se commitearon en su rama antes de fusionar. drakter-13 y drakter-27 solo tenían `desktop/node_modules` sin rastrear.

## Siguiente paso

1. Clave de Anthropic válida y prueba de conversación y herramientas con Haiku real.
2. Cablear confirmaciones de tareas y proyectos.
3. Montar `SearchPalette`.
