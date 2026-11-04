# Paquete .deb de Drakter

> **Estado:** sale de la rama `drakter/automejora` (`desktop/electron-builder.README.md`, `electron-builder.yml`), sin integrar en `drakter/build` (2da8bef): en 2da8bef no hay `electron-builder.yml` ni script de empaquetado. NO COMPROBADO: el README de la rama declara la configuración "escrita, no ejecutada". No se ha generado ningún `.deb`.

Sirve para instalar Drakter como aplicación de escritorio en Ubuntu en vez de lanzarla desde el repositorio. Para el modo desarrollo: [instalar.md](instalar.md).

## Requisitos

- Node con `npm`, y `uv` en el PATH (falta en esta máquina: ver [instalar.md](instalar.md), **Pendiente**).
- Construir en el SO de destino: el backend no se cross-compila.
- Config: electron-builder 26.18.0, Electron 45, electron-vite 6.

## Pasos (según el README de la rama; NO COMPROBADO)

1. Backend congelado con PyInstaller:
   `cd desktop && node electron-builder.build-backend.mjs`
   Sale en `backend/dist/linux/drakter-backend/`.
2. Desktop: `npm ci && npm run build` (genera `desktop/out/`).
3. Empaquetar:
   `npx electron-builder --config electron-builder.yml --linux deb AppImage`
   Sale en `desktop/release/`.
4. Instalar el `.deb` generado con `dpkg` (el nombre del archivo no consta: **Pendiente**).

El `.spec` aborta si `backend/migrations/` no tiene ningún `.sql`. Eso solo ocurre en `drakter/automejora` (solo `.gitkeep`); en 2da8bef hay 10 (`0001_core_entities.sql` a `0010_memory_improvement.sql`), así que ese aborto ya no aplicaría. Sigue sin comprobar y el `.spec` no está en `build`.

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

Crea una copia verificada en `<datos>/backups` (subcomandos reales en `backend/app/database/cli.py` de 2da8bef: `status`, `migrate`, `backup`, `restore`). Para restaurar: `python -m app.database.cli restore <archivo>`. Con el backend en marcha, el bundle `pre-update` se crea desde la API de copias (ver `backend/CONTRACT.md`). El backend nuevo aplica las migraciones al arrancar y hace su propia copia previa.

## Actualizar

Manual: instala el `.deb` nuevo encima. `publish: null`, no hay auto-actualización (sin servidor, sin firma, y en Linux solo se actualizaría AppImage).

## Comprobar tras instalar (del README; NO COMPROBADO)

- `ls -l /opt/Drakter/chrome-sandbox` y `ls /etc/apparmor.d/drakter`.
- Lanzar `drakter` sin `--no-sandbox`; la ventana debe mostrar la interfaz.

## Pendiente

- **Scripts:** `desktop/package.json` (también en 2da8bef) no tiene `electron-builder` ni scripts `build:backend`/`pack:linux`; el README los propone y no existen.
- **Arranque del backend empaquetado:** en 2da8bef, `desktop/electron/main/backendProcess.ts` con `app.isPackaged` lanza `<datos>/runtime/backend/.venv/bin/python -m app` (ruta marcada "provisional" en el código), no `resources/backend/drakter-backend`. Sin cambiarlo, la app instalada no encontraría el backend empaquetado.
- Icono `desktop/build/icon.png` (sin él se usa el de Electron) y `.gitignore` de `desktop/release/`, `backend/dist/`, `backend/build/`.
- Riesgo declarado: con el fuse `grantFileProtocolExtraPrivileges: false` y el renderer por `file://`, la ventana puede salir en blanco. No probado.
- Sin firma de código. Windows (`nsis`) preparado y sin comprobar.
