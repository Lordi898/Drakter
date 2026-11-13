"""Generate agent/evals/schemas/tool_inputs.json from the real Drakter tool modules.

Each worktree is imported in its own child interpreter (every worktree ships its own
``app`` package), reading it only. The schema is ``spec.args_model.model_json_schema()``,
the same call ``app/tools/mcp_bridge.py::_mcp_tool`` uses for the MCP ``inputSchema``.

Usage:
  PYTHONDONTWRITEBYTECODE=1 TMPDIR=/var/tmp/drakter-evals /var/tmp/drakter-5-verif/ov-a/venv/bin/python \
      extract_schemas.py [--root WORKTREES_DIR] [--catalog-ref drakter/contratos] [--out FILE]
Interpreter needs pydantic, platformdirs, pydantic_settings, mcp (ov-a venv has them; hermes-b lacks platformdirs).
Env: DRAKTER_WORKTREES (default ~/.ao/data/worktrees/drakter).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

# worktree dir name -> domains it owns (documentation only; every app/tools/*.py with TOOLS is read)
WORKTREES = ["drakter-13", "drakter-14", "drakter-15", "drakter-16", "drakter-18", "drakter-27"]
TMP = "/var/tmp/drakter-evals"
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "schemas" / "tool_inputs.json"

CHILD = r"""
import importlib, importlib.abc, importlib.machinery, json, sys, types
from pathlib import Path
wt, spec_wt = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(wt / "backend"), str(wt / "contracts" / "python")]
sys.path.append(str(spec_wt / "contracts" / "python"))
stubbed = set()
ALLOW = set()  # third-party names that may be stubbed (opt-in via --stub)


class _Dummy:
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Dummy()
    def __getattr__(self, n): return _Dummy()


class _Stub(types.ModuleType):
    __path__ = []
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        return type(n, (_Dummy,), {})


class _Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    # Only for third-party packages missing from this interpreter (never app/drakter_contracts).
    def find_spec(self, name, path=None, target=None):
        top = name.split(".")[0]
        if top not in ALLOW:
            return None
        stubbed.add(name.split(".")[0])
        return importlib.machinery.ModuleSpec(name, self, is_package=True)
    def create_module(self, spec): return _Stub(spec.name)
    def exec_module(self, module): pass


if len(sys.argv) > 3 and sys.argv[3]:
    ALLOW.update(sys.argv[3].split(","))
    sys.meta_path.append(_Finder())
out, errors = {}, {}
tools_dir = wt / "backend" / "app" / "tools"
if not (tools_dir / "spec.py").exists():  # branch predates the shared ToolSpec: borrow it, read-only
    import app.tools as pkg
    pkg.__path__.append(str(spec_wt / "backend" / "app" / "tools"))
try:  # memory/search/storage import it from app.tools.spec; it lives in app.tools.envelope (in-memory shim)
    import app.tools.spec as _spec
    if not hasattr(_spec, "untrusted_envelope"):
        from app.tools.envelope import untrusted_envelope as _ue
        _spec.untrusted_envelope = _ue
        stubbed.add("shim:spec.untrusted_envelope")
except Exception as exc:
    errors["_spec_shim"] = repr(exc)
for f in sorted(tools_dir.glob("*.py")):
    if f.stem.startswith("_"):
        continue
    try:
        mod = importlib.import_module("app.tools." + f.stem)
    except Exception as exc:  # reported, never hidden
        errors[f.stem] = repr(exc)
        continue
    for spec in getattr(mod, "TOOLS", ()) or ():
        m = spec.args_model
        out[spec.name] = {"module": f.stem, "args_model": m.__name__, "schema": m.model_json_schema()}
print(json.dumps({"tools": out, "errors": errors, "stubbed": sorted(stubbed)}))
"""


def git(wt: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(wt), *args], check=True, capture_output=True, text=True).stdout.strip()


def run_child(wt: Path, spec_wt: Path, stub: list[str]) -> dict:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "TMPDIR": TMP,
        "HOME": TMP,
    }
    r = subprocess.run([sys.executable, "-B", "-I", "-c", CHILD, str(wt), str(spec_wt), ",".join(stub)], env=env, cwd=TMP,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{wt.name}: child failed\n{r.stderr[-2000:]}")
    return json.loads(r.stdout.splitlines()[-1])


def clean(node, defs, seen=()):
    """Inline $ref, drop $defs and noise titles (never a property literally named 'title')."""
    if isinstance(node, list):
        return [clean(n, defs, seen) for n in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        if name in seen:
            raise SystemExit(f"recursive schema {name}: cannot inline")
        extra = {k: v for k, v in node.items() if k != "$ref"}
        return {**clean(copy.deepcopy(defs[name]), defs, seen + (name,)), **clean(extra, defs, seen)}
    out = {}
    for k, v in node.items():
        if k in ("$defs", "title"):
            continue
        if k in ("properties", "patternProperties"):
            out[k] = {pk: clean(pv, defs, seen) for pk, pv in v.items()}
        else:
            out[k] = clean(v, defs, seen)
    return out


def finalize(schema: dict) -> dict:
    s = clean(schema, schema.get("$defs", {}))
    s.setdefault("type", "object")
    s.setdefault("properties", {})
    s.setdefault("required", [])
    s.setdefault("additionalProperties", False)
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.environ.get("DRAKTER_WORKTREES", os.path.expanduser("~/.ao/data/worktrees/drakter")))
    ap.add_argument("--catalog-ref", default="drakter/contratos")
    ap.add_argument("--stub", action="append", default=[], help="third-party module to stub if missing (repeatable)")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    root = Path(a.root)
    Path(TMP).mkdir(parents=True, exist_ok=True)

    catalog_repo = root / "drakter-30"
    catalog = json.loads(git(catalog_repo, "show", f"{a.catalog_ref}:contracts/tools/catalog.json"))
    catalog = catalog if isinstance(catalog, list) else catalog.get("tools", catalog)
    by_name = {t["name"]: t for t in catalog}

    generated_from = {a.catalog_ref: git(catalog_repo, "rev-parse", "--short", a.catalog_ref)}
    tools, notes = {}, []
    for name in WORKTREES:
        wt = root / name
        dirty = "+dirty" if git(wt, "status", "--porcelain", "--untracked-files=no") else ""
        generated_from[git(wt, "rev-parse", "--abbrev-ref", "HEAD")] = git(wt, "rev-parse", "--short", "HEAD") + dirty
        res = run_child(wt, root / "drakter-16", a.stub)
        if res["stubbed"]:
            notes.append(f"{name}: third-party modules stubbed (missing in interpreter): {res['stubbed']}")
        for mod, err in res["errors"].items():
            notes.append(f"{name}: module {mod} not importable: {err}")
        for tname, d in res["tools"].items():
            if tname not in by_name:
                notes.append(f"{tname} ({name}/{d['module']}) is not in the catalog: skipped")
                continue
            if tname in tools:
                notes.append(f"{tname} defined twice; keeping first")
                continue
            exp = by_name[tname].get("args_model")
            if exp and exp.rsplit(".", 1)[-1] != d["args_model"]:
                notes.append(f"{tname}: catalog args_model={exp} but code={d['args_model']}")
            tools[tname] = finalize(d["schema"])

    missing = sorted(set(by_name) - set(tools))
    result = {"generated_from": generated_from, "tools": dict(sorted(tools.items()))}
    Path(a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(tools)}/{len(by_name)} tools -> {a.out}")
    print("missing:", ", ".join(missing))
    for n in notes:
        print("NOTE:", n)


if __name__ == "__main__":
    main()
