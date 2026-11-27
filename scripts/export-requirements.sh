#!/usr/bin/env bash
# Genera backend/requirements.txt desde backend/uv.lock (mismas versiones fijadas), para quien
# prefiera crear el venv con `python3.12 -m venv` y `pip` en lugar de `uv sync`.
#
#   scripts/export-requirements.sh           reescribe backend/requirements.txt
#   scripts/export-requirements.sh --check   sale con 1 si no coincide con uv.lock (lo usa el CI)
#
# Fuente de verdad: backend/pyproject.toml + backend/uv.lock. Tras cambiar dependencias
# (`uv add`, `uv lock`), ejecuta este script y haz commit de los dos archivos.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$repo/backend/requirements.txt"
command -v uv >/dev/null || { echo "falta uv: https://docs.astral.sh/uv/" >&2; exit 2; }

render() {
  cat <<'HEAD'
# Dependencias del backend de Drakter (Python 3.12), fijadas desde backend/uv.lock.
# GENERADO por scripts/export-requirements.sh: no editar a mano.
#
# Instalar desde la carpeta backend/ (la ruta de los contratos es relativa a ella):
#   cd backend
#   python3.12 -m venv .venv
#   source .venv/bin/activate
#   pip install --upgrade pip
#   pip install -r requirements.txt
#
# Alternativa recomendada, equivalente: cd backend && uv sync --frozen
HEAD
  (cd "$repo/backend" && uv export --frozen --no-dev --no-hashes --no-header --format requirements-txt)
}

if [ "${1:-}" = "--check" ]; then
  if diff -u "$out" <(render) >/dev/null; then
    echo "backend/requirements.txt al día con uv.lock"
  else
    diff -u "$out" <(render) | head -40 >&2 || true
    echo "backend/requirements.txt no coincide con uv.lock: ejecuta scripts/export-requirements.sh" >&2
    exit 1
  fi
else
  render > "$out"
  echo "escrito $out"
fi
