#!/bin/sh
# Instala el OCR de Drakter (hands/ocr) en su propio venv, fuera del repo:
#   venv    ~/.local/share/drakter/venvs/ocr   (Python 3.12, rapidocr 3.10.0, onnxruntime 1.32.0)
#   modelos ~/.local/share/drakter/models/ocr/ (PP-OCRv5 mobile: det, rec latin y cls; ~13 MB)
# Es la única vez que se descarga algo; en ejecución el OCR no usa la red. Requiere `uv`.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="$HOME/.local/share/drakter"
VENV="$DATA/venvs/ocr"
mkdir -p "$DATA/venvs"
chmod 700 "$DATA" "$DATA/venvs" 2>/dev/null || true
command -v uv >/dev/null 2>&1 || { echo "Falta uv (https://docs.astral.sh/uv/)." >&2; exit 1; }
[ -x "$VENV/bin/python" ] || uv venv --python 3.12 "$VENV"
uv pip install --python "$VENV/bin/python" "rapidocr==3.10.0" "onnxruntime==1.32.0" "$HERE"
"$VENV/bin/python" -I -m drakter_ocr --install-models  # DRAKTER_OCR_MODELS_FROM=<dir> copia en vez de descargar
echo "OCR listo en $VENV"
