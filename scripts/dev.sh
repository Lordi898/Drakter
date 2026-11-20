#!/usr/bin/env bash
# Arranca Drakter en desarrollo: dev.sh [all|desktop]. No instala nada.
set -euo pipefail

# Un padre Electron deja ELECTRON_RUN_AS_NODE=1 en el entorno: Electron arrancaría como Node.
unset ELECTRON_RUN_AS_NODE ELECTRON_NO_ATTACH_CONSOLE

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$root/backend"
desktop_dir="$root/desktop"
venv_python="$backend_dir/.venv/bin/python"
desktop_pid=""

usage() { echo "Uso: $(basename "$0") [all|backend|desktop]" >&2; }

die() {
  echo "dev.sh: $1" >&2
  echo "  Resuélvelo con: $2" >&2
  exit 1
}

require_backend() {
  [ -d "$backend_dir" ] || die "backend/ no está en este checkout" "git checkout main && git pull --ff-only"
  [ -x "$venv_python" ] || die "falta backend/.venv" "cd backend && uv sync --frozen"
  case "$("$venv_python" --version 2>&1)" in
    "Python 3.12."*) ;;
    *) die "backend/.venv no es Python 3.12" "rm -rf backend/.venv && cd backend && uv sync --frozen" ;;
  esac
}

require_desktop() {
  [ -d "$desktop_dir" ] || die "desktop/ no está en este checkout" "git checkout main && git pull --ff-only"
  command -v node >/dev/null || die "node no está en el PATH" "instala Node y vuelve a abrir la terminal"
  command -v npm >/dev/null || die "npm no está en el PATH" "instala Node y vuelve a abrir la terminal"
  [ -d "$desktop_dir/node_modules" ] || die "falta desktop/node_modules" "cd desktop && npm ci"
  # Electron 45 no trae postinstall: el paso idempotente descarga el binario si falta.
  node "$desktop_dir/scripts/ensure-electron.cjs" >&2 \
    || die "no se pudo obtener el binario de Electron" "cd desktop && node scripts/ensure-electron.cjs"
  [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || die "no hay sesión gráfica" "ejecuta dev.sh desde el escritorio o exporta DISPLAY"
}

# TERM a todo el grupo de procesos; KILL si sigue vivo a los 5 s.
stop_group() {
  [ -n "$1" ] || return 0
  kill -TERM -- "-$1" 2>/dev/null || return 0
  local _
  for _ in {1..50}; do
    kill -0 -- "-$1" 2>/dev/null || return 0
    sleep 0.1
  done
  kill -KILL -- "-$1" 2>/dev/null || true
}

cleanup() {
  trap '' INT TERM HUP
  stop_group "$desktop_pid"
}

set_traps() {
  trap cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  trap 'exit 129' HUP
}

# Primer plano para el usuario, pero con wait: bash solo atiende señales entre órdenes.
run_desktop() {
  local status=0
  (cd "$desktop_dir" && exec setsid npm run dev) &
  desktop_pid=$!
  wait "$desktop_pid" || status=$?
  exit "$status"
}

# D-14: Electron main lanza el backend (handshake por stdin, puerto efímero anunciado
# por stdout), así que aquí solo se valida que ambos lados estén listos.
run_all() {
  require_backend
  require_desktop
  command -v hermes-python >/dev/null || [ -n "${DRAKTER_HERMES_PYTHON:-}" ] \
    || echo "dev.sh: aviso: no hay hermes-python en el PATH; el chat no funcionará (ver docs/RUN_STATE.md)" >&2
  set_traps
  run_desktop
}

[ "$#" -le 1 ] || { usage; exit 2; }

case "${1:-all}" in
  all) run_all ;;
  backend)
    die "el backend no se arranca solo: lo lanza Electron con credenciales por stdin (D-14)" "scripts/dev.sh all"
    ;;
  desktop)
    require_desktop
    set_traps
    run_desktop
    ;;
  *) usage; exit 2 ;;
esac
