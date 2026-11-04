#!/usr/bin/env bash
# Pasada integrada final: backend + stub LLM + Electron por CDP, con informe por casilla.
# No instala nada. El stub NO prueba Haiku 5.5. Opciones: verify-all.sh --help
# Salida: 0 sin fallos, 1 con algún FALLA, 2 si la pasada no pudo ejecutarse.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$root/backend"
python=""
args=("$@")
while [ "$#" -gt 0 ]; do
  case "$1" in
    --backend-dir) backend_dir="${2:?falta la ruta}"; shift ;;
    --backend-python) python="${2:?falta la ruta}"; shift ;;
  esac
  shift
done
python="${python:-$backend_dir/.venv/bin/python}"

if [ ! -x "$python" ]; then
  echo "verify-all.sh: falta $python" >&2
  echo "  Resuélvelo con: cd backend && uv sync" >&2
  exit 2
fi
case "$("$python" --version 2>&1)" in
  "Python 3.12."*) ;;
  *) echo "verify-all.sh: $python no es Python 3.12" >&2; exit 2 ;;
esac

# Datos y logs nunca en /tmp: pueden ocupar y deben sobrevivir para revisar un fallo.
case "${TMPDIR:-}" in ""|/tmp|/tmp/*) export TMPDIR=/var/tmp/drakter-e2e ;; esac
mkdir -p "$TMPDIR"
chmod 700 "$TMPDIR"
exec "$python" "$root/tests/e2e/run.py" "${args[@]}"
