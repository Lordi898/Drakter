"""Eval `jobs_routing` (voz v2, WP7/WP9): ¿enruta el modelo a `jobs_*` cuando toca?

Una llamada por caso, sin ejecutar herramientas: se puntúa la PRIMERA decisión del modelo.
- `none`: responde sin `jobs_*` (puede usar otras herramientas).
- `jobs_start|jobs_status|jobs_amend|jobs_cancel`: la primera herramienta `jobs_*` es esa.
- `none_or_jobs_status`: sin `jobs_*` o con `jobs_status`.
- `ask`: no llama a `jobs_*` y pregunta (el texto acaba en «?»).

Prompt de sistema: el SOUL.md que el backend compone en el home de Hermes (identidad + VOICE.md).
El `context` del caso va como prefijo del turno, igual que el `turn_prefix` de Jobs.

Uso (desde la raíz, con el venv del backend; la clave sale de ~/.config/drakter/.env):
    backend/.venv/bin/python agent/evals/jobs_routing.py [--soul RUTA] [--model claude-haiku-5-5]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("jobs_routing.jsonl")
CLOCK = "Fecha y hora actual: lunes 9 de noviembre de 2026, 10:00 (Europe/Madrid)."
JOBS = ("jobs_start", "jobs_status", "jobs_amend", "jobs_cancel")


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    env = Path.home() / ".config" / "drakter" / ".env"
    if not key and env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("falta ANTHROPIC_API_KEY")
    return key


def tools() -> list[dict]:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.tools.jobs import TOOLS as JOB_SPECS  # noqa: PLC0415

    catalog = {t["name"]: t for t in json.loads((ROOT / "contracts/tools/catalog.json").read_text())}
    schemas = json.loads((ROOT / "agent/evals/schemas/tool_inputs.json").read_text())["tools"]
    out = [{"name": n, "description": catalog[n]["description"], "input_schema": s}
           for n, s in sorted(schemas.items()) if n in catalog]
    for spec in JOB_SPECS:
        out.append({"name": spec.name, "description": spec.description,
                    "input_schema": spec.args_model.model_json_schema()})
    return out


def fake_result(name: str, case: dict) -> dict:
    """Resultado plausible: `jobs_status` devuelve los trabajos del contexto con UUID."""
    if name != "jobs_status":
        return {"ok": True, "items": []}
    jobs = []
    for i, part in enumerate((case.get("context") or "").split(";")):
        if "'" in part:
            title = part.split("'")[1]
            jobs.append({"job_id": f"00000000-0000-4000-8000-00000000000{i + 1}", "title": title,
                         "state": "running", "elapsed_s": 60, "tool_calls": 3, "pending_actions": 0})
    return {"jobs": jobs}


def run_case(client: httpx.Client, body: dict, case: dict) -> tuple[list[dict], list[str]]:
    """Hasta 4 rondas: `jobs_status` y las herramientas de consulta reciben un resultado falso;
    se para en la primera `jobs_*` que no sea `jobs_status` o en la respuesta final."""
    trail: list[str] = []
    messages = body["messages"]
    for _ in range(4):
        resp = client.post("/v1/messages", json={**body, "messages": messages})
        resp.raise_for_status()
        content = resp.json()["content"]
        uses = [b for b in content if b.get("type") == "tool_use"]
        trail += [b["name"] for b in uses]
        if not uses or any(b["name"] in JOBS and b["name"] != "jobs_status" for b in uses):
            return content, trail
        messages = [*messages, {"role": "assistant", "content": content},
                    {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": b["id"],
                         "content": json.dumps(fake_result(b["name"], case), ensure_ascii=False)}
                        for b in uses]}]
    return content, trail


def verdict(expected: str, content: list[dict], trail: list[str]) -> tuple[bool, str]:
    used = trail
    actions = [n for n in used if n in JOBS and n != "jobs_status"]
    first_job = actions[0] if actions else ("jobs_status" if "jobs_status" in used else None)
    text = " ".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
    got = first_job or ("ask" if text.endswith("?") else "none")
    if expected == "none":
        return first_job is None, got
    if expected == "none_or_jobs_status":
        return first_job in (None, "jobs_status"), got
    if expected == "ask":  # puede mirar el estado antes de preguntar
        return not actions and text.endswith("?"), ("ask" if text.endswith("?") and not actions else got)
    return first_job == expected, got


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--soul", type=Path,
                        default=Path(os.environ.get("DRAKTER_DATA_DIR", Path.home() / ".local/share/drakter"))
                        / "hermes" / "SOUL.md")
    parser.add_argument("--model", default="claude-haiku-5-5")
    args = parser.parse_args()
    system = f"{args.soul.read_text(encoding='utf-8').strip()}\n\n{CLOCK}"
    defs = tools()
    client = httpx.Client(base_url="https://api.anthropic.com", timeout=90,
                          headers={"x-api-key": api_key(), "anthropic-version": "2023-06-01"})
    passed = 0
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    for case in cases:
        prefix = "[canal: voz]\n" + (f"[{case['context']}]\n" if case.get("context") else "")
        body = {"model": args.model, "max_tokens": 1024,
                "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                "tools": defs, "messages": [{"role": "user", "content": prefix + case["user"]}]}
        content, trail = run_case(client, body, case)
        ok, got = verdict(case["expected"], content, trail)
        passed += ok
        print(f"{'ok   ' if ok else 'FALLA'} {case['id']:8} esperado={case['expected']:20} "
              f"obtenido={got:12} herramientas={','.join(trail) or '-'}")
    print(f"\n{passed}/{len(cases)} casos superados")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
