#!/usr/bin/env python3
"""Pasada integrada de Drakter. Se lanza con `scripts/verify-all.sh`."""
from __future__ import annotations

import argparse
import atexit
import datetime as dt
import importlib
import os
import signal
import subprocess
import sys
import tomllib
from pathlib import Path

from harness import flows, report
from harness.model import PHASES, REGISTRY, Result, Status, run_check
from harness.stack import Layout, Stack

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCENARIOS = ("backend", "data", "conversation", "desktop", "shutdown")
EXIT_OK, EXIT_FAILED, EXIT_NOT_RUN = 0, 1, 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-dir", type=Path, default=ROOT / "backend")
    parser.add_argument("--desktop-dir", type=Path, default=ROOT / "desktop")
    parser.add_argument("--stub-dir", type=Path, default=ROOT / "tools" / "dev-llm-stub")
    parser.add_argument("--backend-python", type=Path)
    parser.add_argument("--status-file", type=Path, default=ROOT / "docs" / "IMPLEMENTATION_STATUS.md")
    parser.add_argument("--out", type=Path, help="carpeta del informe")
    parser.add_argument("--only", action="append", default=[], metavar="PREFIJO",
                        help="ejecuta solo las comprobaciones con este prefijo (pasada parcial)")
    parser.add_argument("--no-build", action="store_true", help="no recompila desktop/out")
    parser.add_argument("--no-desktop", action="store_true", help="no abre Electron")
    parser.add_argument("--keep-work", action="store_true", help="conserva logs y datos de la pasada")
    parser.add_argument("--min-mem-mb", type=int, default=1500)
    parser.add_argument("--validate", action="store_true",
                        help="valida catálogo y mapa de casillas sin arrancar nada")
    return parser.parse_args()


def mem_available_mb() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 0


def git_source(path: Path) -> str:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True,
                              check=False).stdout.strip()

    commit = git("rev-parse", "--short", "HEAD")
    if not commit or Path(git("rev-parse", "--show-toplevel") or "/nada") not in (path, *path.parents):
        return f"{path} @ sin git"
    dirty = " con cambios sin commit" if git("status", "--porcelain") else ""
    return f"{path} @ {git('rev-parse', '--abbrev-ref', 'HEAD')} {commit}{dirty}"


def desktop_is_stale(desktop: Path) -> bool:
    built = desktop / "out" / "main" / "index.js"
    if not built.is_file():
        return True
    sources = [p for d in ("src", "electron") for p in (desktop / d).rglob("*") if p.is_file()]
    sources += [desktop / "package.json"]
    return max(p.stat().st_mtime for p in sources if p.exists()) > built.stat().st_mtime


class Context:
    """Lo que recibe cada comprobación."""

    def __init__(self, stack: Stack, report_dir: Path, catalog: dict) -> None:
        self.stack = stack
        self.report_dir = report_dir
        self.catalog = catalog
        self.cdp = None
        self.state: dict = {}  # datos compartidos entre comprobaciones

    @property
    def api(self):
        return self.stack.api

    def scrub(self, text: str) -> str:
        token = self.stack.api.token if self.stack.api else None
        return text.replace(token, "[REDACTED]") if token else text


def load_all(catalog_path: Path) -> dict:
    catalog = flows.load_catalog(catalog_path) if catalog_path.is_file() else {}
    for name in SCENARIOS:
        importlib.import_module(f"scenarios.{name}")
    return catalog


