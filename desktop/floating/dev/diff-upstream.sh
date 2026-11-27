#!/bin/sh
# Drakter (solo desarrollo): compara desktop/floating/roamies y fonts con Roamies 8f0adaa y falla si alguna línea
# cambiada no lleva la marca «// Drakter:» (lo exige la AGPL y el criterio de hecho de D1).
# Uso: desktop/floating/dev/diff-upstream.sh <ruta a un checkout de KenKaiii/Roamies en 8f0adaa>
# SPDX-License-Identifier: AGPL-3.0-only
set -eu
UP=${1:?Uso: diff-upstream.sh <checkout de Roamies>}
HERE=$(cd "$(dirname "$0")/.." && pwd)
bad=0
for f in "$HERE"/roamies/*.js; do
  b=$(basename "$f")
  n=$(diff "$UP/showcase/roamies/$b" "$f" | grep '^>' | grep -vc '// Drakter:' || true)
  c=$(diff "$UP/showcase/roamies/$b" "$f" | grep -c '^>' || true)
  if [ "$n" != 0 ]; then echo "SIN MARCA  $b: $n líneas"; bad=1; fi
  if [ "$c" = 0 ]; then echo "idéntico   $b"; else echo "parcheado  $b: $c líneas, todas marcadas"; fi
done
for f in "$HERE"/fonts/*; do
  cmp -s "$f" "$UP/showcase/onboarding/fonts/$(basename "$f")" || { echo "DISTINTO   fonts/$(basename "$f")"; bad=1; }
done
exit $bad
