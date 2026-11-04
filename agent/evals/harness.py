"""Runs eval cases through a plain Messages API tool loop against a fake backend.

The loop is the same for the stub and for Claude Haiku 5.5; only the client changes. It does not
go through Hermes or MCP: see README.md, Límites.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from grader import RULES, Call, Trace, clean_answer

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parents[1]
SCENARIOS_DIR = EVALS_DIR / "scenarios"
SCHEMAS_PATH = EVALS_DIR / "schemas" / "tool_inputs.json"
IDENTITY_DIR = REPO_ROOT / "agent" / "identity"

CONTRACTS_REF = "drakter/contratos"
STUB_REF = "drakter/dev-stub"
HERMES_REF = "drakter/agente-hermes"
CATALOG_PATH = "contracts/tools/catalog.json"
SAFETY_PATH = "agent/configuration/safety_instructions.md"
STUB_PATH = "tools/dev-llm-stub"

# Same order as backend/app/integrations/hermes/home.py (_IDENTITY_ORDER).
IDENTITY_ORDER = (
    "SOUL.md", "VALUES.md", "PERSONALITY.md", "COMMUNICATION.md", "EMOTIONAL_STYLE.md",
    "BEHAVIOR.md", "CAPABILITIES.md", "TOOL_GUIDE.md", "WORKSPACE_GUIDE.md", "SYSTEM_GUIDE.md",
    "ENVIRONMENT.md", "PREFERENCES.md", "USER.md", "CURRENT_CONTEXT.md",
)
# Frozen so that relative dates in cases mean the same in every run.
EVAL_CLOCK = "Fecha y hora actual: lunes 9 de noviembre de 2026, 10:00 (Europe/Madrid)."
CASE_ID_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
MAX_ROUNDS = 8
MAX_TOKENS = 16000
OUTCOME_STATUSES = {"ok", "error", "confirmation_required"}
STUB_HEADER = "x-drakter-dev-stub"
STUB_MODEL = "drakter-dev-stub"
CONFIRMATION_EXPIRES = "2026-11-09T10:15:00.000Z"
RETRIEVED_AT = "2026-11-09T09:59:00.000Z"


class EvalError(ValueError):
    """Scenarios, sources or credentials are not usable."""


def git_show(ref: str, path: str) -> str:
    done = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{ref}:{path}"], capture_output=True, text=True)
    if done.returncode:
        raise EvalError(f"no encuentro {path} en el repo ni en la rama {ref}")
    return done.stdout


def read_source(path: str, ref: str, override: Path | None = None) -> tuple[str, str]:
    """Prefer the merged file; before integration, fall back to the branch that owns it."""
    candidate = override or REPO_ROOT / path
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8"), str(candidate)
    return git_show(ref, path), f"{ref}:{path}"


def compose_system(system_file: Path | None) -> tuple[str, dict[str, Any]]:
    if system_file:
        text = system_file.read_text(encoding="utf-8")
        return f"{text.strip()}\n\n{EVAL_CLOCK}", {"source": str(system_file), "files": []}
    safety, origin = read_source(SAFETY_PATH, HERMES_REF)
    missing = [name for name in IDENTITY_ORDER if not (IDENTITY_DIR / name).is_file()]
    if missing:
        raise EvalError(f"faltan archivos de identidad: {missing}")
    parts = [safety.strip()] + [(IDENTITY_DIR / name).read_text(encoding="utf-8").strip() for name in IDENTITY_ORDER]
    text = "\n\n".join(parts + [EVAL_CLOCK])
    return text, {
        "source": f"{origin} + agent/identity/",
        "files": list(IDENTITY_ORDER),
        "sha256": hashlib.sha256(text.encode()).hexdigest()[:16],
        "chars": len(text),
    }


@dataclass
class Tools:
    manifests: dict[str, dict[str, Any]]
    schemas: dict[str, dict[str, Any]]
    origin: str
    definitions: list[dict[str, Any]] = field(default_factory=list)

    @property
    def offered(self) -> set[str]:
        return set(self.schemas)


def load_tools(catalog_override: Path | None) -> Tools:
    text, origin = read_source(CATALOG_PATH, CONTRACTS_REF, catalog_override)
    manifests = {item["name"]: item for item in json.loads(text)}
    if not SCHEMAS_PATH.is_file():
        raise EvalError(f"falta {SCHEMAS_PATH}: genera los esquemas con tools/extract_schemas.py")
    schemas = json.loads(SCHEMAS_PATH.read_text(encoding="utf-8"))["tools"]
    unknown = sorted(set(schemas) - set(manifests))
    if unknown:
        raise EvalError(f"esquemas de herramientas fuera del catálogo: {unknown}")
    # Sorted: the tool list is part of the cached prefix.
    definitions = [
        {"name": name, "description": manifests[name]["description"], "input_schema": schemas[name]}
        for name in sorted(schemas)
    ]
    return Tools(manifests, schemas, origin, definitions)


def validate_args(schema: dict[str, Any], args: dict[str, Any]) -> list[str]:
    """Top-level shape only; the fake backend is not the real validator."""
    properties = schema.get("properties", {})
    problems = [f"falta {name}" for name in schema.get("required", []) if name not in args]
    if schema.get("additionalProperties") is False:
        problems += [f"campo desconocido {name}" for name in args if name not in properties]
    return problems


def expand_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    """`{"$untrusted": {...}}` becomes the UntrustedEnvelope the backend wraps documents in."""
    if "$untrusted" not in outcome:
        return outcome
    item = outcome["$untrusted"]
    envelope = {
        "trust": "untrusted", "source_type": item["source_type"], "source_id": item["source_id"],
        "retrieved_at": RETRIEVED_AT, "truncated": False, "content": item["content"],
        "content_hash": hashlib.sha256(item["content"].encode()).hexdigest(),
    }
    return {"status": "ok", "data": envelope}


class FakeBackend:
    """Canned outcomes per tool. It models the contract's gate, it does not test the real one."""

    def __init__(self, case: dict[str, Any], tools: Tools) -> None:
        self.case_id = case["id"]
        self.tools = tools
        self.queues = {name: list(items) for name, items in case.get("tools", {}).items()}
        self.count = 0

    def default_outcome(self, name: str, risk: str) -> dict[str, Any]:
        self.count += 1
        fake_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"drakter-evals/{self.case_id}/{self.count}"))
        if risk == "confirm":
            return {
                "status": "confirmation_required", "action_id": fake_id,
                "summary": "Vas a eliminar 1 elemento. Esta acción no se puede deshacer.",
                "expires_at": CONFIRMATION_EXPIRES,
            }
        if risk == "read":
            return {"status": "ok", "data": {"items": [], "total": 0}}
        return {"status": "ok", "data": {"id": fake_id}}

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        manifest = self.tools.manifests.get(name)
        if manifest is None or name not in self.tools.schemas:
            return {"status": "error", "error": {"code": "not_found", "message": f"Herramienta desconocida: {name}"}}
        problems = validate_args(self.tools.schemas[name], args)
        if problems:
            return {"status": "error", "error": {"code": "validation_error", "message": "; ".join(problems)}}
        queue = self.queues.get(name)
        if not queue:
            return self.default_outcome(name, manifest["risk"])
        outcome = queue.pop(0) if len(queue) > 1 else queue[0]
        return expand_outcome(outcome)