def main() -> int:
    args = parse_args()
    catalog = load_all(HERE / "catalog.toml")
    checklists = report.parse_checklists(args.status_file)
    coverage = report.load_coverage(HERE / "coverage.toml")
    problems = report.validate_coverage(coverage, checklists, set(REGISTRY))
    if args.validate:
        print("\n".join(problems) or f"mapa válido: {len(checklists)} casillas, {len(REGISTRY)} comprobaciones")
        return EXIT_NOT_RUN if problems else EXIT_OK
    if problems:
        print("El mapa de casillas no es válido (--validate):", *problems, sep="\n  ", file=sys.stderr)
        return EXIT_NOT_RUN
    available = mem_available_mb()
    if available < args.min_mem_mb:
        print(f"MemAvailable {available} MB < {args.min_mem_mb} MB: no se lanza. "
              "Esta pasada es para cuando se liberen recursos.", file=sys.stderr)
        return EXIT_NOT_RUN

    tmp = Path(os.environ.get("TMPDIR") or "/var/tmp/drakter-e2e")
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    work = tmp / f"verify-{stamp}-{os.getpid()}"
    report_dir = args.out or tmp / f"report-{stamp}"
    python = args.backend_python or args.backend_dir / ".venv" / "bin" / "python"
    with (HERE / "config.toml").open("rb") as handle:
        config = tomllib.load(handle)
    layout = Layout(ROOT, work, args.backend_dir.resolve(), args.desktop_dir.resolve(),
                    args.stub_dir.resolve(), python, config)
    stack = Stack(layout)
    ctx = Context(stack, report_dir, catalog)
    warnings: list[str] = []

    def cleanup(*_):
        stack.stop_all()

    atexit.register(cleanup)
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, lambda *_: sys.exit(EXIT_NOT_RUN))

    selected = lambda name: not args.only or any(name.startswith(p) for p in args.only)
    results: dict[str, Result] = {}

    def run_phase(phase: str) -> None:
        for item in REGISTRY.values():
            if item.phase == phase and selected(item.id):
                result = run_check(item, ctx)
                results[item.id] = result
                print(f"[{result.status.value:^13}] {item.id}: {result.evidence[:110]}", flush=True)

    stack.start_stub()  # antes que el backend: este debe conocer su URL
    stack.start_backend()
    run_phase(PHASES[0])
    if args.no_desktop:
        stack.state["desktop"] = "omitido con --no-desktop"
    else:
        desktop = layout.desktop_dir
        if (desktop / "package.json").is_file() and desktop_is_stale(desktop):
            if args.no_build:
                warnings.append("`desktop/out` es anterior a las fuentes y se usó --no-build.")
            elif (desktop / "node_modules").is_dir():
                print("Compilando el escritorio…", flush=True)
                logs = stack.logs_dir / "desktop-build.log"
                with logs.open("wb") as log:
                    build = subprocess.run(["npm", "run", "build"], cwd=desktop, stdout=log, check=False,
                                           stderr=subprocess.STDOUT, env=stack.base_env())
                if build.returncode != 0:
                    stack.failed.add("desktop")
                    stack.state["desktop"] = f"`npm run build` salió con {build.returncode}"
        if "desktop" not in stack.failed:
            stack.start_desktop()
    run_phase(PHASES[1])
    if ctx.cdp is not None:
        ctx.cdp.close()
    ctx.state["exit_codes"] = stack.stop_all()
    run_phase(PHASES[2])

    if args.only:
        warnings.append(f"Pasada parcial (--only {' '.join(args.only)}): lo demás queda NO COMPROBADO.")
    items = report.judge(checklists, coverage, results)
    sources = {"backend": layout.backend_dir, "desktop": layout.desktop_dir, "stub": layout.stub_dir}
    meta = {
        "date": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "scope": git_source(ROOT),
        "components": {name: {"state": stack.state.get(name, "no se intentó arrancar"),
                              "source": git_source(path) if path.exists() else f"{path} (ausente)"}
                       for name, path in sources.items()},
    }
    path = report.write_report(report_dir, meta, list(results.values()), items, warnings)
    if not args.keep_work and not any(r.status is Status.FALLA for r in results.values()):
        stack.remove_work()
    else:
        print(f"Logs de la pasada: {stack.logs_dir}")
    failed = sum(1 for i in items if i.status is Status.FALLA) + \
        sum(1 for r in results.values() if r.status is Status.FALLA)
    print(f"\n{report.STUB_BANNER}\nInforme: {path}")
    return EXIT_FAILED if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
