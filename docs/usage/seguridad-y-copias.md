# Seguridad y copias de seguridad

> **Estado:** integrado en `drakter/integracion` (`2e05ba6`): diálogo nativo (`desktop/electron/main/approvals.ts`), confirmaciones (`api/confirmations.py`), actividad (`api/activity.py`), copias en Configuración y `backend/app/database/{backup,cli}.py`. En la pasada de cierre un borrado sin confirmar respondió 503 en vez de 409, y `GET /api/v1/audit` no existe. Las notas «Pendiente» del cuerpo se escribieron sobre `drakter/build` (`2da8bef`) y alguna puede estar ya resuelta. NO COMPROBADO en la app real (ver «Estado de la integración» en [README](README.md)).

Drakter pide tu confirmación antes de acciones destructivas, registra lo que hace el agente y te deja hacer copias de tu base de datos y restaurarlas.

## Confirmaciones

Piden confirmación: el borrado definitivo, las operaciones masivas (por encima del ajuste `bulk_threshold`), los cambios de configuración sensible y las escrituras de un turno contaminado por contenido no confiable.

1. El agente pide la acción y el backend crea una confirmación con un resumen (por ejemplo, "Vas a eliminar 1 tarea: «...». Esta acción no se puede deshacer."), cuántos elementos afecta y cuándo caduca.
2. En el chat aparece un aviso "Drakter necesita tu confirmación" con un temporizador y el botón **Revisar**. El aviso no tiene botones de aprobar ni rechazar.
3. La decisión se toma en un diálogo nativo del proceso principal de Electron (título "Confirmar acción", botones **Cancelar** y **Aprobar**; Cancelar es la opción por defecto). Muestra el resumen, "Elementos afectados" y, si existe, el riesgo. NO COMPROBADO en ejecución. En 2da8bef el diálogo llama a `/api/v1/confirmations/{id}` y el backend de `build` aún no sirve esa ruta.
4. Al aprobar se ejecutan exactamente los argumentos guardados, una vez. Si los elementos han cambiado, sale "Los elementos han cambiado; la acción no se ha ejecutado."
5. Si caduca, no se ejecuta nunca. Por voz no se confirma: solo en la interfaz.

El agente no puede aprobar ni rechazar: su token no vale para esa ruta.

## Permisos

Cada herramienta tiene permiso `<dominio>.<accion>` y riesgo `read`, `write` o `confirm`. El agente nunca puede, ni con confirmación: ampliar permisos, alterar la auditoría, gestionar las ubicaciones permitidas del almacén ni ejecutar comandos arbitrarios. Las ubicaciones del almacén solo se gestionan desde la interfaz.

## Auditoría

Toda llamada del agente queda registrada en la tabla `audit_events` (también lecturas), sin contenido de documentos ni claves. Los parámetros se guardan por lista blanca; el resto se omite. El registro solo se añade, no se edita.

No hay pantalla de auditoría en 2da8bef. En `build` existen la tabla `audit_events` (migración 0008) y escrituras desde ajustes, hábitos y calendario; la consulta (`list_events`) solo está en `drakter/seguridad`. **Pendiente:** ruta o pantalla para que la consultes tú.

## Copias de seguridad

Se guardan en `backups/` dentro del directorio de datos de la app. En Linux es, por defecto, `~/.local/share/drakter/backups/` (ruta de `platformdirs`; NO COMPROBADO en tu máquina). El directorio de datos se cambia con `DRAKTER_DATA_DIR` (ruta absoluta; figura en `backend/.env.example` y en `backend/app/core/config.py`). La base está en `drakter.db` en ese mismo directorio.

Cada copia es un único archivo `drakter-<fecha>-<etiqueta>.db` (permisos 0600, directorio 0700). Se verifica la integridad al crearla. En 2da8bef ya no hay archivo `.sha256`.

**Desde la pantalla:** Ajustes, sección "Copias de seguridad". El botón **Crear copia ahora** crea una copia manual y la lista muestra fecha, tipo y tamaño. La pantalla no restaura: dice que se hará desde ahí "cuando esté disponible con confirmación".

**Desde la terminal** (en `backend/`, con el entorno de Python del proyecto):

```
python -m app.database.cli backup
python -m app.database.cli restore <archivo>
```

`backup` imprime `copia: <ruta>`. `restore` acepta un nombre suelto, que se busca en `backups/`, o una ruta, que debe quedar dentro de `backups/`. También existen `status` y `migrate`. La API usa `GET` y `POST /api/v1/settings/backups`.

## Restaurar: qué sobrescribe

Restaurar **sobrescribe toda tu base de datos actual** (tareas, proyectos, hábitos, calendario, memoria, propuestas, auditoría...) con el contenido de la copia. No toca los archivos del almacén.

1. Cierra Drakter antes de restaurar. NO COMPROBADO qué pasa con el backend en marcha: el código de 2da8bef ya no lo comprueba.
2. Ejecuta `python -m app.database.cli restore <archivo>`.
3. Antes de sobrescribir, se crea una copia con etiqueta `pre-restore`: es tu vuelta atrás. El comando muestra `copia previa: <ruta>`.
4. Al terminar imprime `restaurada`.

Se rechaza una copia que no sea un archivo SQLite regular, que esté en modo WAL, que falle `integrity_check`, que sea un enlace simbólico o que quede fuera de `backups/`. Si falla a medias, el error indica la copia previa. Ya no hay cuarentena ni comprobación de `.sha256` (eso era de `drakter/backend-base`).

## Problemas frecuentes

- `error: ...` y código 1 en la CLI: copia no verificable, enlace simbólico o fuera de `backups/`.
- "No se pudo crear la copia de seguridad": se muestra el motivo en una notificación.

## Pendiente

- Pantalla de auditoría y restauración desde la interfaz: no existen en 2da8bef. Rutas de confirmaciones y auditoría del backend: solo en `drakter/seguridad`. NO COMPROBADO todo el flujo.
