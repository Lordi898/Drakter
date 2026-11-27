# Copias de seguridad y actualización

Las copias se guardan en `~/.local/share/drakter/backups/` (o `$DRAKTER_DATA_DIR/backups/`). Cada una es `drakter-<fecha>-<tipo>.db` con su `.sha256`, permisos 600. Copian la base de datos (tareas, proyectos, hábitos, calendario, memoria, auditoría…), no los archivos del almacén.

Las copias se hacen con la CLI del backend. Hay dos formas de llamarla, y las dos hacen lo mismo:

```bash
# Desde el repositorio
cd ~/Drakter/backend && .venv/bin/python -m app.database.cli <orden>

# Con la app instalada (AppImage), sin repositorio
~/.local/opt/drakter/app/resources/backend/drakter-backend -m app.database.cli <orden>
```

Órdenes: `status` (versión del esquema), `backup`, `restore <archivo>` y `migrate`.

## Copia inicial

Hazla en cuanto abras Drakter por primera vez, y otra vez antes de meter datos importantes:

```bash
cd ~/Drakter/backend && .venv/bin/python -m app.database.cli backup
# copia: /home/<tú>/.local/share/drakter/backups/drakter-20261120T190927483073Z-manual.db
```

También puedes hacerla desde **Ajustes → Copias de seguridad → Crear copia ahora**. La copia se puede crear con la app abierta.

Guarda una copia fuera del ordenador (disco externo o nube): copia el `.db` y su `.sha256` juntos.

Las copias guardan lo que había en la base en ese momento. Desde la migración `0016`, cuando una confirmación del modo flotante (usar tus apps, abrir una URL, mirar la pantalla) se cierra, Drakter borra de la base el texto tecleado, la URL en claro y el texto de otras apps, y deja solo sus huellas (hashes). Las copias hechas **antes** de la migración `0016`, o antes de que se redactara esa fila, **conservan ese texto en claro**. Si restauras una de ellas, Drakter vuelve a redactar esas filas al arrancar, pero el archivo de la copia sigue teniendo el texto. Guárdalas como guardarías la propia base y, si ya no las necesitas, bórralas.

## Restaurar

Restaurar **sustituye toda la base actual** por la copia.

1. Cierra Drakter (con la app abierta la CLI responde «La base está en uso por otra instancia de Drakter»).
2. Restaura:
   ```bash
   cd ~/Drakter/backend && .venv/bin/python -m app.database.cli restore drakter-20261120T190927483073Z-manual.db
   # restaurada
   # copia previa: …/backups/drakter-…-pre-restore.db
   ```
   Un nombre suelto se busca en `backups/`. Antes de sobrescribir se guarda la base actual como `pre-restore`: si te equivocas, restaura esa.
3. Abre Drakter.

Se rechaza una copia cuyo contenido no coincida con su `.sha256` («El contenido de la copia no coincide con su hash»), que falle la comprobación de integridad, que sea un enlace simbólico o que esté fuera de `backups/`. La interfaz aún no restaura: solo crea copias.

## Actualizar

```bash
cd ~/Drakter
scripts/update.sh             # desde el repositorio
scripts/update.sh --package   # además reconstruye y reinstala el AppImage
```

Qué hace, en orden:

1. Se niega si tienes cambios sin guardar en el repositorio.
2. `git pull --ff-only` con tus credenciales de git (el repositorio es privado; la app no guarda ningún token).
3. Reinstala solo lo que haya cambiado: `uv sync --locked` (backend), `npm ci` (escritorio), `scripts/install-voice.sh` (si cambió el lock de voz o los contratos) y `scripts/install-hermes.sh` (si cambió la versión de Hermes). Después, `npm run build`.
4. Si Drakter corre con `drakter-local.sh`, lo para.
5. **Copia de la base** y migraciones. Si la copia falla, no migra.
6. Vuelve a arrancar lo que paró (con `DRAKTER_PROVIDER`, por defecto `anthropic`).

Si Drakter está abierto de otra forma (AppImage, `dev.sh`), la migración no se hace en ese momento: se aplica al volver a abrirlo, y el backend hace antes su propia copia `pre-migrate`. Cierra y abre Drakter para usar la versión nueva.

No hay actualización automática dentro de la app: `electron-updater` con un repositorio privado necesitaría guardar un token de GitHub en la app y solo actualiza el AppImage, no el backend ni los runtimes (ver `docs/DECISIONS.md`).
