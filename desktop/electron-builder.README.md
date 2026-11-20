# Empaquetado de Drakter Desktop

Configuración de electron-builder 26.18.0 (Electron 45, electron-vite 6). Linux primero; Windows preparado pero sin comprobar.
Estado: **regenerada el 2026-11-20** sobre `main` (`f82dda9` + rama de lanzamiento): AppImage y `.deb` construidos; el AppImage instalado con `scripts/install-appimage.sh` arranca con sandbox y conecta con su backend (ver "Comprobaciones del lanzamiento"). Falta instalar el `.deb` (requiere sudo). Windows sin probar.

Archivos: `electron-builder.yml` (config), `electron-builder.backend.spec` (PyInstaller), `electron-builder.build-backend.mjs` (lanzador del backend), `electron-builder.rthook-module.py` (runtime hook: `drakter-backend -m <módulo>`). Atajo de los tres pasos: `scripts/package.sh [appimage|deb|all]`.

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

El `.spec` aborta si `backend/migrations/` no tiene ningún `.sql`, o si `collect_submodules("app")` no encuentra `app.api.health`: ese hook corre en un subproceso que no ve `pathex`, y sin `backend/` en `sys.path` devolvía una lista vacía y el backend congelado respondía 404 en todas las rutas (corregido).
El `.spec` pone las migraciones en `_internal/migrations`: `MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"` vale `<_MEIPASS>/migrations` porque `__file__` es `<_MEIPASS>/app/database/migrator.pyc`.

El backend queda en `resources/backend/drakter-backend[.exe]` (+ `_internal/`) dentro de la app instalada.

## Qué se incluye y qué no

- Incluye: `out/**` y `package.json` en `app.asar`; el backend PyInstaller en `resources/backend` (filtrados `.env*`, `*.pem`, `*.key`, `*.map`, `__pycache__`).
- No incluye: `node_modules` (el renderer lo empaqueta Vite; si `main` importa un paquete externo, quitar `!node_modules/**` de `files`), mapas, fuentes `.ts/.tsx`, `.env*`.
- Incluye también, en `resources/backend/`: `agent/` (sin `evals/`), `voice/` (sin `tests/`) y `tools/catalog.json`; dentro del bundle, el runner de Hermes como archivo y `pyproject.toml`. Motivo: el backend congelado resuelve su `REPO_ROOT` como el padre de `_internal`, es decir `resources/backend/`, y ahí busca la identidad, los permisos del agente, el runner y el código de voz (que ejecuta el venv de voz con `-m voice`).
- No incluye **Hermes**, **OpenViking** (AGPL: servicio aparte, no se redistribuye dentro del instalador), los **venvs** (voz, Hermes) ni **modelos**: los comprueba e instala `scripts/install-appimage.sh [--runtimes]` con `install-hermes.sh` e `install-voice.sh`.
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

La actualización es manual. Antes de instalar una versión nueva:

```bash
cd backend && python -m app.database.cli backup     # copia verificada en <datos>/backups
```

En una instalación empaquetada, la misma CLI va dentro del backend congelado gracias al runtime hook: `resources/backend/drakter-backend -m app.database.cli backup|restore|status|migrate`. `scripts/update.sh` hace la copia antes de migrar. Las migraciones del backend nuevo se aplican además al arrancar, con su propia copia `pre-migrate`.

## Actualización: `scripts/update.sh`

`publish: null`: no hay auto-actualización dentro de la app. La actualización es `scripts/update.sh [--package]` (git pull --ff-only, dependencias que cambien, copia, migraciones, reinicio; con `--package` reconstruye y reinstala el AppImage). `electron-updater` se descarta: con un repositorio privado, el proveedor `github` necesita un token con acceso al repo guardado en la app (`GH_TOKEN`/`private: true`), solo actualiza el AppImage (no el `.deb`, ni el backend fuera del paquete, ni los venvs de voz y Hermes, ni los modelos) y puede migrar la base sin copia previa. Ver `docs/DECISIONS.md`.

## Qué falta para Windows

- Firma de código del instalador y del `.exe` (hoy sin certificado; SmartScreen avisará).
- **Bloqueante:** el backend no arranca en Windows: `backend/app/database/connection.py` usa `os.geteuid`, y las copias usan `os.O_NOFOLLOW`; ninguno existe allí.
- Ejecutar el `.spec` y el lanzador **en Windows** (nunca probados; el lanzador solo asume `uv.exe` en el PATH).
- Icono `.ico` (ver abajo) y comprobar rutas de `platformdirs` y que el backend arranca como proceso hijo sin consola visible.

## Fuera de esta carpeta (lo debe añadir quien posea esos archivos)

