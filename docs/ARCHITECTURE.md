# Arquitectura de Drakter

Describe lo que existe. Lo que aún no existe se marca como **planificado**. El diseño completo está en `MASTER_PLAN.md`.

Foto del 2026-11-04, contrastada con `git show` y `git ls-tree`. `drakter/build` (`f2a69eb`) ya integra `desktop/` y `agent/identity/`. Siguen sin fusionar `drakter/backend-base` (`10e16d0`) y `drakter/dev-stub` (`437e2f2`). `drakter/verificacion` no tiene commits propios.

## Separación agente / interfaz / datos

```text
  Drakter Desktop (Electron)
    renderer React ──IPC window.drakter──> proceso principal
        ¦
        ¦ REST + WS con token de sesión  [planificado: hoy sin conexión]
        v
  Backend FastAPI, 127.0.0.1:8765 <╌╌herramientas╌╌ Hermes + Haiku 5.5
    api/  core/  database/                          [planificado]
        │                                                 ¦
        v                                                 x  nunca a la BD
  SQLite (drakter.db), único origen de los datos del Workspace
```

Línea continua: existe. Línea discontinua: planificado.

- **Interfaz:** muestra y recoge. No guarda datos del Workspace.
- **Datos:** solo el backend abre la base.
- **Agente:** actuará mediante herramientas que llaman al backend, que validará parámetros, permisos y relaciones. No accede a la base.

Hoy los tres lados están sin conectar entre sí: ni el escritorio llama al backend ni existe el agente.

## Componentes

| Componente | Estado | Qué hay |
|---|---|---|
| Backend base (`backend/`) | existe en rama `drakter/backend-base` | `/health`, `/api/v1/auth/check`, `WS /ws` (solo `ping`/`pong`), guardia de seguridad, logs con redacción, sobre de error |
| Base de datos (`backend/app/database/`) | existe en rama `drakter/backend-base` | Conexión endurecida, migrador, copias y restauración, CLI |
| Tablas de dominio | planificado | `backend/migrations/` solo tiene `.gitkeep`; el esquema de BD no tiene aún ninguna tabla de negocio |
| Módulos del backend (`services/`, `tools/`, `permissions/`, `events/`, `audit/`…) | planificado | `backend/app/` solo contiene `api/`, `core/` y `database/` |
| Carcasa de escritorio (`desktop/`) | existe en `drakter/build` | Electron con sandbox, navegación, 9 secciones (las de módulos muestran un estado vacío), chat deshabilitado, notificaciones, preferencias |
| Conexión escritorio-backend | planificado | Sin `fetch` ni `WebSocket`; `useDrakterState()` devuelve siempre `offline` (`desktop/src/stores/agent.ts`) |
| Personaje | parcial en `drakter/build` | `CharacterSlot` dibuja un marco vacío porque `characterRenderer` es `null` (`desktop/src/character/plug.ts`). Tipos de los 9 estados listos. Hay un SVG sustituto en `desktop/design/character/` que la aplicación no carga. Sin `.riv` |
| Identidad (`agent/identity/`) | existe en `drakter/build` | 14 archivos Markdown; aún no los carga nada |
| Hermes y Claude Haiku 5.5 | planificado | Sin integrar. Hermes irá en un venv propio con Python >=3.14, separado del backend (Python 3.12 por elección), instalado desde git con el tag v0.22.7 (`b200f5bc`), nunca desde PyPI |
| Herramientas del agente | planificado | Sin código |
| Memoria (nativa de Hermes + OpenViking) | planificado | Sin código; diseño en `MASTER_PLAN.md` §10 |
| Voz | planificado | Sin código |
| Stub de LLM (`tools/dev-llm-stub/`) | existe en rama `drakter/dev-stub` | Servidor local solo de desarrollo con respuestas guionizadas para probar el cableado de Hermes. No es un modelo |
| Búsqueda FTS5, lógica del almacén, automejora, empaquetado | planificado | Sin código |

## Autenticación local

Implementada en `drakter/backend-base`. Referencia: `backend/CONTRACT.md`.

