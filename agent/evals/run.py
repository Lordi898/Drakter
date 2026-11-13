#!/usr/bin/env python3
"""Drakter agent evals. See README.md.

With the stub this proves the pipeline only, never the quality of the model.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

import grader  # noqa: E402
import harness  # noqa: E402
from harness import EvalError, RunState, Stub  # noqa: E402

DEFAULT_MODEL = "claude-haiku-5-5"
ANTHROPIC_URL = "https://api.anthropic.com"
BANNER_STUB = (
    "⚠️ EVIDENCIA: STUB. Esto prueba la tubería (identidad, catálogo, bucle, calificador).\n"
    "⚠️ CALIDAD DEL MODELO: NO EVALUADA. Selección de herramientas, operaciones encadenadas y\n"
    "   personalidad quedan pendientes de repetirse con Claude Haiku 5.5."
)
EXIT_OK, EXIT_FAILED, EXIT_BLOCKED = 0, 1, 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["stub", "anthropic"], default="stub")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--suite")
    parser.add_argument("--case")
    parser.add_argument("--repeat", type=int, default=1, help="sesiones nuevas por caso (consistencia)")
    parser.add_argument("--check", action="store_true", help="valida escenarios sin ejecutar nada")
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--stub-dir", type=Path)
    parser.add_argument("--system-file", type=Path, help="prompt real capturado, en lugar del compuesto")
    parser.add_argument("--base-url", help="solo loopback; para ensayar --provider anthropic sin red")
    parser.add_argument("--out", type=Path, help="directorio de informes")
    return parser.parse_args()


def is_loopback(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def make_client(args: argparse.Namespace, url: str | None) -> Any:
    import anthropic

    if args.provider == "stub":
        # No credential of the user can reach even the local stub.
        for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE", "ANTHROPIC_BASE_URL"):
            os.environ.pop(name, None)
        return anthropic.Anthropic(api_key="dev-stub-sin-clave", base_url=url, max_retries=0)
    if args.base_url and not is_loopback(args.base_url):
        raise EvalError("--base-url solo admite loopback: la clave no sale hacia otro destino")
    # Explicit, so an inherited ANTHROPIC_BASE_URL cannot redirect the key.
    return anthropic.Anthropic(base_url=args.base_url or ANTHROPIC_URL)


def run_cases(state: RunState, suites: list[dict[str, Any]], tools: harness.Tools, repeat: int) -> list[dict[str, Any]]:
    catalog = set(tools.manifests)
    rows = []
    for suite in suites:
        for case in suite["cases"]:
            runs = []
            for _ in range(repeat):
                trace = harness.run_case(state, case, case["id"])
                findings = grader.grade(case, trace, tools.offered, catalog)
                runs.append({
                    "passed": not findings,
                    "tools": [call.name for call in trace.calls],
                    "findings": [vars(f) for f in findings],
                    "answer": trace.answer,
                    "rounds": trace.rounds,
                })
            rows.append({
                "suite": suite["suite"], "case": case["id"], "title": case.get("title", ""),
                "runs": runs, "passed": all(r["passed"] for r in runs),
                "distinct_tool_paths": len({tuple(r["tools"]) for r in runs}),
                "rubric": case.get("rubric", []),
            })
    return rows


def run_controls(state: RunState, suites: list[dict[str, Any]], tools: harness.Tools) -> list[dict[str, Any]]:
    """Scripted misbehaviour: the grader must fail each one, for the expected reason."""
    catalog = set(tools.manifests)
    rows = []
    for suite in suites:
        for case in suite["cases"]:
            for control in case["controls"]:
                trace = harness.run_case(state, case, f"{case['id']}--{control['id']}")
                fired = {f.rule for f in grader.grade(case, trace, tools.offered, catalog)}
                missed = sorted(set(control["expect_rule"]) - fired)
                rows.append({
                    "case": case["id"], "control": control["id"], "caught": not missed,
                    "expected": control["expect_rule"], "fired": sorted(fired), "missed": missed,
                })
    return rows


def write_report(out: Path, report: dict[str, Any]) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Evals de Drakter: {report['evidence']}", "", report["banner"], ""]
    lines += ["| Suite | Caso | Resultado | Caminos | Hallazgos |", "|---|---|---|---|---|"]
    for row in report["cases"]:
        rules = sorted({f["rule"] for run in row["runs"] for f in run["findings"]})
        lines.append(f"| {row['suite']} | {row['case']} | {'ok' if row['passed'] else 'FALLA'} "
                     f"| {row['distinct_tool_paths']} | {', '.join(rules)} |")
    if report["controls"]:
        caught = sum(c["caught"] for c in report["controls"])
        lines += ["", f"Controles negativos cazados: {caught}/{len(report['controls'])}."]
    if report["evidence"].startswith("model:"):
        lines += ["", "## ⚠️ Revisión humana pendiente", ""]
        for row in report["cases"]:
            if row["rubric"]:
                lines += [f"### {row['case']}", *[f"- {item}" for item in row["rubric"]], ""]
                lines += [f"> {run['answer']}" for run in row["runs"]] + [""]
    path = out / "report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def summarize(report: dict[str, Any]) -> None:
    print(report["banner"])
    totals: Counter[str] = Counter()
    for row in report["cases"]:
        totals[f"{row['suite']}:{'ok' if row['passed'] else 'falla'}"] += 1
    suites = sorted({row["suite"] for row in report["cases"]})
    for suite in suites:
        print(f"  {suite}: {totals[f'{suite}:ok']} ok, {totals[f'{suite}:falla']} fallan")
    for row in report["cases"]:
        if not row["passed"]:
            rules = sorted({f"{f['rule']}: {f['detail']}" for run in row["runs"] for f in run["findings"]})
            print(f"  FALLA {row['case']}: {rules}")
    if report["controls"]:
        caught = sum(c["caught"] for c in report["controls"])
        print(f"  controles negativos cazados: {caught}/{len(report['controls'])}")
        for control in report["controls"]:
            if not control["caught"]:
                print(f"  NO CAZADO {control['case']}--{control['control']}: faltó {control['missed']}, saltó {control['fired']}")
    if report["uncovered_rules"]:
        print(f"  reglas sin control que las demuestre: {report['uncovered_rules']}")
    print(f"  tokens: entrada {report['usage']['input']}, salida {report['usage']['output']}, caché {report['usage']['cache_read']}")


def main() -> int:
    args = parse_args()
    try:
        tools = harness.load_tools(args.catalog)
        suites = harness.load_suites(tools, args.suite, args.case)
        all_suites = harness.load_suites(tools)
        system, identity = harness.compose_system(args.system_file)
        uncovered = harness.rule_coverage(all_suites)
        if args.check:
            count = sum(len(s["cases"]) for s in all_suites)
            print(f"{count} casos válidos; {len(tools.offered)} herramientas ofrecidas de {len(tools.manifests)}; prompt {len(system)} caracteres")
            if uncovered:
                print(f"reglas sin control: {uncovered}")
            return EXIT_FAILED if uncovered else EXIT_OK

        work = harness.work_dir()
        out = args.out or work
        if args.provider == "stub":
            with Stub(suites, args.stub_dir, work) as stub:
                state = RunState(system, tools, "drakter-dev-stub", make_client(args, stub.url), stub_marks=True)
                cases = run_cases(state, suites, tools, args.repeat)
                controls = run_controls(state, suites, tools)
        else:
            state = RunState(system, tools, args.model, make_client(args, None), stub_marks=False)
            cases = run_cases(state, suites, tools, args.repeat)
            controls = []
    except EvalError as exc:
        print(f"BLOQUEADO: {exc}", file=sys.stderr)
        return EXIT_BLOCKED
    except Exception as exc:
        import anthropic

        if isinstance(exc, (anthropic.AnthropicError, TypeError)):
            # Never echoes the request: the SDK message carries no key, but keep it to the type.
            print(f"BLOQUEADO: ⚠️ sin acceso al modelo ({type(exc).__name__}). Calidad del modelo NO EVALUADA.", file=sys.stderr)
            return EXIT_BLOCKED
        raise

    if state.saw_stub or not state.saw_model:
        evidence, banner = "stub", BANNER_STUB
    else:
        evidence = f"model:{args.model}"
        banner = (f"EVIDENCIA: {args.model}, {args.repeat} sesión(es) por caso.\n"
                  "⚠️ Las rúbricas de personalidad siguen pendientes de lectura humana (report.md).")
    report = {
        "evidence": evidence, "banner": banner, "provider": args.provider, "repeat": args.repeat,
        "identity": identity, "catalog": tools.origin, "offered_tools": len(tools.offered),
        "cases": cases, "controls": controls,
        "uncovered_rules": uncovered if args.provider == "stub" and not args.case and not args.suite else [],
        "usage": {"input": state.input_tokens, "output": state.output_tokens, "cache_read": state.cache_read_tokens},
    }
    path = write_report(out, report)
    summarize(report)
    print(f"  informe: {path}")
    failed = any(not row["passed"] for row in cases) or any(not c["caught"] for c in controls) or report["uncovered_rules"]
    return EXIT_FAILED if failed else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
