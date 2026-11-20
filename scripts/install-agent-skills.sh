#!/usr/bin/env bash
# Instala en .claude/skills/ las skills de desarrollo de terceros que no se
# versionan en este repositorio porque su origen no publica licencia.
#
# Origen: https://github.com/LLMTooling/agent-skills (sin licencia declarada).
# Commit fijado: f096e2bcc375e76b57ca27247040849fa01eaf56 (2026-06-29).
#
# Cada skill es un zip `.skill`; se extrae en .claude/skills/<nombre>/ y su
# SKILL.md se normaliza a LF (venían con CRLF). Es lo mismo que se hizo en la
# instalación original (docs/DECISIONS.md, 2026-11-04).
#
# Además instala las skills del avatar (MIT/Apache-2.0, ver AVATAR_SKILLS).
# Esas sí se versionan en el repositorio; el script sirve para llevarlas a otro
# checkout sin esperar a la fusión. Cada una conserva el LICENSE de su origen.
#
# Uso: scripts/install-agent-skills.sh [--force] [--dest DIR] [--only-avatar]
#   --force        reemplaza las carpetas que ya existan.
#   --dest DIR     raíz de otro checkout (por defecto, la de este script).
#   --only-avatar  instala solo las skills del avatar.
#
# Requisitos: git y python3. Solo accede a github.com.
set -euo pipefail

REPO_URL="https://github.com/LLMTooling/agent-skills.git"
COMMIT="f096e2bcc375e76b57ca27247040849fa01eaf56"

# nombre=ruta dentro del repo de origen
SKILLS=(
  "electron=skills/electron/electron.skill"
  "electron-builder=skills/electron/electron-builder.skill"
  "electron-vite=skills/electron/electron-vite.skill"
  "vite=skills/build-tools/vite.skill"
  "vitest=skills/testing/vitest.skill"
  "playwright-cli=skills/testing/playwright-cli.skill"
  "typescript-best-practices=skills/typescript-dev/typescript-best-practices.skill"
  "react-19=skills/react-ecosystem/react-19.skill"
  "shadcn=skills/react-ecosystem/shadcn.skill"
  "radix-ui=skills/react-ecosystem/radix-ui.skill"
  "lucide-react=skills/react-ecosystem/lucide-react.skill"
  "react-arborist=skills/react-ecosystem/react-arborist.skill"
  "tailwind-css=skills/styling/tailwind-css.skill"
  "motion=skills/animation-graphics/motion.skill"
  "fastapi=skills/backend-frameworks/fastapi.skill"
  "pydantic-dev=skills/python-dev/pydantic-dev.skill"
  "python-best-practices=skills/python-dev/python-best-practices.skill"
  "fastmcp-sdk=skills/mcp/fastmcp-sdk.skill"
  "pdf-to-markdown=skills/utilities/pdf-to-markdown.skill"
)

# Skills del avatar: nombre|repo|commit|ruta en el repo|titular MIT si el
# origen no trae LICENSE (solo emalorenzo, que declara MIT en package.json).
AVATAR_SKILLS=(
  "character-design-continuity|calesthio/generative-media-skills|8c85352d5d75d4dcbe58480bd138e37b9742bab1|skills/production/creative-direction/character-design-continuity|"
  "2d-character-rig-animation|calesthio/generative-media-skills|8c85352d5d75d4dcbe58480bd138e37b9742bab1|skills/production/creative-direction/2d-character-rig-animation|"
  "animation-principles|iart-ai/motion-design-skills|b85e50c4cef5ff17aa2187a10d49d2dae9226c74|skills/animation-principles|"
  "svg-animation|iart-ai/web-animation-skills|ed3a045192679b24d32090ee7a983871311ababd|skills/svg-animation|"
  "rive-interactive|freshtechbro/claudedesignskills|1da73febff0c3e1dfefc07f8a5ef8f7d1dfdb6cd|plugins/individual/rive-interactive/skills/rive-interactive|"
  "three-best-practices|emalorenzo/three-agent-skills|f950f95ae3b13581546e6d6d8b2f88a08eb3e577|skills/three-best-practices|emalorenzo"
  "r3f-best-practices|emalorenzo/three-agent-skills|f950f95ae3b13581546e6d6d8b2f88a08eb3e577|skills/r3f-best-practices|emalorenzo"
  "threejs-shaders|CloudAI-X/threejs-skills|0e181866f095b5f06d005133876e926515390d95|skills/threejs-shaders|"
  "threejs-animation|CloudAI-X/threejs-skills|0e181866f095b5f06d005133876e926515390d95|skills/threejs-animation|"
  "gsap-core|greensock/gsap-skills|aed9cfd3277740755f6bfc1155c7aa645403b760|skills/gsap-core|"
  "gsap-timeline|greensock/gsap-skills|aed9cfd3277740755f6bfc1155c7aa645403b760|skills/gsap-timeline|"
  "gsap-plugins|greensock/gsap-skills|aed9cfd3277740755f6bfc1155c7aa645403b760|skills/gsap-plugins|"
  "gsap-react|greensock/gsap-skills|aed9cfd3277740755f6bfc1155c7aa645403b760|skills/gsap-react|"
  "gsap-performance|greensock/gsap-skills|aed9cfd3277740755f6bfc1155c7aa645403b760|skills/gsap-performance|"
  "canvas-design|anthropics/skills|e4bb5d960d87126ff3b3a8af1a104b7db67560ba|skills/canvas-design|"
  "algorithmic-art|anthropics/skills|e4bb5d960d87126ff3b3a8af1a104b7db67560ba|skills/algorithmic-art|"
)

