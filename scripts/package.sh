#!/usr/bin/env bash
# Construye los instaladores de Linux en desktop/release/.
#
#   scripts/package.sh [appimage|deb|all]     (por defecto: all)
#
# 1. backend congelado con PyInstaller (desktop/electron-builder.build-backend.mjs)
# 2. npm ci (si falta node_modules) y npm run build
# 3. electron-builder 26.18.0 con desktop/electron-builder.yml
# No empaqueta runtimes (venvs de voz y Hermes) ni modelos: ver scripts/install-appimage.sh.
set -euo pipefail
unset ELECTRON_RUN_AS_NODE ELECTRON_NO_ATTACH_CONSOLE

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-all}" in
  appimage) targets=(AppImage) ;;
  deb) targets=(deb) ;;
  all) targets=(deb AppImage) ;;
  *) echo "Uso: $(basename "$0") [appimage|deb|all]" >&2; exit 2 ;;
esac
export PATH="$HOME/.local/bin:$PATH"
for tool in uv node npm npx; do
  command -v "$tool" >/dev/null || { echo "ERROR: falta $tool en el PATH" >&2; exit 1; }
done

# fpm (.deb) copia ~330 MB y comprime con xz en TMPDIR: si /tmp es un tmpfs justo, falla.
export TMPDIR="${DRAKTER_BUILD_TMP:-$HOME/.cache/drakter-build/tmp}"
mkdir -p "$TMPDIR"

cd "$repo/desktop"
echo "── backend congelado"
node electron-builder.build-backend.mjs
[ -d node_modules ] || { echo "── npm ci"; npm ci --no-audit --no-fund; }
echo "── npm run build"
npm run build
echo "── electron-builder (${targets[*]})"
npx --yes electron-builder@26.18.0 --config electron-builder.yml --linux "${targets[@]}" -c.npmRebuild=false
ls -lh release/*.AppImage release/*.deb 2>/dev/null || true
