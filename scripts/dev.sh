#!/usr/bin/env bash
# Arranca Drakter en desarrollo: dev.sh [all|backend|desktop]. No instala nada.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$root/backend"
desktop_dir="$root/desktop"
venv_python="$backend_dir/.venv/bin/python"
health_timeout=30 # segundos
backend_pid="" desktop_pid=""

usage() { echo "Uso: $(basename "$0") [all|backend|desktop]" >&2; }

die() {
  echo "dev.sh: $1" >&2
  echo "  Resuélvelo con: $2" >&2
  exit 1
}

require_backend() {
  [ -d "$backend_dir" ] || die "backend/ no está en este checkout" "git merge drakter/backend-base"
  [ -x "$venv_python" ] || die "falta backend/.venv" "cd backend && uv sync --frozen"
  case "$("$venv_python" --version 2>&1)" in
    "Python 3.12."*) ;;
    *) die "backend/.venv no es Python 3.12" "rm -rf backend/.venv && cd backend && uv sync --frozen" ;;
  esac
}

require_desktop() {
  [ -d "$desktop_dir" ] || die "desktop/ no está en este checkout" "git merge drakter/build"
  command -v node >/dev/null || die "node no está en el PATH" "instala Node y vuelve a abrir la terminal"
  command -v npm >/dev/null || die "npm no está en el PATH" "instala Node y vuelve a abrir la terminal"
  [ -d "$desktop_dir/node_modules" ] || die "falta desktop/node_modules" "cd desktop && npm ci"
  [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || die "no hay sesión gráfica" "ejecuta dev.sh desde el escritorio o exporta DISPLAY"
}

# stderr descartado: un error de validación podría repetir valores del .env.
effective_port() {
  (cd "$backend_dir" && "$venv_python" -c \
    'from app.core.config import load_settings; print(load_settings().port)' 2>/dev/null) \
    || die "no se pudo leer la configuración del backend" "scripts/dev.sh backend (muestra el error)"
}

port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

health_ok() {
  "$venv_python" -I -c '
import json, sys, urllib.request as r
opener = r.build_opener(r.ProxyHandler({}))
body = json.load(opener.open(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=2))
sys.exit(body.get("status") != "ok")
' "$1" 2>/dev/null
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
  stop_group "$backend_pid"
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

run_all() {
  require_backend
  require_desktop
  local port
  port="$(effective_port)"
  port_in_use "$port" && die "el puerto $port ya está en uso" "ss -ltnp 'sport = :$port' (y para ese proceso o cambia DRAKTER_PORT)"

  set_traps
  # setsid da a cada lado su propio grupo: npm no reenvía señales hasta Electron.
  (cd "$backend_dir" && exec setsid "$venv_python" -m app) &
  backend_pid=$!

  local deadline=$((SECONDS + health_timeout))
  until health_ok "$port"; do
    if ! kill -0 "$backend_pid" 2>/dev/null; then
      echo "dev.sh: el backend terminó antes de responder en /health" >&2
      exit 1
    fi
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "dev.sh: /health no respondió en ${health_timeout} s (puerto $port)" >&2
      exit 1
    fi
    sleep 0.2
  done
  echo "dev.sh: backend listo en http://127.0.0.1:$port"

  run_desktop
}

[ "$#" -le 1 ] || { usage; exit 2; }

case "${1:-all}" in
  all) run_all ;;
  backend)
    require_backend
    cd "$backend_dir"
    exec "$venv_python" -m app
    ;;
  desktop)
    require_desktop
    set_traps
    run_desktop
    ;;
  *) usage; exit 2 ;;
esac
