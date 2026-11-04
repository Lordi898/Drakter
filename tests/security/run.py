#!/usr/bin/env python3
"""Lanza el banco contra un backend real. Ver tests/security/README.md."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from contract import CONTRACT  # noqa: E402
from redlib import ATTACKS, cleanup, run_attacks, start_target  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, type=Path, help="carpeta backend/ a atacar")
    parser.add_argument("--python", required=True, help="intérprete con las dependencias del backend")
    parser.add_argument("--only", help="prefijo de id, por ejemplo NET o CONF-02")
    parser.add_argument("--contract", type=Path, help="JSON que reemplaza claves de contract.py")
    parser.add_argument("--report", type=Path, help="escribe aquí los resultados en JSON")
    args = parser.parse_args()

    contract = dict(CONTRACT)
    if args.contract:
        contract.update(json.loads(args.contract.read_text("utf-8")))
    broken = 0
    for module in sorted(HERE.glob("attacks_*.py")):
        try:
            importlib.import_module(module.stem)
        except Exception as exc:  # noqa: BLE001 - un módulo roto no debe ocultar el resto
            broken += 1
            print(f"ERROR          {module.name}: {exc!r}")
    selected = [item for item in ATTACKS if not args.only or item.id.startswith(args.only)]

    context = start_target(args.backend.resolve(), args.python, contract)
    try:
        results = run_attacks(context, selected)
    finally:
        cleanup(context)

    totals = {
        verdict: sum(item["verdict"] == verdict for item in results)
        for verdict in ("BLOCKED", "BREACH", "NOT_APPLICABLE", "ERROR")
    }
    totals["ERROR"] += broken
    print(json.dumps(totals))
    if args.report:
        args.report.write_text(json.dumps(results, ensure_ascii=False, indent=2), "utf-8")
    return 1 if totals["BREACH"] or totals["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
