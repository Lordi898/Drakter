#!/usr/bin/env bash
# Xvfb sin sudo: descarga el .deb de apt y lo extrae en ~/.local/share/drakter/xvfb (no instala nada en el sistema).
# El arnés lo encuentra solo con --headless. Alternativas: Xvfb en el PATH o DRAKTER_E2E_XVFB=/ruta/Xvfb.
set -euo pipefail
dest="$HOME/.local/share/drakter/xvfb"
mkdir -p "$dest"
cd "$dest"
apt-get download xvfb
dpkg -x xvfb_*.deb root
rm -f xvfb_*.deb
ldd root/usr/bin/Xvfb | grep "not found" && { echo "faltan librerías para Xvfb" >&2; exit 1; } || true
echo "Xvfb listo: $dest/root/usr/bin/Xvfb"
