#!/usr/bin/env bash
# Instala Hermes (v0.22.7, commit fijado) en una ubicación ESTABLE, desde git (nunca PyPI).
# Idempotente: si ya está en el commit y el venv funciona, no toca nada.
# Regla del proyecto: los runtimes nunca viven en /tmp ni /var/tmp (docs/DECISIONS.md).
#
# Variables opcionales:
#   DRAKTER_RUNTIME_DIR  raíz de runtimes (por defecto ~/.local/share/drakter)
#   DRAKTER_BIN_DIR      dónde enlazar python3.14 y hermes-python (por defecto ~/.local/bin)
set -euo pipefail

HERMES_REPO="https://github.com/NousResearch/hermes-agent"
HERMES_TAG="v0.22.7"
HERMES_COMMIT="b200f5bc60e31588ba2cb60e288029c4a54ba5fa"
PY_VERSION="3.14"

runtime="${DRAKTER_RUNTIME_DIR:-$HOME/.local/share/drakter}"
bin_dir="${DRAKTER_BIN_DIR:-$HOME/.local/bin}"
src="$runtime/src/hermes-agent"
venv="$runtime/venvs/hermes"

case "$(realpath -m "$runtime")" in
  /tmp|/tmp/*|/var/tmp|/var/tmp/*)
    echo "ERROR: $runtime está en un directorio temporal; elige una ruta estable." >&2
    exit 1 ;;
esac
for tool in git uv; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta $tool en el PATH" >&2; exit 1; }
done

mkdir -p "$runtime/src" "$runtime/venvs" "$bin_dir"

# 1. Python 3.14 gestionado por uv (vive en ~/.local/share/uv, no en /tmp).
uv python install "$PY_VERSION" >/dev/null 2>&1 || true
py="$(uv python find --managed-python "$PY_VERSION")"
ln -sfn "$py" "$bin_dir/python3.14"

# 2. Clon en el commit fijado (se compara el commit; el pyproject del tag dice 0.0.0).
if [ ! -d "$src/.git" ]; then
  git clone --quiet "$HERMES_REPO" "$src"
fi
if [ "$(git -C "$src" rev-parse HEAD)" != "$HERMES_COMMIT" ]; then
  git -C "$src" fetch --quiet --tags origin
  git -C "$src" checkout --quiet --detach "$HERMES_COMMIT"
fi
[ "$(git -C "$src" rev-parse HEAD)" = "$HERMES_COMMIT" ] \
  || { echo "ERROR: el clon no está en $HERMES_COMMIT" >&2; exit 1; }

# 3. Venv con el lock del propio Hermes y los extras del contrato (anthropic, mcp).
# --compile-bytecode: el runner corre con -B y, sin .pyc, recompilaba openai/anthropic en cada
# primer turno (~1 s, LAT-1).
(cd "$src" && UV_PROJECT_ENVIRONMENT="$venv" uv sync --frozen --python "$py" \
  --extra anthropic --extra mcp --compile-bytecode)
"$venv/bin/python" -m compileall -q -x '/(tests|evals)/' "$src" >/dev/null || true

# 4. Enlace estable que usa el backend (DRAKTER_HERMES_PYTHON por defecto: hermes-python).
cat > "$bin_dir/hermes-python" <<WRAP
#!/bin/sh
# Hermes $HERMES_TAG (${HERMES_COMMIT%"${HERMES_COMMIT#???????}"}) en venv estable. Generado por scripts/install-hermes.sh.
exec "$venv/bin/python" "\$@"
WRAP
chmod +x "$bin_dir/hermes-python"

"$bin_dir/hermes-python" -c 'import sys; print("Hermes listo:", sys.version.split()[0])'
echo "Clon: $src ($HERMES_TAG, $HERMES_COMMIT)"
echo "Venv: $venv"
echo "Enlace: $bin_dir/hermes-python"
