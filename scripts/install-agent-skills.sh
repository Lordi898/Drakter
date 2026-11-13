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
# Uso: scripts/install-agent-skills.sh [--force]
#   --force  reemplaza las carpetas que ya existan.
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

FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/.claude/skills"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

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
echo "Listo: ${#SKILLS[@]} skills en .claude/skills/"
