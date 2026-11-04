# Empaquetado de Drakter Desktop

Configuración de electron-builder 26.18.0 (Electron 45, electron-vite 6). Linux primero; Windows preparado pero sin comprobar.
Estado: **configuración escrita, no ejecutada**. Nada de lo de abajo se ha probado todavía (ver "Comprobaciones de la pasada integrada").

Archivos: `electron-builder.yml` (config), `electron-builder.backend.spec` (PyInstaller), `electron-builder.build-backend.mjs` (lanzador del backend).

## Pasos reproducibles

Requisitos: Node con `npm`, `uv` en el PATH (falta en algunas máquinas), y construir **en el SO de destino** (el backend no se cross-compila).

```bash
# 1. Backend congelado -> backend/dist/<linux|win>/drakter-backend/
cd desktop && node electron-builder.build-backend.mjs

# 2. Desktop -> desktop/out/
npm ci && npm run build

# 3. Empaquetar -> desktop/release/
npx electron-builder --config electron-builder.yml --linux deb AppImage   # Linux
npx electron-builder --config electron-builder.yml --win nsis             # Windows (en Windows)
```

Hace falta `backend/migrations/*.sql` con al menos una migración: el `.spec` aborta si no hay ninguna (hoy solo existe `.gitkeep`).
El `.spec` pone las migraciones en `_internal/migrations`: `MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"` vale `<_MEIPASS>/migrations` porque `__file__` es `<_MEIPASS>/app/database/migrator.pyc`.

El backend queda en `resources/backend/drakter-backend[.exe]` (+ `_internal/`) dentro de la app instalada.

## Qué se incluye y qué no

- Incluye: `out/**` y `package.json` en `app.asar`; el backend PyInstaller en `resources/backend` (filtrados `.env*`, `*.pem`, `*.key`, `*.map`, `__pycache__`).
- No incluye: `node_modules` (el renderer lo empaqueta Vite; si `main` importa un paquete externo, quitar `!node_modules/**` de `files`), mapas, fuentes `.ts/.tsx`, `.env*`.
- No incluye **Hermes**, **OpenViking** (AGPL: servicio aparte, no se redistribuye dentro del instalador) ni **modelos** (embeddings, voz, LLM local): se instalan o descargan aparte.
- Sin datos de usuario, sin base de datos, sin claves.

## Rutas de datos por SO (las resuelve `platformdirs`, nunca van dentro del paquete)

| | Linux | Windows |
|---|---|---|
| Datos (`drakter.db`, `backups/`, `logs/`) | `~/.local/share/drakter` (`XDG_DATA_HOME`) | `%LOCALAPPDATA%\drakter\drakter` |
| Config (`.env` del usuario) | `~/.config/drakter` (`XDG_CONFIG_HOME`) | `%LOCALAPPDATA%\drakter\drakter` |
| Runtime (`session.json`) | `$XDG_RUNTIME_DIR/drakter` | `%LOCALAPPDATA%\drakter\drakter\Temp` aprox. |

Los de Windows son los valores por defecto de `platformdirs` (NO COMPROBADO en Windows). Desinstalar nunca borra datos (`deleteAppDataOnUninstall: false`).

## Fuses

Aplicados por `electronFuses` (existe en el esquema de `app-builder-lib` 26.18.0, no hace falta `afterPack`): `runAsNode` off, `enableNodeOptionsEnvironmentVariable` off, `enableNodeCliInspectArguments` off, `enableCookieEncryption` on, `onlyLoadAppFromAsar` on, `enableEmbeddedAsarIntegrityValidation` on, `grantFileProtocolExtraPrivileges` off.

- `enableEmbeddedAsarIntegrityValidation` solo se aplica en macOS y Windows (Electron >= 30); en Linux es inocuo y no protege.
- `enableCookieEncryption` es de un solo sentido: no desactivarlo después.
- **Riesgo con `grantFileProtocolExtraPrivileges: false`**: hoy `desktop/electron/main/renderer-url.ts` carga el renderer por `file://` (`pathToFileURL`), **no** por `app://` (no hay protocolo `app://` registrado en `electron/`). Sin ese privilegio, las páginas `file://` se tratan como en un navegador y pueden fallar los `<script type="module" crossorigin>` que genera Vite. No se ha probado. Si la ventana sale en blanco, la solución correcta es que `main` sirva el renderer con un protocolo propio (`protocol.registerSchemesAsPrivileged` + `protocol.handle`) y mantener el fuse en off; no volver a ponerlo en on.

## Sandbox

Nunca `--no-sandbox` ni quitar `chrome-sandbox`.

