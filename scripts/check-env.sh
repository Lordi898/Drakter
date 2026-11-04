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
