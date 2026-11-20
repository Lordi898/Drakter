#!/usr/bin/env bash
# Instala el AppImage de Drakter para el usuario actual, sin sudo, y comprueba los runtimes.
#
#   scripts/install-appimage.sh [--runtimes] [ruta/Drakter-X.Y.Z.AppImage]
#
#   --runtimes   instala lo que falte con scripts/install-hermes.sh y scripts/install-voice.sh
#                (sin la opción solo dice qué falta y cómo arreglarlo).
#
# Qué hace:
#   1. Extrae el AppImage en ~/.local/opt/drakter/app (ruta estable: la necesita el perfil
#      AppArmor del sandbox y arranca más rápido que montar el AppImage cada vez).
#   2. Crea el lanzador ~/.local/bin/drakter-app y la entrada de menú drakter.desktop.
#   3. Comprueba los runtimes que NO van en el paquete: venv de voz y sus modelos, Hermes
#      (hermes-python), ~/.config/drakter/.env y el sandbox de Electron.
# Nunca abre ni imprime el .env: solo mira si existe, sus permisos y qué claves tienen valor.
set -euo pipefail
unset ELECTRON_RUN_AS_NODE ELECTRON_NO_ATTACH_CONSOLE

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
opt="${DRAKTER_INSTALL_DIR:-$HOME/.local/opt/drakter}"
bin_dir="${DRAKTER_BIN_DIR:-$HOME/.local/bin}"
apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
runtime="${DRAKTER_RUNTIME_DIR:-$HOME/.local/share/drakter}"
env_file="${XDG_CONFIG_HOME:-$HOME/.config}/drakter/.env"

runtimes=0
image=""
for arg in "$@"; do
  case "$arg" in
    --runtimes) runtimes=1 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) image="$arg" ;;
  esac
done
if [ -z "$image" ]; then
  image="$(ls -t "$repo"/desktop/release/Drakter-*.AppImage 2>/dev/null | head -n1 || true)"
fi
[ -n "$image" ] && [ -f "$image" ] || {
  echo "ERROR: no encuentro el AppImage. Constrúyelo con scripts/package.sh o pasa su ruta." >&2
  exit 1
}
image="$(readlink -f "$image")"

ok() { echo "OK    $*"; }
warn() { echo "AVISO $*"; problems=$((problems + 1)); }
problems=0