def check_outcome(outcome: Any, where: str) -> list[str]:
    if not isinstance(outcome, dict):
        return [f"{where}: el resultado debe ser un objeto"]
    if "$untrusted" in outcome:
        missing = {"source_type", "source_id", "content"} - set(outcome["$untrusted"])
        return [f"{where}: $untrusted sin {sorted(missing)}"] if missing else []
    status = outcome.get("status")
    if status not in OUTCOME_STATUSES:
        return [f"{where}: status inválido {status!r}"]
    needed = {"ok": {"data"}, "error": {"error"}, "confirmation_required": {"action_id", "summary", "expires_at"}}[status]
    missing = needed - set(outcome)
    return [f"{where}: faltan {sorted(missing)}"] if missing else []


def check_steps(steps: list[dict[str, Any]], tools: Tools, where: str) -> list[str]:
    """The golden path must be a call the real input schema would accept."""
    problems: list[str] = []
    branches = [branch for step in steps for branch in step.get("branches", [])]
    for step in [*steps, *branches]:
        for call in step.get("tool_calls", []):
            name = call["name"]
            if name not in tools.schemas:
                problems.append(f"{where}: {name} no se ofrece")
            else:
                problems += [f"{where}: {name}: {p}" for p in validate_args(tools.schemas[name], call.get("input", {}))]
    return problems


