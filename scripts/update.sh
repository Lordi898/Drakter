#!/usr/bin/env bash
# Actualiza Drakter desde GitHub (repositorio privado, un único usuario).
#
#   scripts/update.sh [--package] [--no-restart]
#
#   --package      además reconstruye el AppImage y lo reinstala (scripts/package.sh +
#                  scripts/install-appimage.sh). Úsalo si abres Drakter con drakter-app.
#   --no-restart   no para ni vuelve a arrancar la app de scripts/drakter-local.sh.
#
# Pasos: git pull --ff-only → dependencias que hayan cambiado (uv sync --locked, npm ci,
# install-voice.sh, install-hermes.sh) → npm run build → copia de la base → migraciones →
# reinicio. Usa las credenciales de git que ya tengas (SSH o gh); la app no guarda tokens.
set -euo pipefail
unset ELECTRON_RUN_AS_NODE ELECTRON_NO_ATTACH_CONSOLE

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package=0 restart=1
for arg in "$@"; do
  case "$arg" in
    --package) package=1 ;;
    --no-restart) restart=0 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $arg" >&2; exit 2 ;;
  esac
done

step() { echo "── $*"; }
die() { echo "ERROR: $1" >&2; [ -n "${2:-}" ] && echo "  Arreglo: $2" >&2; exit 1; }
cd "$repo"
export PATH="$HOME/.local/bin:$PATH"

# ── 1. Código ────────────────────────────────────────────────────────────────
[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || die "hay cambios sin guardar en $repo" "git stash push -m antes-de-update, o haz commit"
branch="$(git symbolic-ref --short HEAD 2>/dev/null)" || die "HEAD no está en una rama" "git checkout main"
old="$(git rev-parse HEAD)"
step "git pull --ff-only ($branch)"
git pull --ff-only || die "no se pudo actualizar sin fusionar" "revisa 'git status' y 'git log origin/$branch'"
new="$(git rev-parse HEAD)"
if [ "$old" = "$new" ]; then
  echo "Ya estabas en la última versión ($(git log -1 --format='%h %s'))."
else
  git log --oneline "$old..$new" | head -n 20
fi
changed() { [ "$old" != "$new" ] && ! git diff --quiet "$old" "$new" -- "$@"; }

# ── 2. Dependencias que hayan cambiado (o que falten) ──────────────────────────
if changed backend/uv.lock backend/pyproject.toml contracts/python || [ ! -x backend/.venv/bin/python ]; then
  step "backend: uv sync --locked"
  (cd backend && uv sync --locked)
fi
if changed desktop/package-lock.json || [ ! -d desktop/node_modules ]; then
  step "escritorio: npm ci"
  (cd desktop && npm ci --no-audit --no-fund)
fi
if changed voice/requirements.lock voice/pyproject.toml contracts/python scripts/install-voice.sh; then
  step "voz: scripts/install-voice.sh"
  scripts/install-voice.sh || echo "AVISO: install-voice.sh falló; Drakter funciona sin voz hasta arreglarlo."
fi
if changed scripts/install-hermes.sh; then
  step "Hermes: scripts/install-hermes.sh"
  scripts/install-hermes.sh
fi
if changed desktop || [ ! -f desktop/out/main/index.js ]; then
  step "escritorio: npm run build"
  (cd desktop && npm run build >/dev/null)
fi

# ── 3. Parar la app de drakter-local.sh para poder migrar ──────────────────────
was_running=0
if [ "$restart" = 1 ] && scripts/drakter-local.sh status | grep -q "app: en marcha"; then
  step "parando Drakter (drakter-local.sh)"
  scripts/drakter-local.sh stop >/dev/null
  was_running=1
fi

# ── 4. Copia y migraciones ─────────────────────────────────────────────────────
db() { (cd backend && .venv/bin/python -m app.database.cli "$@"); }
step "copia de la base de datos"
db backup || die "la copia falló: no se migra" "revisa el espacio en disco y repite"
step "migraciones"
if ! out="$(db migrate 2>&1)"; then
  case "$out" in
    *"en uso por otra instancia"*)
      echo "Drakter está abierto: las migraciones se aplicarán (con su propia copia) al volver a abrirlo." ;;
    *) echo "$out" >&2; die "la migración falló" "restaura la copia de arriba: cd backend && .venv/bin/python -m app.database.cli restore <archivo>" ;;
  esac
else
  echo "$out"
fi

# ── 5. Paquete (opcional) y reinicio ───────────────────────────────────────────
if [ "$package" = 1 ]; then
  step "AppImage: scripts/package.sh + scripts/install-appimage.sh"
  scripts/package.sh appimage
  scripts/install-appimage.sh
fi
if [ "$was_running" = 1 ]; then
  step "arrancando Drakter (drakter-local.sh start ${DRAKTER_PROVIDER:-anthropic})"
  scripts/drakter-local.sh start "${DRAKTER_PROVIDER:-anthropic}"
elif [ "$old" != "$new" ]; then
  echo "Si Drakter está abierto, ciérralo y vuelve a abrirlo para usar la versión nueva."
fi
echo "Actualizado a $(git log -1 --format='%h %s')."
