#!/usr/bin/env bash
# Atajo de GNOME Super+J → `drakter activate` (voz v2, V-17). Sin globalShortcut de Electron.
# Uso: scripts/install-shortcut.sh install|remove
# Idempotente: solo añade o quita su propia ruta de la lista de atajos personalizados.
# Si se instala con DRAKTER_DEV_NO_SANDBOX=1, el atajo arranca también así (solo desarrollo).
set -euo pipefail

SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
KEY="custom-keybindings"
ENTRY_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
ENTRY_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/drakter-activate/"
BINDING="<Super>j"
LAUNCHER="$(readlink -f "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/drakter")"

die() { echo "install-shortcut: $1" >&2; exit 1; }

command -v gsettings >/dev/null 2>&1 || die "falta gsettings (¿no es GNOME?)"
command -v python3 >/dev/null 2>&1 || die "falta python3"
[[ -x "$LAUNCHER" ]] || die "no encuentro el lanzador: $LAUNCHER"

# Lista actual ± nuestra ruta, sin duplicados y sin tocar las demás.
edit_list() {
  local action="$1" current
  current="$(gsettings get "$SCHEMA" "$KEY")"
  python3 - "$action" "$ENTRY_PATH" "$current" <<'EOF'
import ast, sys
action, path, raw = sys.argv[1], sys.argv[2], sys.argv[3].strip()
if raw.startswith("@as "):
    raw = raw[4:]
paths = [p for p in ast.literal_eval(raw) if p != path]
if action == "install":
    paths.append(path)
print("[" + ", ".join("'" + p.replace("'", "\\'") + "'" for p in paths) + "]")
EOF
}

case "${1:-}" in
  install)
    command="$LAUNCHER activate"
    if [[ "${DRAKTER_DEV_NO_SANDBOX:-}" == "1" ]]; then
      command="env DRAKTER_DEV_NO_SANDBOX=1 $command"
    fi
    gsettings set "$ENTRY_SCHEMA:$ENTRY_PATH" name "Drakter: activar voz"
    gsettings set "$ENTRY_SCHEMA:$ENTRY_PATH" command "$command"
    gsettings set "$ENTRY_SCHEMA:$ENTRY_PATH" binding "$BINDING"
    gsettings set "$SCHEMA" "$KEY" "$(edit_list install)"
    echo "Atajo instalado: $BINDING → $command"
    ;;
  remove)
    gsettings set "$SCHEMA" "$KEY" "$(edit_list remove)"
    for field in name command binding; do
      gsettings reset "$ENTRY_SCHEMA:$ENTRY_PATH" "$field"
    done
    echo "Atajo retirado"
    ;;
  *)
    echo "Uso: $0 install|remove" >&2
    exit 2
    ;;
esac
