"""Cruza `docs/IMPLEMENTATION_STATUS.md` con los resultados y escribe el informe."""
from __future__ import annotations

import json
import re
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .model import Result, Status

SECTION = re.compile(r"^## Checklist (\d+)\.\s*(.+?)\s*$")
BOX = re.compile(r"^\s*- \[([ xX])\] (.+?)\s*$")
STUB_BANNER = ("El LLM de esta pasada es el stub de desarrollo (`tools/dev-llm-stub`), con respuestas "
               "guionizadas. **No prueba Claude Haiku 5.5 ni ningún modelo real.** Un PASA marcado "
               "como «con stub» solo prueba el cableado.")
SANDBOX_NOTE = ("Electron se ejecuta con `--no-sandbox` solo en este arnés (`chrome-sandbox` no es "
                "SUID y no hay sudo): el sandbox real del sistema queda sin probar aquí.")


@dataclass
class Item:
    checklist: int
    section: str
    text: str
    marked: bool  # casilla marcada en el documento
    status: Status
    detail: str
    with_stub: bool


def parse_checklists(path: Path) -> list[tuple[int, str, str, bool]]:
    items, number, title = [], None, ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if heading := SECTION.match(line):
            number, title = int(heading.group(1)), heading.group(2)
        elif number is not None and (box := BOX.match(line)):
            items.append((number, title, box.group(2), box.group(1) != " "))
    return items


def load_coverage(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def validate_coverage(coverage: dict[str, Any], checklists: list, known: set[str]) -> list[str]:
    """Problemas de mapeo: textos que ya no existen, ids desconocidos o entradas repetidas."""
    problems, seen = [], set()
    existing = {(number, text) for number, _, text, _ in checklists}
    for entry in coverage.get("item", []):
        key = (entry["checklist"], entry["text"])
        if key in seen:
            problems.append(f"entrada repetida: Checklist {key[0]}: {key[1]}")
        seen.add(key)
        if key not in existing:
            problems.append(f"casilla inexistente: Checklist {key[0]}: {key[1]}")
        for name in entry.get("checks", []):
            if name not in known:
                problems.append(f"comprobación desconocida {name!r} en Checklist {key[0]}: {key[1]}")
        if entry.get("blocked") and entry["blocked"] not in coverage.get("blocked", {}):
            problems.append(f"bloqueo desconocido {entry['blocked']!r} en Checklist {key[0]}: {key[1]}")
    return problems


def judge(checklists: list, coverage: dict[str, Any], results: dict[str, Result]) -> list[Item]:
    entries = {(e["checklist"], e["text"]): e for e in coverage.get("item", [])}
    sections = {s["checklist"]: s["reason"] for s in coverage.get("section", [])}
    blocked = coverage.get("blocked", {})
    judged = []
    for number, title, text, marked in checklists:
        entry = entries.get((number, text), {})
        names = entry.get("checks", [])
        found = [results[name] for name in names if name in results]
        status, detail = Status.NO_COMPROBADO, sections.get(number, "sin comprobación automática")
        if entry.get("reason"):
            detail = entry["reason"]
        if entry.get("blocked"):
            detail = blocked[entry["blocked"]]
        failures = [r for r in found if r.status is Status.FALLA]
        if failures:
            # Una comprobación fallida manda aunque la casilla esté bloqueada por otra causa.
            status = Status.FALLA
            detail = "; ".join(f"{r.id}: {r.evidence}" for r in failures)
        elif entry.get("blocked"):
            pass  # Sin el requisito real no puede salir PASA, aunque lo mapeado acierte.
        elif names and len(found) == len(names):
            pending = [r for r in found if r.status is not Status.PASA]
            if pending:
                detail = "; ".join(f"{r.id}: {r.evidence}" for r in pending)
            else:
                status = Status.PASA
                detail = ", ".join(names)
        with_stub = status is Status.PASA and any(r.uses_stub for r in found)
        judged.append(Item(number, title, text, marked, status, detail, with_stub))
    return judged


def _cell(text: str, limit: int = 220) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def _counts(values) -> dict[str, int]:
    return {s.value: sum(1 for v in values if v.status is s) for s in Status}


def write_report(out: Path, meta: dict[str, Any], results: list[Result], items: list[Item],
                 warnings: list[str]) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    totals, check_totals = _counts(items), _counts(results)
    contradictions = [i for i in items if i.marked and i.status is not Status.PASA]
    lines = ["# Informe de verificación integrada de Drakter", "",
             f"> ⚠️ {STUB_BANNER}", ">", f"> ⚠️ {SANDBOX_NOTE}", "",
             "## Resumen", "",
             f"- Fecha: {meta['date']}", f"- Pasada: **{meta['scope']}**",
             f"- Casillas: PASA {totals['PASA']} · FALLA {totals['FALLA']} · "
             f"NO COMPROBADO {totals['NO COMPROBADO']} (total {len(items)})",
             f"- Comprobaciones: PASA {check_totals['PASA']} · FALLA {check_totals['FALLA']} · "
             f"NO COMPROBADO {check_totals['NO COMPROBADO']} (total {len(results)})", "",
             "## Componentes", "", "| Componente | Estado | Origen |", "|---|---|---|"]
    for name, data in meta["components"].items():
        lines.append(f"| {name} | {_cell(data['state'])} | `{_cell(data['source'])}` |")
    if warnings:
        lines += ["", "## Avisos del arnés", ""] + [f"- {w}" for w in warnings]
    if contradictions:
        lines += ["", "## Marcadas `[x]` en el documento sin PASA aquí", ""]
        lines += [f"- {i.status.value} · Checklist {i.checklist}: {i.text}" for i in contradictions]
    lines += ["", "## Comprobaciones", "", "| Resultado | Comprobación | Evidencia |", "|---|---|---|"]
    for r in results:
        tag = f"{r.status.value} (con stub)" if r.status is Status.PASA and r.uses_stub else r.status.value
        lines.append(f"| {tag} | `{r.id}`: {_cell(r.title, 90)} | {_cell(r.evidence)} |")
    lines += ["", "## Casillas de `docs/IMPLEMENTATION_STATUS.md`"]
    current = None
    for item in items:
        if item.checklist != current:
            current = item.checklist
            group = [i for i in items if i.checklist == current]
            count = _counts(group)
            lines += ["", f"### Checklist {current}. {item.section}", "",
                      f"PASA {count['PASA']} · FALLA {count['FALLA']} · "
                      f"NO COMPROBADO {count['NO COMPROBADO']}", "",
                      "| Resultado | Casilla | Detalle |", "|---|---|---|"]
        tag = f"{item.status.value} (con stub)" if item.with_stub else item.status.value
        lines.append(f"| {tag} | {_cell(item.text, 120)} | {_cell(item.detail)} |")
    path = out / "report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "report.json").write_text(json.dumps({
        "stub_warning": STUB_BANNER, "sandbox_warning": SANDBOX_NOTE, "meta": meta,
        "totals": totals, "check_totals": check_totals, "warnings": warnings,
        "checks": [asdict(r) | {"status": r.status.value} for r in results],
        "items": [asdict(i) | {"status": i.status.value} for i in items],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
