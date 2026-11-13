#!/usr/bin/env bash
# Instala el runtime de la voz v2 (Pipecat 1.16.0, py3.12) en una ubicación ESTABLE.
# Idempotente: se puede repetir; solo instala lo que falte según voice/requirements.lock.
# Regla del proyecto: runtimes y modelos nunca viven en /tmp ni /var/tmp, y el código
# no descarga nada en ejecución (docs/DECISIONS.md, voz v2).
#
# Uso: scripts/install-voice.sh [--relock]
#   --relock   regenera voice/requirements.lock desde voice/pyproject.toml
#
# Variables opcionales:
#   DRAKTER_RUNTIME_DIR   raíz de runtimes (por defecto ~/.local/share/drakter)
#   DRAKTER_KOKORO_SRC    de dónde copiar Kokoro si falta en models/kokoro
set -euo pipefail

PY_VERSION="3.12"

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="${DRAKTER_RUNTIME_DIR:-$HOME/.local/share/drakter}"
venv="$runtime/venvs/voice"
models="$runtime/models"
kokoro_src="${DRAKTER_KOKORO_SRC:-$HOME/.drakter-backup/tmp-drakter-3-work/models}"
lock="$repo/voice/requirements.lock"
relock=0
[ "${1:-}" = "--relock" ] && relock=1

case "$(realpath -m "$runtime")" in
  /tmp|/tmp/*|/var/tmp|/var/tmp/*)
    echo "ERROR: $runtime está en un directorio temporal; elige una ruta estable." >&2
    exit 1 ;;
esac
command -v uv >/dev/null || { echo "ERROR: falta uv en el PATH" >&2; exit 1; }

mkdir -p "$runtime/venvs" "$models"

# 1. Venv con Python 3.12 gestionado por uv.
if [ ! -x "$venv/bin/python" ]; then
  uv python install "$PY_VERSION" >/dev/null 2>&1 || true
  uv venv --quiet --python "$PY_VERSION" "$venv"
fi
py="$venv/bin/python"
"$py" -c 'import sys; assert sys.version_info[:2] == (3, 12), sys.version' \
  || { echo "ERROR: $venv no es Python 3.12; bórralo y repite." >&2; exit 1; }

# 2. Lock: se genera una vez y se versiona. Sin --only-binary global.
if [ "$relock" = 1 ] || [ ! -f "$lock" ]; then
  uv pip compile --quiet --python "$py" "$repo/voice/pyproject.toml" -o "$lock"
  echo "Lock regenerado: $lock"
fi

# 3. Dependencias del lock + contratos en editable (apuntan a ESTE checkout).
uv pip install --quiet --python "$py" -r "$lock"
uv pip install --quiet --python "$py" -e "$repo/contracts/python"
if [ -f "$repo/.git" ]; then
  echo "AVISO: drakter-contracts queda enlazado a un worktree ($repo/contracts/python)." >&2
  echo "       Repite este script desde el checkout principal antes de borrar el worktree." >&2
fi

# 4. Kokoro: se copia desde la copia local si falta (nunca se descarga).
mkdir -p "$models/kokoro"
for f in kokoro-v1.0.int8.onnx voices-v1.0.bin; do
  if [ ! -s "$models/kokoro/$f" ] && [ -s "$kokoro_src/$f" ]; then
    cp "$kokoro_src/$f" "$models/kokoro/$f"
    echo "Copiado $f a $models/kokoro/"
  fi
done

# 5. Modelos: deben estar ya en disco. Error claro con la ruta si falta alguno.
missing=0
need() {
  if [ ! -s "$1" ]; then
    echo "ERROR: falta el modelo $1" >&2
    missing=1
  fi
}
moonshine="$models/moonshine/download.moonshine.ai/model"
for m in small-streaming-es tiny-streaming-es; do
  enc="$(find "$moonshine/$m" -name encoder.ort 2>/dev/null | head -n1)"
  need "${enc:-$moonshine/$m/<version>/encoder.ort}"
done
for f in hey_jarvis_v0.1.onnx melspectrogram.onnx embedding_model.onnx; do
  need "$models/openwakeword/$f"
done
need "$models/smart-turn/smart-turn-v3.2-cpu.onnx"
need "$models/kokoro/kokoro-v1.0.int8.onnx"
need "$models/kokoro/voices-v1.0.bin"
if [ "$missing" = 1 ]; then
  echo "ERROR: faltan modelos en $models (ver arriba). El venv sí quedó instalado." >&2
  exit 1
fi

# 6. Comprobación de imports.
"$py" - <<'PY'
from importlib.metadata import version

import aiortc, moonshine_voice, openwakeword, pipecat  # noqa: F401,E401
import drakter_contracts.voice_ipc  # noqa: F401

assert version("pipecat-ai") == "1.16.0", version("pipecat-ai")
print("Voz lista: pipecat", version("pipecat-ai"), "· moonshine", version("moonshine-voice"),
      "· openwakeword", version("openwakeword"), "· aiortc", version("aiortc"))
PY
echo "Venv: $venv"
echo "Modelos: $models"