def expected_tools(expect: dict[str, Any]) -> set[str]:
    sequences = expect.get("any_of") or ([expect["sequence"]] if "sequence" in expect else [])
    names: set[str] = set(expect.get("forbidden", []))
    for sequence in sequences:
        for step in sequence:
            names.update(step["tool"] if isinstance(step["tool"], list) else [step["tool"]])
    return names


def check_case(case: dict[str, Any], tools: Tools, seen: set[str]) -> list[str]:
    case_id = case.get("id", "?")
    problems: list[str] = []
    if not CASE_ID_RE.fullmatch(case_id):
        problems.append(f"{case_id}: id inválido")
    if case_id in seen:
        problems.append(f"{case_id}: id repetido")
    seen.add(case_id)
    for key in ("user", "expect", "script", "controls"):
        if key not in case:
            problems.append(f"{case_id}: falta {key}")
    if problems:
        return problems
    for name in expected_tools(case["expect"]) - set(tools.manifests):
        problems.append(f"{case_id}: {name} no está en el catálogo")
    for name, outcomes in case.get("tools", {}).items():
        if name not in tools.schemas:
            problems.append(f"{case_id}: resultado para {name}, que no se ofrece")
            continue
        for outcome in outcomes:
            problems += check_outcome(outcome, f"{case_id}.tools.{name}")
            if tools.manifests[name]["risk"] == "confirm" and outcome.get("status") == "ok":
                problems.append(f"{case_id}: {name} es confirm y el backend nunca devuelve ok sin aprobación")
    problems += check_steps(case["script"], tools, f"{case_id}.script")
    if not case["controls"]:
        problems.append(f"{case_id}: sin controles negativos")
    for control in case["controls"]:
        unknown = set(control.get("expect_rule", [])) - set(RULES)
        if unknown or not control.get("expect_rule"):
            problems.append(f"{case_id}.{control.get('id')}: expect_rule inválido {sorted(unknown)}")
        if not CASE_ID_RE.fullmatch(control.get("id", "")):
            problems.append(f"{case_id}: control con id inválido")
    return problems


def load_suites(tools: Tools, only_suite: str | None = None, only_case: str | None = None) -> list[dict[str, Any]]:
    suites, problems, seen = [], [], set()
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        suite = json.loads(path.read_text(encoding="utf-8"))
        for case in suite["cases"]:
            problems += check_case(case, tools, seen)
        suites.append(suite)
    if problems:
        raise EvalError("escenarios no válidos:\n  " + "\n  ".join(problems))
    if not suites:
        raise EvalError(f"no hay escenarios en {SCENARIOS_DIR}")
    chosen = []
    for suite in suites:
        if only_suite and suite["suite"] != only_suite:
            continue
        cases = [c for c in suite["cases"] if not only_case or c["id"] == only_case]
        if cases:
            chosen.append({**suite, "cases": cases})
    if not chosen:
        raise EvalError("ningún caso coincide con el filtro")
    return chosen


def rule_coverage(suites: list[dict[str, Any]]) -> list[str]:
    """Rules that no control proves able to fail: a rule that never bites proves nothing."""
    covered = {rule for s in suites for c in s["cases"] for ctl in c["controls"] for rule in ctl["expect_rule"]}
    return sorted(set(RULES) - covered)


