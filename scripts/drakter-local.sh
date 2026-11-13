#!/usr/bin/env bash
# Deja Drakter corriendo en el escritorio, desacoplado de la terminal (solo desarrollo).
#   drakter-local.sh start [stub|anthropic]   (por defecto: stub)
#   drakter-local.sh stop | status
# Logs: /tmp/drakter-dev.log (Electron + backend) y /tmp/drakter-stub.log.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dev_pid_file="/tmp/drakter-dev.pid"
stub_pid_file="/tmp/drakter-stub.pid"
stub_port=28517

alive() { [ -f "$1" ] && kill -0 -- "-$(cat "$1")" 2>/dev/null; }

stop_one() {
  alive "$1" || { rm -f "$1"; return 0; }
  local pgid; pgid="$(cat "$1")"
  kill -TERM -- "-$pgid" 2>/dev/null || true
  for _ in {1..50}; do kill -0 -- "-$pgid" 2>/dev/null || break; sleep 0.1; done
  kill -KILL -- "-$pgid" 2>/dev/null || true
  rm -f "$1"
}

start() {
  local provider="${1:-stub}"
  alive "$dev_pid_file" && { echo "Drakter ya está en marcha (status/stop)."; exit 0; }
  export PATH="$HOME/.local/bin:$PATH"
  # Sesión gráfica del usuario, aunque se lance desde otra terminal.
  export DISPLAY="${DISPLAY:-:0}"
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  [ -n "${WAYLAND_DISPLAY:-}" ] || { [ -S "$XDG_RUNTIME_DIR/wayland-0" ] && export WAYLAND_DISPLAY=wayland-0; } || true
  # AppArmor restringe userns y chrome-sandbox no es root:4755 (README, "Sandbox de Electron").
  export DRAKTER_DEV_NO_SANDBOX=1 ELECTRON_DISABLE_SANDBOX=1

  case "$provider" in
    stub)
      export DRAKTER_MODEL_PROVIDER=dev_stub
      if ! alive "$stub_pid_file"; then
        mkdir -p /var/tmp/drakter-stub/sandbox
        # setsid puede hacer fork: el pid lo escribe el propio líder de sesión (= pgid).
        setsid bash -c 'echo $$ >"$1"; shift; exec "$@"' _ "$stub_pid_file" \
          nohup python3.12 -I "$root/tools/dev-llm-stub/server.py" --port "$stub_port" \
          --var sandbox=/var/tmp/drakter-stub/sandbox >/tmp/drakter-stub.log 2>&1 </dev/null &
      fi
      ;;
    anthropic) export DRAKTER_MODEL_PROVIDER=anthropic ;;
    *) echo "Proveedor desconocido: $provider (stub|anthropic)" >&2; exit 2 ;;
  esac

  setsid bash -c 'echo $$ >"$1"; shift; exec "$@"' _ "$dev_pid_file" \
    nohup "$root/scripts/dev.sh" all >/tmp/drakter-dev.log 2>&1 </dev/null &
  sleep 0.5
  echo "Drakter arrancando (modelo: $provider). Log: /tmp/drakter-dev.log"
}

case "${1:-}" in
  start) start "${2:-stub}" ;;
  stop) stop_one "$dev_pid_file"; stop_one "$stub_pid_file"; echo "Drakter parado." ;;
  status)
    alive "$dev_pid_file" && echo "app: en marcha" || echo "app: parada"
    alive "$stub_pid_file" && echo "stub: en marcha (:$stub_port)" || echo "stub: parado"
    ;;
  *) echo "Uso: $(basename "$0") start [stub|anthropic] | stop | status" >&2; exit 2 ;;
esac
