#!/usr/bin/env bash
# Perfiles de voz: listar | comprobar | probar <perfil> ["texto"]. Ayuda: voces.sh --help
# Usa el venv de Fish (httpx + pydantic) o, si no está, el del backend.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data="${XDG_DATA_HOME:-$HOME/.local/share}/drakter"
python="${DRAKTER_VOCES_PYTHON:-}"
if [ -z "$python" ]; then
  for candidate in "$data/venvs/fish/bin/python" "$root/backend/.venv/bin/python"; do
    if [ -x "$candidate" ]; then python="$candidate"; break; fi
  done
fi
if [ -z "$python" ]; then
  echo "voces.sh: no encuentro Python con httpx y pydantic." >&2
  echo "  Instala el venv de Fish en $data/venvs/fish o ejecuta: cd backend && uv sync" >&2
  exit 2
fi
export PYTHONPATH="$root/contracts/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$python" "$root/scripts/voces.py" "$@"
