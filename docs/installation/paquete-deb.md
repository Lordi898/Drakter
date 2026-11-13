# Paquete .deb de Drakter

> **Estado:** construido en esta máquina el 2026-11-13 desde `drakter/integracion` (`7fd30e1`) con los pasos de abajo: salen `drakter-desktop_0.1.0_amd64.deb` y `Drakter-0.1.0.AppImage`, y el backend empaquetado responde. NO COMPROBADO: instalar el `.deb` (requiere sudo) y abrir la ventana instalada. Detalle de las comprobaciones: `desktop/electron-builder.README.md`.

Sirve para instalar Drakter como aplicación de escritorio en Ubuntu en vez de lanzarla desde el repositorio. Para el modo desarrollo: [instalar.md](instalar.md).

## Requisitos

- Node con `npm`, `uv` en el PATH y `desktop/node_modules` instalado ([instalar.md](instalar.md)).
- Construir en el SO de destino: el backend no se cross-compila.
- Config: electron-builder 26.18.0, Electron 45, electron-vite 6.

## Pasos

1. Backend congelado con PyInstaller:
   `cd desktop && node electron-builder.build-backend.mjs`
   Sale en `backend/dist/linux/drakter-backend/`.
2. Desktop: `npm run build` (genera `desktop/out/`).
3. Empaquetar (electron-builder no está en `package.json`, se usa con `npx`):
   `npx --yes electron-builder@26.18.0 --config electron-builder.yml --linux deb AppImage -c.npmRebuild=false`
   Sale en `desktop/release/`. Si `/tmp` es un tmpfs con poco hueco, antepón `TMPDIR=/var/tmp`.
4. Instalar: `sudo apt install ./release/drakter-desktop_0.1.0_amd64.deb`. NO COMPROBADO.

En esta máquina tardó unos 2-4 minutos en total. El `.spec` aborta si faltan migraciones o si no encuentra los routers del backend.

## Qué incluye y qué no

- Incluye: `out/**` y `package.json` en `app.asar`, y el backend en `resources/backend` (sin `.env*`, `*.pem`, `*.key`, `*.map`, `__pycache__`).
- No incluye: `node_modules`, mapas, fuentes `.ts/.tsx`, `.env*`.
- No incluye Hermes, OpenViking (AGPL, servicio aparte) ni modelos (embeddings, voz, LLM local): se instalan aparte. Ver [hermes-y-openviking.md](hermes-y-openviking.md) y [voz.md](voz.md).
- Sin datos de usuario, base de datos ni claves. Los datos viven en `~/.local/share/drakter` y la config en `~/.config/drakter`; desinstalar no los borra.

## Sandbox

Nunca `--no-sandbox`. El `postinst` del `.deb` ajusta `chrome-sandbox` y, según el README, instala el perfil AppArmor `/etc/apparmor.d/drakter`, necesario en Ubuntu 24+. AppImage no está soportado. Detalle y comprobaciones: [sandbox-electron.md](sandbox-electron.md).

## Copia antes de actualizar

La actualización es manual. Antes de instalar una versión nueva:

```bash
cd backend && python -m app.database.cli backup
```

Crea una copia verificada en `<datos>/backups` (subcomandos de `backend/app/database/cli.py`: `status`, `migrate`, `backup`, `restore`). Esa CLI es de la instalación desde el repositorio; el backend empaquetado no la incluye. Con la app instalada, crea una copia en Configuración → Copias de seguridad antes de actualizar. El backend nuevo aplica las migraciones al arrancar y hace su propia copia previa.

## Actualizar

Manual: instala el `.deb` nuevo encima. `publish: null`, no hay auto-actualización (sin servidor, sin firma, y en Linux solo se actualizaría AppImage).

## Comprobar tras instalar (NO COMPROBADO: requiere sudo)

- `ls -l /opt/Drakter/chrome-sandbox` y `ls /etc/apparmor.d/drakter`.
- Lanzar `drakter` sin `--no-sandbox`; la ventana debe mostrar la interfaz.

## Pendiente

- `desktop/package.json` sin `electron-builder` ni scripts `build:backend`/`pack:linux`.
- Icono `desktop/build/icon.png` (sin él se usa el de Electron) y `.gitignore` de `desktop/release/`, `backend/dist/`, `backend/build/`.
- Riesgo declarado: con el fuse `grantFileProtocolExtraPrivileges: false` y el renderer por `file://`, la ventana puede salir en blanco. No probado.
- Sin firma de código. Windows (`nsis`) preparado y sin comprobar; el backend tiene código solo-POSIX.