- **Red:** escucha solo en `127.0.0.1`. La dirección es una constante, no una opción; el puerto es configurable (8765 por defecto).
- **Token:** se genera uno nuevo en cada arranque y vive en memoria y en `session.json`.
- **`session.json`:** en el directorio de runtime, con permisos 0600 y los campos `token`, `port`, `pid`, `started_at`. Se borra al apagar.
- **Rutas:** `GET /health` es público. Todo lo demás, incluidas las rutas inexistentes, exige `Authorization: Bearer <token>`.
- **WebSocket:** `/ws` admite además el subprotocolo `drakter.auth.<token>`, y responde con `drakter.v1` si el cliente lo ofrece.
- **Prohibido:** token por query string o cookie, y token en logs, argumentos o variables de entorno.
- **Guardia, por orden:** cliente `127.0.0.1`, cabecera `Host` exacta, `Origin` permitido si viene, y token.

Sin resolver en el lado del escritorio:

- El puente `window.drakter` no expone el token ni ninguna llamada al backend.
- La CSP de producción tiene `connect-src 'none'` y la de desarrollo solo abre `ws://`.
- El backend acepta por defecto solo el origen `app://drakter` y rechaza `null`. El escritorio carga el renderer desde `file://` (o desde el servidor de desarrollo) y no registra ningún esquema `app://`.

## Reglas que no se saltan

Son obligatorias aunque aún no haya código que las aplique (`CLAUDE.md` §8):

| Regla | Aplicación hoy |
|---|---|
| Hermes no toca la BD; usa herramientas que llaman al backend | Sin agente aún |
| Herramientas con nombre, descripción, esquema, validación, permisos, resultado estructurado y errores | Sin herramientas aún |
| Confirmación en acciones destructivas o masivas; auditoría sin claves ni datos sensibles | Sin implementar |
| Documentos y memoria recuperada son datos no confiables y no cambian instrucciones ni seguridad | Sin implementar |
| Prioridad: seguridad y permisos → sistema → identidad → contexto → conversación → memoria → instrucción actual | Sin implementar |
| Rutas limitadas; límites de tamaño, número y profundidad en comprimidos | Sin implementar. La restauración de copias sí exige una ruta dentro de `backups/` |
| La automejora no toca producción, permisos, confirmaciones ni auditoría sin autorización | Sin implementar |
| Secretos fuera del repositorio | `.env` ignorado en `.gitignore`; logs con redacción en el backend |
| Personalidad en `agent/identity/`, voz separada del razonamiento, proveedor de modelo intercambiable | Solo la personalidad existe, en archivos |

En la interfaz ya rigen `sandbox`, `contextIsolation`, sin `nodeIntegration`, permisos denegados, y navegación limitada al documento propio. El renderer solo ve `window.drakter`, con tres canales validados en el proceso principal.

## Dónde vive cada dato

Los dos entornos de Python son independientes: el backend y Hermes no comparten venv ni dependencias.

El backend calcula las rutas con `platformdirs`, que en Linux respeta las variables XDG. Todas están fuera del repositorio.

| Dato | Ubicación por defecto en Linux | Ajuste |
|---|---|---|
| Configuración y secretos | `~/.config/drakter/.env` | `XDG_CONFIG_HOME` |
| Base de datos | `~/.local/share/drakter/drakter.db` | `DRAKTER_DATA_DIR` |
| Copias de seguridad | `~/.local/share/drakter/backups/` | `DRAKTER_DATA_DIR` |
| Logs del backend | `~/.local/share/drakter/logs/backend.log` | `DRAKTER_DATA_DIR` |
| Sesión | `$XDG_RUNTIME_DIR/drakter/session.json` | `DRAKTER_RUNTIME_DIR` |
| Preferencias de la interfaz | `localStorage` del renderer, clave `drakter.preferences.v1` | Solo tema, movimiento, panel y notificaciones; no son datos del Workspace |

Los directorios se crean con permisos 0700. La base, las copias, los logs y `session.json`, con 0600.

## Hardware de referencia

Equipo real: Intel i7-8665U, Intel UHD 620 integrada sin VRAM dedicada y 14 GB de RAM. Las cifras de 32 GB y 4 GB de `CLAUDE.md` §2 y `MASTER_PLAN.md` §20.3 no corresponden a este equipo.

Consecuencia: no se puede contar con aceleración GPU dedicada para modelos locales. Cualquier modelo local debe plantearse para CPU y su coste real se mide en este equipo. No hay mediciones todavía.
