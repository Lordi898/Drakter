#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
DESKTOP_DIR="$(cd "$HERE/../.." && pwd)"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
TARGET="$TARGET_DIR/drakter.desktop"

ICON="drakter"
for candidate in "$DESKTOP_DIR/build/icon.png" "$DESKTOP_DIR/resources/icon.png" "$DESKTOP_DIR/public/icon.png"; do
  if [[ -f "$candidate" ]]; then ICON="$candidate"; break
fi
done

mkdir -p "$TARGET_DIR"
sed -e "s|@EXEC@|$HERE/drakter|" -e "s|@ICON@|$ICON|" "$HERE/drakter.desktop.in" > "$TARGET"
chmod 644 "$TARGET"
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$TARGET_DIR" || true
fi
echo "Instalado: $TARGET"
