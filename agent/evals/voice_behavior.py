"""Eval `voice_behavior`: comportamiento de Drakter en turnos de voz (conversación real del usuario).

Casos en `voice_behavior.jsonl`. Cada turno lleva `[canal: voz]`, como el backend. El prompt es
el SOUL.md que compondría el backend desde ESTE árbol (`render_soul`), así se mide antes y después
de tocar `agent/identity/`. Las herramientas reciben un resultado falso genérico (como mucho 3 rondas).

Reglas (búsquedas de texto, no juzgan el tono; lee las respuestas):
- `min_words` / `max_sentences`: longitud de la respuesta final.
- `must_match` / `must_not_match`: expresiones regulares sobre la respuesta final.
- `no_tools`: no llama a ninguna herramienta.

Uso (desde la raíz, con el venv del backend; la clave sale de ~/.config/drakter/.env):
    <backend-venv>/bin/python agent/evals/voice_behavior.py [--case ID] [--model claude-haiku-5-5]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from jobs_routing import CLOCK, ROOT, api_key, tools  # noqa: E402

CASES = Path(__file__).with_name("voice_behavior.jsonl")
VOICE = "[canal: voz]\n"
FAKE = {"status": "ok", "data": {"id": "00000000-0000-4000-8000-000000000001", "items": [], "total": 0}}


def soul() -> str:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.integrations.hermes.home import render_soul  # noqa: PLC0415

    return f"{render_soul(ROOT).strip()}\n\n{CLOCK}"


def run_case(client: httpx.Client, body: dict) -> tuple[str, list[str]]:
    trail: list[str] = []
    messages = body["messages"]
    for _ in range(3):
        resp = client.post("/v1/messages", json={**body, "messages": messages})
        resp.raise_for_status()
        content = resp.json()["content"]
        uses = [b for b in content if b.get("type") == "tool_use"]
        trail += [b["name"] for b in uses]
        if not uses:
            break
        messages = [*messages, {"role": "assistant", "content": content},
                    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": b["id"],
                                                  "content": json.dumps(FAKE)} for b in uses]}]
    text = " ".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
    return text, trail


def failures(case: dict, text: str, trail: list[str]) -> list[str]:
    out = []
    words = len(text.split())
    sentences = len([s for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()])
    if words < case.get("min_words", 0):
        out.append(f"corta ({words} palabras)")
    if sentences > case.get("max_sentences", 99):
        out.append(f"larga ({sentences} frases)")
    if case.get("no_tools") and trail:
        out.append(f"herramientas: {','.join(trail)}")
    out += [f"falta /{p}/" for p in case.get("must_match", []) if not re.search(p, text)]
    out += [f"prohibido /{p}/" for p in case.get("must_not_match", []) if re.search(p, text)]
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-haiku-5-5")
    parser.add_argument("--case")
    args = parser.parse_args()
    system = [{"type": "text", "text": soul(), "cache_control": {"type": "ephemeral"}}]
    defs = tools()
    client = httpx.Client(base_url="https://api.anthropic.com", timeout=90,
                          headers={"x-api-key": api_key(), "anthropic-version": "2023-06-01"})
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [c for c in cases if not args.case or c["id"] == args.case]
    passed = 0
    for case in cases:
        messages = [*case.get("history", []), {"role": "user", "content": VOICE + case["user"]}]
        body = {"model": args.model, "max_tokens": 1024, "system": system, "tools": defs, "messages": messages}
        text, trail = run_case(client, body)
        bad = failures(case, text, trail)
        passed += not bad
        print(f"{'ok   ' if not bad else 'FALLA'} {case['id']:24} {'; '.join(bad)}\n      «{text}»")
    print(f"\n{passed}/{len(cases)} casos superados")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
