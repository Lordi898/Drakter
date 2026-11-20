# Primeros pasos

Drakter tiene dos formas de instalarse. Las dos necesitan el repositorio clonado, porque la voz y Hermes se instalan desde él y no van dentro del paquete.

| | AppImage (recomendada) | Desde el repositorio |
|---|---|---|
| Para qué | Uso diario | Desarrollo |
| Sudo | No (solo una vez, para el sandbox en Ubuntu 24+) | No |
| Se abre con | Menú de aplicaciones o `drakter-app` | `scripts/drakter-local.sh start anthropic` |
| Se actualiza con | `scripts/update.sh --package` | `scripts/update.sh` |

El `.deb` también se construye (`scripts/package.sh deb`) e instala el sandbox por su cuenta, pero necesita sudo (ver [paquete .deb](../installation/paquete-deb.md)).

## 1. Clonar y preparar el entorno

```bash
git clone https://github.com/Lordi898/Drakter.git ~/Drakter
cd ~/Drakter
(cd backend && uv sync --locked)
(cd desktop && npm ci)
scripts/install-hermes.sh        # agente: Hermes v0.22.7 en ~/.local/share/drakter/venvs/hermes
scripts/install-voice.sh         # voz: venv y comprobación de modelos (opcional)
scripts/check-env.sh             # OK / AVISO / FALTA
```

El repositorio es privado: `git clone` y `git pull` usan tus credenciales de git (SSH o `gh auth login`). Los modelos de voz deben estar en `~/.local/share/drakter/models/`: el código no descarga nada. Detalle: [instalar la voz](../installation/voz.md).

## 2. Claves

```bash
mkdir -p ~/.config/drakter
cp -n .env.example ~/.config/drakter/.env
chmod 600 ~/.config/drakter/.env
```

Rellena al menos `ANTHROPIC_API_KEY`. Para la voz en la nube, `DEEPGRAM_API_KEY` (reconocimiento) y `FISH_API_KEY` (voz de Drakter); sin ellas se usa lo local. Más: [clave de API](../installation/clave-api.md).

## 3. Instalar la app (AppImage)

```bash
scripts/package.sh appimage          # genera desktop/release/Drakter-<versión>.AppImage (~2-3 min)
scripts/install-appimage.sh          # o: scripts/install-appimage.sh --runtimes
```

`install-appimage.sh` extrae el AppImage en `~/.local/opt/drakter/app`, crea el lanzador `~/.local/bin/drakter-app` y la entrada «Drakter» del menú, y revisa los runtimes: Hermes, el venv de voz, los modelos, el `.env` y el sandbox. Con `--runtimes` instala lo que falte. Nunca imprime tus claves.

En Ubuntu 24 o posterior, el script te da **un comando con sudo** para instalar el perfil AppArmor del sandbox de Electron. Ejecútalo una vez: sin él, la app no arranca desde el menú. Se extrae en lugar de ejecutar el AppImage directamente porque Ubuntu 24 no trae `libfuse2` y porque el perfil necesita una ruta fija.

## 4. Primer arranque

1. Abre **Drakter** desde el menú (o `drakter-app`).
2. La primera vez el backend crea la base de datos en `~/.local/share/drakter/drakter.db` y aplica las migraciones.
3. Haz la **copia de seguridad inicial**: [Copias y actualización](copias-y-actualizacion.md#copia-inicial).
4. Atajo de voz Super+J, una vez: `scripts/install-shortcut.sh install`.
5. Ajustes → Voz: elige micrófono y salida y pulsa **Probar** ([Voz](voz.md#auriculares-o-altavoces)).

Si algo no va: [Solución de problemas](problemas.md).
