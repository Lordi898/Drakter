# Solución de problemas

Primero, siempre: `scripts/check-env.sh` y, con la app instalada, `scripts/install-appimage.sh` (repite la comprobación de runtimes sin perder nada). Logs: `~/.local/share/drakter/logs/` (`backend.log`, `hermes.log`).

## La app no arranca

| Síntoma | Causa y arreglo |
|---|---|
| Error de `chrome-sandbox` o «The SUID sandbox helper binary…» | Ubuntu 24+ restringe los user namespaces. Ejecuta una vez el comando con sudo que imprime `scripts/install-appimage.sh` (perfil AppArmor). Nunca uses `--no-sandbox`: la app empaquetada lo rechaza. Detalle: [sandbox de Electron](../installation/sandbox-electron.md). |
| Al lanzarla desde un terminal de VS Code u otra app Electron no sale ninguna ventana | El terminal heredó `ELECTRON_RUN_AS_NODE=1`. Abre Drakter con `drakter-app`, `scripts/drakter` o `scripts/drakter-local.sh`, que la quitan; o `unset ELECTRON_RUN_AS_NODE`. |
| «AppImages require FUSE to run» | Normal en Ubuntu 24 (sin `libfuse2`). No abras el AppImage directamente: instálalo con `scripts/install-appimage.sh`. Para una prueba suelta: `APPIMAGE_EXTRACT_AND_RUN=1 ./Drakter-*.AppImage`. |
| «Falta el servicio local de Drakter» | El paquete está incompleto: reconstruye con `scripts/package.sh appimage` y reinstala. |
| La ventana se abre pero «Drakter no está conectado ahora» | El backend no arrancó: mira `backend.log`. Con `invalid configuration: <campo>`, revisa ese campo en `~/.config/drakter/.env`. |

## El agente no responde

- «ANTHROPIC_API_KEY is not configured» en `backend.log`: rellena la clave en `~/.config/drakter/.env` (permisos 600) y reinicia.
- `hermes-python` no encontrado: `scripts/install-hermes.sh`. Si abres la app desde el menú, `~/.local/bin` debe estar en tu `PATH` (lo está en Ubuntu tras volver a iniciar sesión), o pon `DRAKTER_HERMES_PYTHON=/home/<tú>/.local/bin/hermes-python` en el `.env`.
- **Sin red:** el agente (Claude) necesita conexión. Las pantallas de datos (tareas, calendario, almacén…) siguen funcionando.

## La voz no funciona

| Síntoma | Causa y arreglo |
|---|---|
| Punto del micrófono en `off` | El micrófono está silenciado en Drakter: bandeja → «Activar micrófono». |
| Punto en `standby` pero no reacciona a «Hey Jarvis» ni a Super+J | El micrófono está silenciado **en el sistema** (tecla de silencio o Ajustes de GNOME → Sonido) o Drakter usa otra entrada: Ajustes → Voz → Micrófono. Comprueba el nivel con `wpctl status`. |
| No se oye a Drakter | Icono de altavoz del chat tachado (lo silencia solo en Drakter), o la salida elegida no es la que tienes puesta: Ajustes → Voz → Salida de audio → **Probar**. |
| Se interrumpe sola mientras habla | Eco de los altavoces: usa auriculares o baja el volumen ([Voz](voz.md#auriculares-o-altavoces)). |
| «dependency_missing» o error de voz al abrir | Falta el venv de voz o un modelo: `scripts/install-voice.sh` y `~/.local/share/drakter/venvs/voice/bin/python -m voice check`. |
| Sin red, la voz no conecta | Arranca con `drakter-app`, `scripts/drakter` o `drakter-local.sh`: pasan `--allow-loopback-in-peer-connection`, sin el que WebRTC no usa 127.0.0.1. |
| Sin red, Drakter habla con otra voz | Normal: Fish necesita red y pasa a Kokoro (local) con un único aviso. El reconocimiento pasa de Deepgram a Moonshine local. |
| Super+J no hace nada | Prueba `scripts/drakter activate`; si funciona, repite `scripts/install-shortcut.sh install`. |

## Datos

- «La base está en uso por otra instancia de Drakter» al restaurar o migrar: cierra Drakter y repite.
- Algo se borró por error: restaura la última copia ([Copias y actualización](copias-y-actualizacion.md#restaurar)).
- `scripts/update.sh` dice «hay cambios sin guardar»: `git status`; guarda tus cambios con `git stash push -m antes-de-update` o haz commit, y repite.
