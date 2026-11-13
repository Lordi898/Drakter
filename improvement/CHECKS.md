# Comprobaciones manuales para la pasada integrada

Salvo la reversión por contenido, ya probada en un repositorio temporal, estas
comprobaciones siguen pendientes. Usa siempre un repositorio temporal, nunca el
real, y `TMPDIR` fuera de `/tmp`.

## Preparación

El repositorio temporal necesita `backend/app/` e
`improvement/evaluations/default.json`, porque los checks se leen del commit base.
Un clon local del proyecto sirve. Sin ese archivo, el resultado es `blocked`.

```bash
export TMPDIR=/var/tmp/drakter-automejora
LAB=$(mktemp -d "$TMPDIR/lab.XXXX")
git clone --quiet --no-hardlinks . "$LAB/repo"
cd backend
```

Abre `.venv/bin/python` y define lo común. Sustituye `LAB` por la ruta real.

```python
import uuid
from pathlib import Path
from app.core.config import ensure_private_dir
from app.services import improvement_lab as lab

LAB = Path("...")
experiments = LAB / "data/improvement/experiments"
ensure_private_dir(experiments)
cfg = lab.LabConfig(repo_path=LAB / "repo", experiments_dir=experiments)

def add_file(path, line="hola", mode="100644"):
    return (
        f"diff --git a/{path} b/{path}\nnew file mode {mode}\n--- /dev/null\n+++ b/{path}\n"
        f"@@ -0,0 +1 @@\n+{line}\n"
    ).encode()
```

## Casos

| # | Caso | Llamada | Esperado |
|---|---|---|---|
| 1 | Agente en ruta protegida | `lab.evaluate_patch(cfg, str(uuid.uuid4()), add_file("backend/app/core/x.py"), "agent")` | `failed`, `checks` vacío, ruta en `protected_paths` |
| 1b | Agente en Python del backend | `add_file("backend/app/services/x.py", "x = 1")` con `"agent"` | `failed`, ruta en `protected_paths` |
| 2 | Persona en ruta protegida | Igual, con `"user"` y `add_file("backend/app/core/x.py", "x = 1")` | `passed`, ruta en `protected_paths`, checks con salida 0 |
| 3 | Enlace simbólico | `add_file("docs/l", "/etc/passwd", "120000")` con `"user"` | `failed`: no aplica o se rechaza por enlace simbólico |
| 4 | Parche válido, checkout intacto | Ver abajo | `passed`, y el repositorio sin cambios |
| 5 | Revertir tras merge | Ver abajo | `AppError` 409 `change_already_merged` |
| 6 | `bwrap` ausente | Ver abajo | `blocked`, con motivo |

Caso 4. Compara antes y después:

```python
import subprocess
def state():
    repo = LAB / "repo"
    git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True).stdout
    return git("rev-parse", "HEAD"), git("status", "--porcelain"), git("for-each-ref")

before = state()
result = lab.evaluate_patch(cfg, str(uuid.uuid4()), add_file("docs/nota.md"), "agent")
assert result.status == "passed", result
assert state() == before
```

Caso 5. Publica y simula el merge sobre la rama actual del repositorio temporal:

```python
pid = str(uuid.uuid4())
patch = add_file("docs/nota.md")
out = lab.evaluate_patch(cfg, pid, patch, "agent")
change = lab.apply_patch(cfg, pid, patch, out.base_commit, "docs: nota")
assert lab.apply_patch(cfg, pid, patch, out.base_commit, "docs: nota") == change

subprocess.run(["git", "-C", str(LAB / "repo"), "merge", "--ff-only", change.branch], check=True)
lab.revert_change(cfg, change)  # AppError 409 change_already_merged
```

Sin el merge, `revert_change` borra la rama y una segunda llamada no hace nada. Con
`git merge --squash` más un commit, también da `change_already_merged`. Si tras ese
squash cambia otra parte de los mismos archivos, sigue siendo `change_already_merged`;
si cambian las mismas líneas dentro de un squash mezclado, da `revert_inconclusive`.
En todos estos casos la rama sigue existiendo.

Caso 6:

```python
lab._find_bwrap = lambda: None
out = lab.evaluate_patch(cfg, str(uuid.uuid4()), add_file("docs/nota.md"), "agent")
assert out.status == "blocked", out
```

## Otras comprobaciones

- `cfg` con `repo_path=None`: `evaluate_patch` da `blocked`; `apply_patch` y
  `revert_change` dan 409 `improvement_repo_unconfigured`.
- `experiments/` queda vacío después de cada llamada.
- `sweep_experiments` borra los experimentos huérfanos y no sigue enlaces simbólicos.
- Un check que se cuelga termina en su `timeout_s`, con `exit_code=None`, y no deja
  procesos vivos.
- Si `kernel.apparmor_restrict_unprivileged_userns=1` impide el espacio de nombres
  de usuario, el resultado es `blocked`, nunca una ejecución sin sandbox.
