#!/usr/bin/env bash
# Runs a real Hermes through the DEV stub. Proves the wiring only, never model quality.
# Usage: check_hermes.sh <hermes-venv> [work-dir]
set -euo pipefail

VENV=${1:?usage: check_hermes.sh <hermes-venv> [work-dir]}
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d "${2:-${TMPDIR:-/var/tmp}}/dev-stub-check.XXXXXX")
PORT=${STUB_PORT:-28517}
HERMES="$VENV/bin/hermes"
SANDBOX="$WORK/sandbox"
FAILURES=0

# HOME is replaced too, so no credentials of the real user are in reach.
# DRAKTER_ENV stays inherited: the stub must keep its refusal in production.
export HERMES_HOME="$WORK/home" HOME="$WORK/user-home"
unset ANTHROPIC_API_KEY ANTHROPIC_TOKEN ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL OPENAI_API_KEY OPENAI_BASE_URL
unset CLAUDE_CODE_OAUTH_TOKEN HERMES_YOLO_MODE
mkdir -p "$HERMES_HOME" "$HOME" "$SANDBOX/canario"
touch "$SANDBOX/canario/testigo"

health() { python3 -I -c "import urllib.request as u; u.urlopen('http://127.0.0.1:$PORT/health', timeout=1)" 2>/dev/null; }

# A stale stub on this port would answer for code and a sandbox that are not these.
if health; then
  echo "ABORT: el puerto $PORT ya esta ocupado" >&2
  exit 70
fi

python3 -I "$HERE/server.py" --port "$PORT" --var "sandbox=$SANDBOX" 2>"$WORK/stub.log" &
STUB_PID=$!
trap 'kill "$STUB_PID" 2>/dev/null || true' EXIT
for _ in $(seq 50); do
  health && break
  kill -0 "$STUB_PID" 2>/dev/null || break
  sleep 0.1
done
if ! kill -0 "$STUB_PID" 2>/dev/null || ! health; then
  echo "ABORT: el stub no arranco" >&2
  cat "$WORK/stub.log" >&2
  exit 70
fi

"$HERMES" config set model.provider custom >/dev/null
"$HERMES" config set model.api_mode anthropic_messages >/dev/null
"$HERMES" config set model.base_url "http://127.0.0.1:$PORT" >/dev/null
"$HERMES" config set model.default drakter-dev-stub >/dev/null

run() { # name expected toolsets
  local name=$1 expected=$2 toolsets=$3 output
  output=$(timeout 180 "$HERMES" chat -q "[stub:$name] prueba" -t "$toolsets" 2>&1 </dev/null) || true
  printf '%s\n' "$output" >"$WORK/$name.out"
  if grep -qF -- "$expected" <<<"$output"; then
    echo "OK   $name"
  else
    echo "FAIL $name (salida en $WORK/$name.out)"
    FAILURES=$((FAILURES + 1))
  fi
}

run conversacion "guionizada" file
run herramienta-permitida "DEV-STUB-NOTA-7f3a" file
run herramienta-no-permitida "Herramienta rechazada por Hermes" file
run accion-destructiva "Accion bloqueada" terminal
run inyeccion-documento "La orden inyectada quedo bloqueada" file,terminal

if [ -e "$SANDBOX/canario/testigo" ]; then
  echo "OK   canario intacto (bloqueo en modo desatendido, no aprobacion de usuario)"
else
  echo "FAIL canario borrado"
  FAILURES=$((FAILURES + 1))
fi
echo "--- log del stub ($WORK/stub.log)"
grep -F 'scenario=' "$WORK/stub.log" || true
exit "$FAILURES"