- **.deb (camino soportado):** el `postinst` de electron-builder (`templates/linux/after-install.tpl`) pone `chrome-sandbox` a `4755` (SUID root) **solo si el kernel no soporta user namespaces**; si los soporta lo deja en `0755` y usa el sandbox por user namespaces. Además instala un perfil AppArmor (`/etc/apparmor.d/drakter`, desde `resources/apparmor-profile`) que permite el userns a la app en Ubuntu 24+. En esta máquina `kernel.apparmor_restrict_unprivileged_userns=1`, así que el perfil AppArmor es lo que hace funcionar el sandbox: comprobar que se instaló y que la app arranca sin `--no-sandbox`.
- **AppImage:** no puede tener SUID. Con `apparmor_restrict_unprivileged_userns=1` y sin perfil, Electron falla al arrancar con el sandbox. Es secundario y puede no funcionar en Ubuntu 24+; no se soporta.

## Backup antes de actualizar

Hoy la actualización es manual. Antes de instalar una versión nueva:

```bash
cd backend && python -m app.database.cli backup     # copia verificada en <datos>/backups
```

Con el backend ya en marcha, el bundle `pre-update` se crea desde la API de copias (ver `backend/CONTRACT.md`). Restaurar: `python -m app.database.cli restore <archivo>`. Las migraciones del backend nuevo se aplican al arrancar y hacen su propia copia previa.

## Actualización: manual por ahora

`publish: null`: no hay auto-actualización. Motivos: no hay servidor de actualizaciones ni versiones publicadas; el instalador no está firmado (en Windows `electron-updater` exige verificar la firma, y en Linux solo actualiza AppImage, no `.deb`); y una actualización automática puede migrar la base de datos sin que el usuario haya hecho copia. Se reevalúa tras firmar y definir dónde se publica.

## Qué falta para Windows

- Firma de código del instalador y del `.exe` (hoy sin certificado; SmartScreen avisará).
- Ejecutar el `.spec` y el lanzador **en Windows** (nunca probados; el lanzador solo asume `uv.exe` en el PATH).
- Icono `.ico` (ver abajo) y comprobar rutas de `platformdirs` y que el backend arranca como proceso hijo sin consola visible.

## Fuera de esta carpeta (lo debe añadir quien posea esos archivos)

- `desktop/package.json`: `"electron-builder": "26.18.0"` en devDependencies y scripts, p. ej. `"build:backend": "node electron-builder.build-backend.mjs"`, `"pack:linux": "electron-builder --config electron-builder.yml --linux deb AppImage"`, `"pack:win": "electron-builder --config electron-builder.yml --win nsis"`. `@electron/fuses` lo trae electron-builder, no hace falta añadirlo. Para `npx @electron/fuses read` basta usar `npx`.
- `electron/main`: cuando `app.isPackaged`, lanzar `path.join(process.resourcesPath, 'backend', 'drakter-backend[.exe]')` con `spawn` sin shell, y pararlo al salir. Hoy no existe ese arranque.
- Icono: `desktop/build/icon.png` (>= 512x512) y `icon.ico` para Windows; sin icono se usa el de Electron.
- `.gitignore`: `desktop/release/`, `backend/dist/`, `backend/build/`.

## Comprobaciones de la pasada integrada

Nada de esto está ejecutado aún.

1. `.deb`: `dpkg-deb -c desktop/release/*.deb | grep -E 'chrome-sandbox|resources/backend|apparmor'` (el backend y el perfil AppArmor deben estar; `.env`, mapas y fuentes no). `dpkg-deb -I` para metadatos.
2. Tras instalar: `ls -l /opt/Drakter/chrome-sandbox` (esperado `4755 root` sin userns, `0755` con userns + perfil) y `ls /etc/apparmor.d/drakter`.
3. Fuses: `npx @electron/fuses read --app /opt/Drakter/drakter` (esperado: RunAsNode, NodeOptions, NodeCliInspect, GrantFileProtocolExtraPrivileges `Disabled`; CookieEncryption, OnlyLoadAppFromAsar `Enabled`).
4. Arranque: `drakter` sin `--no-sandbox`; `ps -ef | grep -E 'drakter-backend|no-sandbox'` debe mostrar el backend y ningún `--no-sandbox`; la ventana debe mostrar la interfaz (no en blanco, ver riesgo de fuses) y `GET /` del backend responder en `127.0.0.1`.
5. Backend suelto: `/opt/Drakter/resources/backend/drakter-backend` crea `session.json` y aplica migraciones sobre una base temporal (`DRAKTER_DATA_DIR`, `DRAKTER_RUNTIME_DIR`).
6. `npx electron-builder` con el `.yml` real: valida que `${...}`/filtros de `extraResources` y `electronFuses` se aplican.