- `desktop/package.json`: no tiene `electron-builder` ni scripts. Hoy se usa `npx --yes electron-builder@26.18.0 ... -c.npmRebuild=false` (sin `npmRebuild=false` intentaría recompilar `node_modules`). Sin `homepage` en `package.json`, el `.deb` falla: el `.yml` la añade con `extraMetadata`.
- Hecho: `electron/main/backendProcess.ts` lanza `resources/backend/drakter-backend[.exe]` cuando `app.isPackaged`.
- Hecho: `desktopName: drakter.desktop` va por `extraMetadata` (WM_CLASS) y `scripts/package.sh` llama a `electron-builder@26.18.0` con `npx`, sin tocar el lock.
- Icono: `desktop/build/icon.png` (>= 512x512) y `icon.ico` para Windows; sin icono se usa el de Electron.
- Construir con `TMPDIR` en disco si `/tmp` es un tmpfs justo: fpm copia ~330 MB y comprime con xz allí.

## Comprobaciones de la pasada integrada (2026-11-13, Linux, sin sudo)

Tiempos y memoria de esta máquina con otras pasadas en paralelo (orientativos):

| Paso | Tiempo | RSS máx. |
|---|---|---|
| `node electron-builder.build-backend.mjs` (PyInstaller 6.22.3) | 22-70 s | 116 MB |
| `npm run build` (typecheck + electron-vite) | 5 s | 400 MB |
| `electron-builder --linux deb AppImage` | 38-155 s | 500 MB |

Resultados: backend onedir 45 MB; AppImage ~150 MB; `.deb` 119 MB (instalado 320 MB).

1. `.deb`: `dpkg-deb -c` contiene `opt/Drakter/chrome-sandbox`, `resources/backend/drakter-backend`, `resources/apparmor-profile` y `app.asar`; 0 archivos `.env`, `.pem`, `.key`, `.map`, `.ts/.tsx`. `dpkg-deb -I`: `drakter-desktop 0.1.0 amd64`, `Homepage` y dependencias GTK/NSS. El `postinst` pone `chrome-sandbox` a 4755 sin userns e instala `/etc/apparmor.d/drakter`. **OK.**
2. Tras instalar (`ls -l /opt/Drakter/chrome-sandbox`, `/etc/apparmor.d/drakter`): **no comprobado**, requiere sudo.
3. Fuses (`npx @electron/fuses read --app release/linux-unpacked/drakter`): RunAsNode, NodeOptions, NodeCliInspect y GrantFileProtocolExtraPrivileges `Disabled`; CookieEncryption, OnlyLoadAppFromAsar y EmbeddedAsarIntegrityValidation `Enabled`. **OK.**
4. Arranque de la ventana empaquetada sin `--no-sandbox`: **no comprobado** (necesita el `.deb` instalado para el perfil AppArmor). Sigue abierto el riesgo de ventana en blanco por `file://`.
5. Backend suelto (`backend/dist/linux/drakter-backend/drakter-backend` con handshake por stdin y `DRAKTER_DATA_DIR` temporal): anuncia el puerto en 0,7-6 s, `/health` 200, `/api/v1/tasks` 401 sin token y 200 con él, `/api/v1/today` 200, aplica las 11 migraciones, RSS ~105 MB y sale con 0 al cerrar stdin. **OK** tras corregir el `.spec`.
6. `electron-builder` con el `.yml` real: `extraResources`, filtros y `electronFuses` se aplican. **OK.**

## Comprobaciones del lanzamiento (2026-11-20, Linux, sin sudo)

`scripts/package.sh` en esta máquina: backend 33 s (RSS 139 MB), `npm ci` + build 10 s, electron-builder 88 s (RSS 540 MB). AppImage 155 MB, `.deb` 127 MB.

1. Backend congelado: `drakter-backend -m app.database.cli status|migrate|backup|restore` sobre una carpeta de datos vacía: aplica las 14 migraciones, la copia lleva `.sha256`, restaurar devuelve el valor anterior y guarda `pre-restore`, y una copia alterada se rechaza («no coincide con su hash»). **OK.**
2. `scripts/install-appimage.sh` en carpetas limpias (`DRAKTER_INSTALL_DIR`, `DRAKTER_BIN_DIR`, `XDG_DATA_HOME` aparte): extrae, crea lanzador y `.desktop`, y detecta Hermes, venv de voz, modelos, `.env` y el sandbox. **OK.**
3. App instalada con config, datos y `XDG_RUNTIME_DIR` limpios, sin `--no-sandbox`: arranca, el backend congelado aplica las migraciones, el renderer abre el WebSocket (`connection open`) y el proceso de voz arranca desde `resources/backend/voice` (`service_ready`; sin modelos en esa carpeta de datos limpia, `pipeline_build_failed` esperado). Renderer con `Seccomp: 2`, `NoNewPrivs: 1` y user namespace propio. **OK**, con una reserva: la sesión de prueba heredaba el perfil AppArmor `snap.code.code (complain)` del terminal, que permite user namespaces. Desde el menú de GNOME hace falta el perfil que imprime el instalador (sudo): **no comprobado**.
4. El AppImage sin extraer no arranca: Ubuntu 24 no trae `libfuse2` (`dlopen(): error loading libfuse.so.2`). Por eso el instalador extrae; `APPIMAGE_EXTRACT_AND_RUN=1` sirve para una prueba suelta.
5. `.deb`: construido; instalarlo requiere sudo, **no comprobado**.