FORCE=0; ONLY_AVATAR=0
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ;;
    --only-avatar) ONLY_AVATAR=1 ;;
    --dest) ROOT="$(cd "$2" && pwd)"; shift ;;
    *) echo "opción desconocida: $1" >&2; exit 2 ;;
  esac
  shift
done
DEST="$ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() {  # fetch <dir> <url> <commit>
  [[ -d "$1" ]] && return 0
  git init -q "$1"
  git -C "$1" fetch -q --depth 1 "$2" "$3"
  git -C "$1" -c advice.detachedHead=false checkout -q --detach "$3"
}

write_mit() {  # write_mit <archivo> <titular> <repo>
  cat >"$1" <<EOF
MIT License

Copyright (c) $2
(Licencia declarada como "MIT" en package.json y README de
https://github.com/$3; el repositorio no incluye el texto, que se reproduce aquí.)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
}

install_avatar() {
  mkdir -p "$DEST"
  for entry in "${AVATAR_SKILLS[@]}"; do
    IFS='|' read -r name repo commit path holder <<<"$entry"
    target="$DEST/$name"
    if [[ -e "$target" && $FORCE -eq 0 ]]; then
      echo "  = $name (ya existe; usa --force para reemplazarla)"
      continue
    fi
    src="$TMP/${repo//\//_}-${commit:0:8}"
    fetch "$src" "https://github.com/$repo.git" "$commit"
    rm -rf "$target"
    cp -r "$src/$path" "$target"
    if ! ls "$target" | grep -qiE '^licen[cs]e'; then
      if [[ -f "$src/LICENSE" ]]; then
        cp "$src/LICENSE" "$target/LICENSE"
      elif [[ -n "$holder" ]]; then
        write_mit "$target/LICENSE" "$holder" "$repo"
      else
        echo "sin LICENSE para $name ($repo)" >&2; exit 1
      fi
    fi
    echo "  + $name ($repo@${commit:0:8})"
  done
}

if [[ $ONLY_AVATAR -eq 1 ]]; then
  install_avatar
  echo "Listo: ${#AVATAR_SKILLS[@]} skills del avatar en $DEST"
  exit 0
fi

echo "Descargando $REPO_URL@${COMMIT:0:8}..."
git init -q "$TMP/src"
git -C "$TMP/src" fetch -q --depth 1 "$REPO_URL" "$COMMIT"
git -C "$TMP/src" -c advice.detachedHead=false checkout -q --detach "$COMMIT"

mkdir -p "$DEST"
for entry in "${SKILLS[@]}"; do
  name="${entry%%=*}"
  src="$TMP/src/${entry#*=}"
  target="$DEST/$name"
  if [[ -e "$target" && $FORCE -eq 0 ]]; then
    echo "  = $name (ya existe; usa --force para reemplazarla)"
    continue
  fi
  rm -rf "$target"
  python3 -I - "$src" "$target" <<'PY'
import pathlib, sys, zipfile
src, target = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
with zipfile.ZipFile(src) as z:
    for member in z.infolist():
        out = (target / member.filename).resolve()
        if target not in out.parents and out != target:
            sys.exit(f"ruta fuera de destino en {src}: {member.filename}")
    z.extractall(target)
skill = target / "SKILL.md"
if skill.exists():
    skill.write_bytes(skill.read_bytes().replace(b"\r\n", b"\n"))
PY
  echo "  + $name"
done
echo "Listo: ${#SKILLS[@]} skills en $DEST"
install_avatar
echo "Listo: ${#AVATAR_SKILLS[@]} skills del avatar en $DEST"
