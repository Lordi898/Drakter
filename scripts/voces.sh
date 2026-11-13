#!/usr/bin/env bash
# Perfiles de voz: listar | comprobar | probar <perfil> ["texto"]. Ayuda: voces.sh --help
# Usa el venv de Fish (httpx + pydantic) o, si no está, el del backend.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
data="${XDG_DATA_HOME:-$HOME/.local/share}/drakter"
python="${DRAKTER_VOCES_PYTHON:-}"
if [ -z "$python" ]; then
  for candidate in "$data/venvs/fish/bin/python" "$root/backend/.venv/bin/python"; do
    if [ -x "$candidate" ] && "$candidate" -c 'import httpx, pydantic' 2>/dev/null; then
      python="$candidate"; break
    fi
  done
fi
if [ -z "$python" ]; then
  echo "voces.sh: no encuentro un Python que funcione con httpx y pydantic." >&2
  echo "  Probé $data/venvs/fish y $root/backend/.venv (¿enlaces rotos o sin dependencias?)." >&2
  echo "  Arréglalo con: cd $root/backend && uv sync   (o define DRAKTER_VOCES_PYTHON)" >&2
  exit 2
fi
export PYTHONPATH="$root/contracts/python${PYTHONPATH:+:$PYTHONPATH}"
exec "$python" "$root/scripts/voces.py" "$@"