case "$(realpath -m "$opt")" in
  /tmp|/tmp/*|/var/tmp|/var/tmp/*) echo "ERROR: $opt es temporal; elige una ruta estable." >&2; exit 1 ;;
esac

# ── 1. Extraer en una carpeta nueva y sustituir la anterior de golpe ──────────
mkdir -p "$opt" "$bin_dir" "$apps_dir"
work="$(mktemp -d "$opt/.extract.XXXXXX")"
trap 'rm -rf "$work"' EXIT
chmod +x "$image"
(cd "$work" && "$image" --appimage-extract >/dev/null)
[ -x "$work/squashfs-root/drakter" ] || { echo "ERROR: el AppImage no contiene 'drakter'." >&2; exit 1; }
[ -x "$work/squashfs-root/resources/backend/drakter-backend" ] \
  || { echo "ERROR: el AppImage no lleva el backend (resources/backend)." >&2; exit 1; }
rm -rf "$opt/app.old"
[ -d "$opt/app" ] && mv "$opt/app" "$opt/app.old"
mv "$work/squashfs-root" "$opt/app"
rm -rf "$opt/app.old"
version="$(sed -n 's/^X-AppImage-Version=//p' "$opt/app/drakter.desktop" 2>/dev/null | head -n1)"
ok "Drakter ${version:-?} extraído en $opt/app"

# ── 2. Lanzador y entrada de menú ─────────────────────────────────────────────
cat >"$bin_dir/drakter-app" <<EOF
#!/bin/sh
# Generado por scripts/install-appimage.sh. Un padre Electron (VS Code, Orchestrator...) deja
# ELECTRON_RUN_AS_NODE=1 y la app arrancaría como Node. El switch de loopback lo necesita la
# voz (WebRTC con 127.0.0.1) y debe ir en argv.
unset ELECTRON_RUN_AS_NODE ELECTRON_NO_ATTACH_CONSOLE
PATH="$bin_dir:\$PATH"; export PATH
exec "$opt/app/drakter" --allow-loopback-in-peer-connection "\$@"
EOF
chmod +x "$bin_dir/drakter-app"
icon="$opt/app/drakter.png"
[ -f "$icon" ] || icon="$(find "$opt/app/usr/share/icons" -name 'drakter.png' 2>/dev/null | sort | tail -n1)"
cat >"$apps_dir/drakter.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Drakter
Comment=Agente personal de IA
Exec=$bin_dir/drakter-app %U
Icon=${icon:-drakter}
Terminal=false
Categories=Office;
StartupWMClass=Drakter
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$apps_dir" >/dev/null 2>&1 || true
ok "lanzador $bin_dir/drakter-app y menú $apps_dir/drakter.desktop"

# ── 3. Runtimes que no van en el paquete ──────────────────────────────────────
echo "── Comprobando runtimes"
if [ "$runtimes" = 1 ]; then
  command -v hermes-python >/dev/null || PATH="$bin_dir:$PATH" "$repo/scripts/install-hermes.sh"
  [ -x "$runtime/venvs/voice/bin/python" ] || "$repo/scripts/install-voice.sh" \
    || echo "AVISO install-voice.sh terminó con error (ver arriba): faltan modelos o dependencias."
fi

if PATH="$bin_dir:$PATH" command -v hermes-python >/dev/null \
  && PATH="$bin_dir:$PATH" hermes-python -c 'import run_agent' 2>/dev/null; then
  ok "Hermes: hermes-python funciona"
else
  warn "Hermes no está instalado o no funciona: sin él no hay agente. Arreglo: scripts/install-hermes.sh"
fi

voice_py="$runtime/venvs/voice/bin/python"
if [ -x "$voice_py" ] && "$voice_py" -c 'import pipecat, drakter_contracts.voice_ipc' 2>/dev/null; then
  ok "voz: venv $runtime/venvs/voice"
else
  warn "voz: falta el venv de voz o está roto; la app funciona sin voz. Arreglo: scripts/install-voice.sh"
fi
models="$runtime/models"
for m in kokoro/kokoro-v1.0.int8.onnx openwakeword/hey_jarvis_v0.1.onnx smart-turn/smart-turn-v3.2-cpu.onnx; do
  [ -s "$models/$m" ] || warn "voz: falta el modelo $models/$m (ver docs/usage/voz.md)"
done

if [ ! -e "$env_file" ]; then
  warn "no existe $env_file: crea el archivo desde .env.example con ANTHROPIC_API_KEY (chmod 600)"
else
  [ "$(stat -L -c %a "$env_file")" = 600 ] || warn "$env_file debería tener permisos 600 (chmod 600 \"$env_file\")"
  # Solo se mira si la clave tiene valor; el valor nunca se lee a una variable ni se imprime.
  if grep -qE '^ANTHROPIC_API_KEY=.+' "$env_file"; then ok "ANTHROPIC_API_KEY configurada"
  else warn "ANTHROPIC_API_KEY vacía en $env_file: sin ella el agente no responde"; fi
  for key in DEEPGRAM_API_KEY FISH_API_KEY; do
    grep -qE "^$key=.+" "$env_file" || echo "INFO  $key vacía: esa voz en la nube no estará disponible"
  done
fi

# Sandbox de Electron. Nunca --no-sandbox: con userns restringido hace falta un perfil AppArmor.
if [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)" = 1 ] \
  && ! grep -qs "$opt/app/drakter" /etc/apparmor.d/*; then
  profile="$opt/apparmor-drakter-app"
  cat >"$profile" <<EOF
# Perfil AppArmor de Drakter (AppImage extraído). Solo permite user namespaces al binario.
abi <abi/4.0>,
include <tunables/global>

profile drakter-app $opt/app/drakter flags=(unconfined) {
  userns,
  include if exists <local/drakter-app>
}
EOF
  warn "el sandbox de Electron necesita un perfil AppArmor (Ubuntu 24+). Una sola vez, con sudo:
        sudo install -m 644 \"$profile\" /etc/apparmor.d/drakter-app && sudo apparmor_parser -r /etc/apparmor.d/drakter-app"
else
  ok "sandbox de Electron: permitido"
fi

echo "──"
if [ "$problems" = 0 ]; then
  echo "Listo. Abre Drakter desde el menú o con: drakter-app"
else
  echo "Instalado con $problems aviso(s). Arregla lo indicado y abre Drakter con: drakter-app"
fi
