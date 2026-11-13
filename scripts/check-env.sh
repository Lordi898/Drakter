#!/usr/bin/env bash
# Comprueba el entorno de desarrollo. Sale con 1 si hay algún FALTA.
# El .env de usuario solo se inspecciona con [ -e ] y stat: nunca se abre.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
oks=0 warnings=0 missing=0

ok() { echo "OK    $*"; oks=$((oks + 1)); }
warn() { echo "AVISO $*"; warnings=$((warnings + 1)); }
fail() { echo "FALTA $*"; missing=$((missing + 1)); }

is_python312() { case "$("$1" --version 2>&1)" in "Python 3.12."*) ;; *) return 1 ;; esac; }

# Los runtimes nunca viven en directorios temporales (docs/DECISIONS.md): una limpieza de
# /tmp o /var/tmp los borra y rompe todo lo que cuelga de ellos.
is_temp_path() { case "$1" in /tmp|/tmp/*|/var/tmp|/var/tmp/*) return 0 ;; esac; return 1; }

# stable_link <nombre> <ruta> <comando de arreglo>: la ruta debe existir (enlaces no rotos)
# y ni ella ni su destino final pueden estar bajo /tmp o /var/tmp.
stable_link() {
  local name="$1" path="$2" fix="$3" target
  if [ -L "$path" ] && [ ! -e "$path" ]; then
    fail "$name es un enlace roto ($path -> $(readlink "$path")). Arreglo: $fix"
    return 1
  fi
  [ -e "$path" ] || return 0
  target="$(readlink -f "$path")"
  if is_temp_path "$target" || is_temp_path "$(readlink "$path" 2>/dev/null || true)"; then
    fail "$name apunta a una ruta temporal ($target). Arreglo: $fix"
    return 1
  fi
  return 0
}

# stable_venv <nombre> <directorio> <comando de arreglo>: pyvenv.cfg (home/executable) y el
# intérprete del venv no pueden resolver a rutas temporales ni estar rotos.
stable_venv() {
  local name="$1" dir="$2" fix="$3" cfg="$2/pyvenv.cfg" line value
  [ -d "$dir" ] || return 0
  if [ -f "$cfg" ]; then
    while IFS= read -r line; do
      case "$line" in "home = "*|"executable = "*) value="${line#*= }" ;; *) continue ;; esac
      if is_temp_path "$value"; then
        fail "$name: $cfg apunta a una ruta temporal ($value). Arreglo: $fix"
        return 1
      fi
    done <"$cfg"
  fi
  if [ ! -x "$dir/bin/python" ] || ! "$dir/bin/python" -c '' 2>/dev/null; then
    fail "$name: $dir/bin/python está roto. Arreglo: $fix"
    return 1
  fi
  stable_link "$name" "$dir/bin/python" "$fix"
}

# Como command -v, pero también devuelve enlaces rotos (command -v los ignora).
path_entry() {
  local dir IFS=:
  for dir in $PATH; do
    [ -e "${dir:-.}/$1" ] || [ -L "${dir:-.}/$1" ] && { echo "${dir:-.}/$1"; return 0; }
  done
  return 0
}

fix_py() { echo "uv python install $1 && ln -sfn \"\$(uv python find --managed-python $1)\" ~/.local/bin/python$1"; }

stable_link python3.12 "$(path_entry python3.12)" "$(fix_py 3.12)" || true
stable_link python3.14 "$(path_entry python3.14)" "$(fix_py 3.14)" || true
if ! command -v python3.12 >/dev/null; then
  fail "python3.12 no está en el PATH"
elif is_python312 python3.12; then
  ok "$(python3.12 --version 2>&1)"
else
  fail "python3.12 no es 3.12.x: $(python3.12 --version 2>&1 || true)"
fi

# Hermes va en su propio venv con Python >=3.14; el backend sigue en 3.12.
hermes_python=""
for candidate in python3.14 python3; do
  if command -v "$candidate" >/dev/null \
    && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 14))' 2>/dev/null; then
    hermes_python="$candidate"
    break
  fi
done
if [ -n "$hermes_python" ]; then
  ok "$("$hermes_python" --version 2>&1) para el venv de Hermes ($hermes_python)"
else
  warn "no hay Python >=3.14: hará falta para el venv de Hermes"
fi

# hermes-python: script o enlace; debe resolver al venv estable de Hermes.
hermes_fix="scripts/install-hermes.sh"
hermes_bin="$(path_entry hermes-python)"
if [ -z "$hermes_bin" ]; then
  warn "hermes-python no está en el PATH (ejecuta $hermes_fix)"
else
  stable_link hermes-python "$hermes_bin" "$hermes_fix" || true
  hermes_target="$(sed -n 's/^exec "\{0,1\}\([^" ]*\)"\{0,1\}.*/\1/p' "$hermes_bin" 2>/dev/null | head -n1 || true)"
  if [ -n "$hermes_target" ]; then
    if is_temp_path "$hermes_target" || is_temp_path "$(readlink -f "$hermes_target" 2>/dev/null || true)"; then
      fail "hermes-python ejecuta una ruta temporal ($hermes_target). Arreglo: $hermes_fix"
    elif [ ! -x "$hermes_target" ]; then
      fail "hermes-python apunta a $hermes_target, que no existe. Arreglo: $hermes_fix"
    else
      ok "hermes-python -> $hermes_target"
    fi
  fi
fi

# Cualquier otro venv del proyecto en los datos de usuario.
data_dir="${DRAKTER_DATA_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/drakter}"
for venv in "$data_dir"/venvs/*/; do
  [ -d "$venv" ] || continue
  venv="${venv%/}"
  stable_venv "venv $(basename "$venv")" "$venv" "rm -rf \"$venv\" y recréalo (Hermes: scripts/install-hermes.sh)" \
    && ok "venv $(basename "$venv") sin rutas temporales"
done

if command -v node >/dev/null; then ok "node $(node --version)"; else fail "node no está en el PATH"; fi
if command -v npm >/dev/null; then ok "npm $(npm --version)"; else fail "npm no está en el PATH"; fi
if command -v uv >/dev/null; then ok "$(uv --version)"; else warn "uv no está en el PATH: solo hace falta para crear el venv"; fi

env_file="${XDG_CONFIG_HOME:-$HOME/.config}/drakter/.env"
if [ -e "$env_file" ]; then
  perms="$(stat -L -c %a "$env_file")"
  if [ "$perms" = 600 ]; then
    ok "$env_file existe con permisos 600"
  else
    warn "$env_file tiene permisos $perms, deberían ser 600 (chmod 600 \"$env_file\")"
  fi
else
  warn "$env_file no existe: el backend usará valores por defecto"
fi

if [ ! -d "$root/backend" ]; then
  warn "backend/ no está en este checkout"
elif [ ! -x "$root/backend/.venv/bin/python" ]; then
  fail "backend/.venv no existe (cd backend && uv sync --frozen)"
elif ! stable_venv "backend/.venv" "$root/backend/.venv" "rm -rf backend/.venv && cd backend && uv sync --locked"; then
  :
elif is_python312 "$root/backend/.venv/bin/python"; then
  ok "backend/.venv con $("$root/backend/.venv/bin/python" --version 2>&1)"
else
  fail "backend/.venv no es Python 3.12 (rm -rf backend/.venv && cd backend && uv sync --frozen)"
fi

if [ ! -d "$root/desktop" ]; then
  warn "desktop/ no está en este checkout"
elif [ -d "$root/desktop/node_modules" ]; then
  ok "desktop/node_modules presente"
else
  fail "desktop/node_modules no existe (cd desktop && npm ci)"
fi

# Con AppArmor restringiendo userns, Electron aborta si chrome-sandbox no es root con setuid.
sandbox="$root/desktop/node_modules/electron/dist/chrome-sandbox"
if [ -e "$sandbox" ] && [ -z "${ELECTRON_DISABLE_SANDBOX:-}" ] \
  && [ "$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)" = 1 ] \
  && [ "$(stat -L -c '%u %a' "$sandbox")" != "0 4755" ]; then
  warn "Electron abortará por su sandbox: ver README, sección Sandbox de Electron"
fi

if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
  ok "sesión gráfica disponible"
else
  warn "no hay DISPLAY ni WAYLAND_DISPLAY: Electron necesita sesión gráfica"
fi

echo "Resumen: $oks OK, $warnings AVISO, $missing FALTA"
[ "$missing" -eq 0 ]
