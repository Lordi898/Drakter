# Clave de API de Anthropic

> **Estado:** contrastada con `drakter/integracion` (`7fd30e1`). La clave la lee `backend/app/integrations/hermes/settings.py` y Ajustes muestra su estado (`desktop/src/settings/AgentStatusSection.tsx`). NO COMPROBADO con una clave real: en las pruebas de cierre no había clave y el chat se probó con el LLM de pruebas.

Drakter necesita una clave de API de Anthropic para hablar con el modelo. Se guarda solo en tu máquina, en `~/.config/drakter/.env`, fuera del repositorio.

## Dónde y con qué formato

- Archivo: `~/.config/drakter/.env` (el código lo resuelve con `platformdirs.user_config_dir("drakter")`; si usas `XDG_CONFIG_HOME`, es esa carpeta).
- Línea exacta, sin espacios y sin comillas:

```
ANTHROPIC_API_KEY=<tu-clave>
```

- El nombre es `ANTHROPIC_API_KEY` a secas, sin prefijo `DRAKTER_` (alias declarado en `backend/app/integrations/hermes/settings.py`).

## Pasos

1. Crea la carpeta privada y el archivo con permisos 600. Si el archivo ya existe, estos comandos conservan su contenido (comprobado sobre una copia de prueba). No contienen la clave, así que no queda nada en el historial:

   ```
   install -d -m 700 ~/.config/drakter
   touch ~/.config/drakter/.env
   chmod 600 ~/.config/drakter/.env
   ```

2. Abre el archivo con un editor y escribe la línea del formato anterior. Pega la clave en el editor, nunca en la terminal:

   ```
   nano ~/.config/drakter/.env
   ```

3. Comprueba los permisos sin mostrar el contenido:

   ```
   stat -c %a ~/.config/drakter/.env
   ```

   Debe imprimir `600`. Para la carpeta, `stat -c %a ~/.config/drakter` debe dar `700`. `scripts/check-env.sh` también lo revisa, sin abrir el archivo.

4. Reinicia Drakter. La configuración se carga al arrancar el backend; un cambio en el `.env` no se aplica a una instancia ya abierta.

Evita `echo "ANTHROPIC_API_KEY=..." >> .env`, `export` con la clave y cualquier forma de escribirla en la línea de comandos: quedaría en el historial de la shell.

No necesitas copiar `.env.example`. Si lo haces, usa `cp -n` para no pisar tu `.env` y borra después toda línea sin valor: en las variables del agente una línea vacía no equivale a no definirla. Ojo: `.env.example` aún lista variables que ya no se leen (ver abajo).

## Qué dice la app

En Configuración (`desktop/src/settings/AgentStatusSection.tsx`) aparece una de estas tres filas:

- **Clave de API: Configurada.** El agente ya cargó la clave.
- **Falta la clave de API.** Texto: "Añade ANTHROPIC_API_KEY a ~/.config/drakter/.env y reinicia Drakter."
- **Clave de API: no comprobada.** "Drakter no lee ese archivo; lo sabrá cuando el agente arranque."

La app nunca lee el valor ni abre el `.env`: de ese archivo solo mira si existe (`backend/app/services/settings_models.py` y `settings_status.py`). Si el `.env` existe pero el agente aún no ha cargado la configuración, verás "no comprobada", no "Configurada".

## Espacios y comillas: qué hace el parser

Los dos ajustes (`app/core/config.py` y `app/integrations/hermes/settings.py`) usan `pydantic-settings` con `env_file`, que lee el archivo con `python-dotenv` (versión bloqueada en `backend/uv.lock`: 1.2.4). Se probó el parser con valores falsos:

- Espacio tras el igual (`A= valor`, `B = valor`): **el parser lo tolera** y lo descarta. No falla.
- Comillas dobles (`C="valor"`): **también las tolera** y las quita.
- Espacio final (`D=valor `) o comentario ` # ...` tras un valor sin comillas: se descartan.
- Un espacio dentro del valor (`E=va lor`) se conserva.

Aun así, la regla es no poner espacios ni comillas. Motivos: no depender de una versión concreta del parser, y que la misma línea funcione si algún día la lee otra herramienta (shell, systemd, Docker), que sí las tratan distinto. Una clave de Anthropic no lleva espacios, así que un espacio dentro del valor siempre es un error de copiado.

## Variables opcionales

Mismo archivo, prefijo `DRAKTER_`. No pongas valores reales en el repositorio:

- Backend (`backend/app/core/config.py`): `DRAKTER_DATA_DIR` (ruta absoluta) y `DRAKTER_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Ignora las líneas vacías.
- Agente (`backend/app/integrations/hermes/settings.py`): `DRAKTER_ENV` (`development` o `production`), `DRAKTER_AGENT_PROVIDER` (`hermes` o `fake`), `DRAKTER_MODEL_PROVIDER` (`anthropic` o `dev_stub`), `DRAKTER_MODEL_NAME` (por defecto `claude-haiku-5-5`), `DRAKTER_DEV_STUB_URL`, `DRAKTER_HERMES_PYTHON` (Python del venv de Hermes; por defecto `hermes-python` en el PATH), `DRAKTER_AGENT_MAX_TURNS`, `DRAKTER_TURN_TIMEOUT_S`, `DRAKTER_IDLE_TIMEOUT_S`. Aquí una línea vacía sí cuenta como valor: pon solo las que quieras cambiar.
- Voz: las variables `DRAKTER_STT_*`, `DRAKTER_TTS_*`, etc. de [voz.md](voz.md).

`DRAKTER_PORT`, `DRAKTER_RUNTIME_DIR` y `DRAKTER_ALLOWED_ORIGINS` ya no existen: el puerto es efímero y lo gestiona Electron. Los valores por defecto sirven para el uso normal. `dev_stub` es solo para desarrollo y el código lo rechaza con `DRAKTER_ENV=production`.

## Problemas frecuentes

- Ajustes sigue diciendo "Falta la clave": el archivo no existe en esa ruta exacta, o no reiniciaste Drakter.
- Sigue en "no comprobada" tras reiniciar: el agente no ha arrancado todavía o no pudo cargar la clave. Revisa el nombre (`ANTHROPIC_API_KEY`, sin prefijo).
- Variables con otro nombre se ignoran sin error (`extra="ignore"`).

## Pendiente

- Los permisos 600 solo los avisa `scripts/check-env.sh`; el backend no se niega a arrancar si faltan.
- No hay comando ni pantalla para guardar la clave desde la app; solo editar el archivo.
- Más pasos de instalación: [instalar.md](instalar.md).
