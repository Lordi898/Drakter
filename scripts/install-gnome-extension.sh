#!/usr/bin/env bash
# Instala la extensión de GNOME Shell drakter-companion@drakter (modo flotante)
# para el usuario actual, compila sus esquemas y la deja activada para el
# próximo inicio de sesión.
#
# Uso: scripts/install-gnome-extension.sh [--no-enable] [--uninstall] [--dev]
#   --no-enable  solo copia y compila (no toca enabled-extensions)
#   --uninstall  la desactiva y borra la carpeta instalada
#   --dev        copia extension.js tal cual, con la interfaz de depuración (solo
#                para el gnome-shell headless de las pruebas, nunca en tu sesión)
#
# Sin --dev se instala una copia sin los bloques `// @debug-begin … // @debug-end`
# (DebugApi, que inyecta teclado y ratón, y la confianza en los drivers de prueba)
# y sin test/.
#
# Destino: ${XDG_DATA_HOME:-~/.local/share}/gnome-shell/extensions/drakter-companion@drakter
# En Wayland, GNOME Shell no recarga extensiones en caliente: hay que cerrar la
# sesión y volver a entrar una vez por cada versión nueva.
set -euo pipefail

UUID=drakter-companion@drakter
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/desktop/gnome-extension/$UUID"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
DEST="$DATA/gnome-shell/extensions/$UUID"
ENABLE=1
UNINSTALL=0
DEV=0

for arg in "$@"; do
  case "$arg" in
    --no-enable) ENABLE=0 ;;
    --uninstall) UNINSTALL=1 ;;
    --dev) DEV=1 ;;
    -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción desconocida: $arg (usa --help)" >&2; exit 2 ;;
  esac
done

enabled_list() { gsettings get org.gnome.shell enabled-extensions 2>/dev/null || echo "@as []"; }

if [ "$UNINSTALL" = 1 ]; then
  gnome-extensions disable "$UUID" 2>/dev/null || true
  cur="$(enabled_list)"
  if [[ "$cur" == *"'$UUID'"* ]]; then
    new="$(printf '%s' "$cur" | sed -e "s/, '$UUID'//; s/'$UUID', //; s/'$UUID'//")"
    gsettings set org.gnome.shell enabled-extensions "$new"
  fi
  [ -d "$DEST" ] && rm -rf -- "$DEST"
  echo "Extensión $UUID desinstalada. Cierra la sesión para que GNOME Shell la descargue del todo."
  exit 0
fi

[ -f "$SRC/metadata.json" ] || { echo "No encuentro la extensión en $SRC" >&2; exit 1; }
command -v glib-compile-schemas >/dev/null || { echo "Falta glib-compile-schemas (paquete libglib2.0-bin)." >&2; exit 1; }

if command -v gnome-shell >/dev/null; then
  major="$(gnome-shell --version 2>/dev/null | sed -n 's/^GNOME Shell \([0-9]*\).*/\1/p')"
  if [ -n "$major" ] && [ "$major" != 50 ]; then
    echo "Aviso: la extensión está hecha para GNOME Shell 50 y aquí hay GNOME Shell $major." >&2
  fi
else
  echo "Aviso: no encuentro gnome-shell; el modo flotante solo funciona en GNOME (Wayland)." >&2
fi

if [ -d "$DEST" ]; then rm -rf -- "$DEST"; fi
mkdir -p "$DEST/schemas" "$DEST/icons"
install -m 0644 "$SRC/metadata.json" "$SRC/org.drakter.Companion1.xml" "$DEST/"
if [ "$DEV" = 1 ]; then
  install -m 0644 "$SRC/extension.js" "$DEST/"
  echo "Aviso: copia de desarrollo, con la interfaz de depuración (DRAKTER_COMPANION_DEBUG=1)." >&2
else
  # Quita los bloques de depuración. Si queda algo de ellos, no se instala nada.
  sed '/\/\/ @debug-begin/,/\/\/ @debug-end/d' "$SRC/extension.js" >"$DEST/extension.js"
  chmod 0644 "$DEST/extension.js"
  if grep -q 'DebugApi\|DRAKTER_COMPANION_DEBUG\|DRAKTER_COMPANION_TRUST\|@debug-' "$DEST/extension.js"; then
    rm -rf -- "$DEST"
    echo "No se ha podido quitar la interfaz de depuración de extension.js: no se instala." >&2
    exit 1
  fi
  if command -v node >/dev/null; then
    cp "$DEST/extension.js" "$DEST/.check.mjs"
    if ! node --check "$DEST/.check.mjs" 2>/dev/null; then
      rm -rf -- "$DEST"
      echo "extension.js sin depuración no es JavaScript válido: no se instala." >&2
      exit 1
    fi
    rm -f -- "$DEST/.check.mjs"
  fi
fi
install -m 0644 "$SRC"/schemas/*.gschema.xml "$DEST/schemas/"
install -m 0644 "$SRC"/icons/*.svg "$DEST/icons/"
glib-compile-schemas --strict "$DEST/schemas"
echo "Extensión instalada en $DEST"

if [ "$ENABLE" = 1 ]; then
  if [ "$(gsettings get org.gnome.shell disable-user-extensions 2>/dev/null)" = "true" ]; then
    echo "Aviso: las extensiones de usuario están desactivadas en GNOME (disable-user-extensions)." >&2
    echo "       Actívalas en la app Extensiones para que Drakter pueda usar el modo flotante." >&2
  fi
  cur="$(enabled_list)"
  if [[ "$cur" != *"'$UUID'"* ]]; then
    if [[ "$cur" == "@as []" || "$cur" == "[]" ]]; then new="['$UUID']"; else new="${cur%]}, '$UUID']"; fi
    gsettings set org.gnome.shell enabled-extensions "$new"
  fi
  echo "Queda activada para el próximo inicio de sesión."
fi

if [ "${XDG_SESSION_TYPE:-}" = wayland ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
  echo
  echo "IMPORTANTE: en Wayland hay que cerrar la sesión y volver a entrar una vez para que"
  echo "GNOME Shell cargue la extensión (o la versión nueva). Después verás el icono de Drakter"
  echo "en el panel mientras Drakter esté conectado, y Super+Alt+D activará el modo flotante."
fi
