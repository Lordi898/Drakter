# Instalación de Drakter

Guías para instalar Drakter desde el repositorio o como app empaquetada. Revisadas contra `main` el 2026-11-27. Lo que no se ha podido probar lleva `NO COMPROBADO` y lo que falta, `Pendiente`.

## Orden de lectura

1. [Instalar](instalar.md): **guía completa** paso a paso. Requisitos, uv, Python 3.12 y Node 24, venv del backend (`python3.12 -m venv` + `pip install -r requirements.txt`, o `uv sync`), escritorio, Hermes, voz, `.env`, comprobación, arranque, actualización y desinstalación.
2. [Configuración (`.env`)](configuracion-env.md): todas las variables de `~/.config/drakter/.env`, con su valor por defecto, más la plantilla [`.env.example`](../../.env.example).
3. [Clave de API](clave-api.md): la clave de Anthropic, con permisos 600 y sin espacios tras el igual.
4. [Sandbox de Electron](sandbox-electron.md): paso opcional con sudo, necesario en Ubuntu reciente para ejecutar con sandbox.
5. [Hermes y OpenViking](hermes-y-openviking.md): el agente, en su propio venv con Python 3.14 (`scripts/install-hermes.sh`).
6. [Voz](voz.md): entorno, modelos, atajo Super+J y prueba de micrófono.
7. [Paquete .deb](paquete-deb.md): instalador del sistema; construido, sin instalar todavía.

App empaquetada (AppImage, sin sudo): [primeros pasos](../usage/primeros-pasos.md). Uso diario: [usage](../usage/README.md).

## Archivos de dependencias

| Archivo | Para qué |
|---|---|
| `backend/pyproject.toml` + `backend/uv.lock` | Fuente de verdad de las dependencias del backend (Python 3.12) |
| `backend/requirements.txt` | Las mismas versiones, para `pip`. Se **genera** con `scripts/export-requirements.sh`; el CI comprueba que coincide con `uv.lock` |
| `desktop/package.json` + `desktop/package-lock.json` | Escritorio (`npm ci`) |
| `voice/pyproject.toml` + `voice/requirements.lock` | Proceso de voz (lo instala `scripts/install-voice.sh`) |
| `contracts/python/pyproject.toml` | Contratos compartidos (`drakter-contracts`), instalados en editable por los anteriores |
| `agent/evals/requirements.txt` | Solo para las evaluaciones del agente |
| Hermes | Fuera del repositorio: commit fijado en `scripts/install-hermes.sh` |