class Stub:
    """Starts the scripted server on an ephemeral loopback port with compiled scenarios."""

    def __init__(self, suites: list[dict[str, Any]], stub_dir: Path | None, work: Path) -> None:
        self.work = work
        self.server = self.locate(stub_dir)
        scenarios = work / "stub-scenarios"
        scenarios.mkdir()
        (scenarios / "sin-marca.json").write_text(json.dumps({
            "description": "El arnés no puso la marca de escenario.",
            "steps": [{"text": "FALLO: petición sin marca de escenario."}],
        }), encoding="utf-8")
        for suite in suites:
            for case in suite["cases"]:
                self.write(scenarios, case["id"], case["script"])
                for control in case["controls"]:
                    self.write(scenarios, f"{case['id']}--{control['id']}", control["steps"])
        self.scenarios = scenarios

    @staticmethod
    def write(directory: Path, name: str, steps: list[dict[str, Any]]) -> None:
        (directory / f"{name}.json").write_text(json.dumps({"description": name, "steps": steps}), encoding="utf-8")

    def locate(self, stub_dir: Path | None) -> Path:
        base = stub_dir or REPO_ROOT / STUB_PATH
        if (base / "server.py").is_file():
            return base / "server.py"
        target = self.work / "stub-src"
        target.mkdir()
        archive = subprocess.run(["git", "-C", str(REPO_ROOT), "archive", STUB_REF, STUB_PATH], capture_output=True)
        if archive.returncode:
            raise EvalError(f"no encuentro el stub en {STUB_PATH} ni en la rama {STUB_REF}")
        subprocess.run(["tar", "-x", "-C", str(target)], input=archive.stdout, check=True)
        return target / STUB_PATH / "server.py"

    def __enter__(self) -> "Stub":
        self.log = self.work / "stub.log"
        # Only what it needs: DRAKTER_ENV stays so the stub keeps refusing production.
        env = {k: v for k, v in os.environ.items() if k in {"PATH", "DRAKTER_ENV"}}
        self.handle = self.log.open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "-I", str(self.server), "--port", "0", "--scenarios", str(self.scenarios),
             "--default-scenario", "sin-marca"],
            stderr=self.handle, stdout=subprocess.DEVNULL, env=env,
        )
        for _ in range(100):
            found = re.search(r"http://127\.0\.0\.1:(\d+)", self.log.read_text(encoding="utf-8"))
            if found:
                self.url = found.group(0)
                return self
            if self.process.poll() is not None:
                break
            time.sleep(0.05)
        self.__exit__()
        raise EvalError(f"el stub no arrancó: {self.log.read_text(encoding='utf-8')}")

    def __exit__(self, *_: Any) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)
        self.handle.close()


@dataclass
class RunState:
    system: str
    tools: Tools
    model: str
    client: Any
    stub_marks: bool
    saw_stub: bool = False
    saw_model: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


def seen_text(case: dict[str, Any]) -> str:
    history = " ".join(str(message.get("content", "")) for message in case.get("history", []))
    return f"{history} {case['user']}"


def run_case(state: RunState, case: dict[str, Any], scenario: str) -> Trace:
    """One fresh session: nothing is carried over between cases or repeats."""
    user = f"{case['user']} [stub:{scenario}]" if state.stub_marks else case["user"]
    messages: list[dict[str, Any]] = [*case.get("history", []), {"role": "user", "content": user}]
    backend = FakeBackend(case, state.tools)
    trace = Trace(seen_text=seen_text(case))
    system = [{"type": "text", "text": state.system, "cache_control": {"type": "ephemeral"}}]
    for _ in range(MAX_ROUNDS + 1):
        raw = state.client.messages.with_raw_response.create(
            model=state.model, max_tokens=MAX_TOKENS, system=system,
            tools=state.tools.definitions, messages=messages,
        )
        response = raw.parse()
        # Decided from what came back, not from a flag: a stub can never pass as a model.
        is_stub = raw.headers.get(STUB_HEADER) == "true" or response.model == STUB_MODEL
        state.saw_stub |= is_stub
        state.saw_model |= not is_stub
        state.input_tokens += response.usage.input_tokens
        state.output_tokens += response.usage.output_tokens
        state.cache_read_tokens += response.usage.cache_read_input_tokens or 0
        trace.rounds += 1
        trace.stop_reason = response.stop_reason or ""
        trace.answer = clean_answer("\n".join(b.text for b in response.content if b.type == "text"))
        # Whole content, unedited: replayed thinking blocks must stay as they came.
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return trace
        results = []
        for block in response.content:
            if block.type == "tool_use":
                outcome = backend.call(block.name, block.input)
                trace.calls.append(Call(block.name, block.input, outcome))
                # isError stays false in foreseeable rejections, as in the contract.
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(outcome, ensure_ascii=False)})
        messages.append({"role": "user", "content": results})
    trace.round_limit_hit = True
    return trace


def work_dir() -> Path:
    base = os.environ.get("TMPDIR") or "/var/tmp"
    return Path(tempfile.mkdtemp(prefix="drakter-evals-", dir=base))
