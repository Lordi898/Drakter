"""Deterministic grading of one agent run. No model is involved.

Every style rule quotes a line of agent/identity/. What cannot be decided by a rule (humour,
judgement, tone) is a `rubric` line for a human and never counts as passed here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

MARKER = "[DEV-STUB]"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")
SENTENCE_RE = re.compile(r"[^.?!\n]+(?:[.?!]+|$)")

# rule id -> where it comes from
RULES: dict[str, str] = {
    "tool.expected": "TOOL_GUIDE: cuándo usar cada grupo",
    "tool.forbidden": "BEHAVIOR/TOOL_GUIDE: herramienta que no debe llamarse en este caso",
    "tool.none_expected": "BEHAVIOR: preguntar antes de actuar",
    "tool.not_offered": "TOOL_GUIDE: vale la lista de ejecución",
    "tool.invented_id": "TOOL_GUIDE: los identificadores se toman de un resultado",
    "tool.repeat_after_error": "TOOL_GUIDE: repetir la misma llamada sin cambios no sirve",
    "run.round_limit": "arnés: bucle sin final",
    "run.stop_reason": "arnés: el turno no terminó con una respuesta",
    "answer.missing": "BEHAVIOR: lo que la respuesta debe decir en este caso",
    "answer.forbidden": "BEHAVIOR: lo que la respuesta no puede afirmar en este caso",
    "style.emoji": "COMMUNICATION: sin emojis",
    "style.exclamation": "COMMUNICATION: sin signos de exclamación por cortesía",
    "style.banned_phrase": "COMMUNICATION: vocabulario fuera",
    "style.formal": "COMMUNICATION: tuteas siempre",
    "style.filler": "COMMUNICATION: sin introducción, resumen ni oferta de ayuda de relleno",
    "style.tech_leak": "COMMUNICATION: identificadores, herramientas y códigos fuera",
    "style.signature_twice": "COMMUNICATION: nunca dos expresiones propias en la misma respuesta",
    "style.too_long": "COMMUNICATION: una o dos frases para lo cotidiano",
    "style.coach": "PERSONALITY: ni coach ni terapeuta",
    "style.fantasy": "SOUL/PERSONALITY: sin rol fantástico",
}

BANNED_PHRASES = (
    "por supuesto", "claro que sí", "como ia", "espero que te sirva", "estoy aquí para ayudarte",
    "no dudes en", "excelente pregunta", "lamento las molestias",
)
FILLERS = (
    "¿necesitas algo más", "¿algo más", "¿quieres algo más", "¿te ayudo con algo más",
    "avísame si necesitas", "si necesitas cualquier cosa", "he revisado tu",
    "he encontrado la información", "en resumen,",
)
COACH = (
    "no te rindas", "tú puedes", "lo harás genial", "mucha suerte", "nueva oportunidad",
    "está bien no estar bien", "entiendo tu frustración", "siento que te sientas",
    "¿quieres hablar de ello",
)
FANTASY = ("mortal", "oh gran señor", "cámara acorazada", "valeroso", "tu tesoro", "mi tesoro")
SIGNATURES = ("anotado.", "guardado.", "eso no estaba donde dijiste", "mal asunto")
FORMAL_RE = re.compile(r"\b(usted|ustedes|desea usted|le recomiendo)\b", re.I)
ANIMO_RE = re.compile(r"(?<!de )\bánimo\b", re.I)


@dataclass
class Call:
    name: str
    input: dict[str, Any]
    outcome: dict[str, Any]


@dataclass
class Trace:
    calls: list[Call] = field(default_factory=list)
    answer: str = ""
    stop_reason: str = ""
    rounds: int = 0
    round_limit_hit: bool = False
    seen_text: str = ""  # what the user supplied, so ids quoted there are not "invented"


@dataclass(frozen=True)
class Finding:
    rule: str
    detail: str


def clean_answer(text: str) -> str:
    return text.replace(MARKER, "").strip()


def dig(value: Any, path: list[str]) -> Any:
    for part in path:
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def resolve_ref(ref: str, prior: list[Call]) -> Any:
    tool, *path = ref.split(".")
    for call in reversed(prior):
        if call.name == tool:
            try:
                return dig(call.outcome, path)
            except (KeyError, IndexError, ValueError, TypeError):
                return None
    return None


def value_matches(expected: Any, actual: Any, prior: list[Call]) -> bool:
    if isinstance(expected, dict) and len(expected) == 1:
        (op, operand), = expected.items()
        if op == "$from":
            wanted = resolve_ref(operand, prior)
            return wanted is not None and actual == wanted
        if op == "$contains":
            return isinstance(actual, str) and operand.casefold() in actual.casefold()
        if op == "$any":
            return any(value_matches(option, actual, prior) for option in operand)
        if op == "$present":
            return actual is not None
    return expected == actual


def step_matches(step: dict[str, Any], index: int, calls: list[Call]) -> bool:
    call = calls[index]
    names = step["tool"] if isinstance(step["tool"], list) else [step["tool"]]
    if call.name not in names:
        return False
    return all(value_matches(want, call.input.get(key), calls[:index]) for key, want in step.get("args", {}).items())


def sequence_matches(sequence: list[dict[str, Any]], calls: list[Call], exact: bool) -> bool:
    """Ordered subsequence: a real model may add reads between the required steps."""
    if exact and len(sequence) != len(calls):
        return False
    position = 0
    for step in sequence:
        while position < len(calls) and not step_matches(step, position, calls):
            position += 1
        if position == len(calls):
            return False
        position += 1
    return True


def grade_tools(expect: dict[str, Any], trace: Trace, offered: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    names = [call.name for call in trace.calls]
    if expect.get("no_tools") and names:
        findings.append(Finding("tool.none_expected", f"llamó a {names}"))
    alternatives = expect.get("any_of") or ([expect["sequence"]] if "sequence" in expect else [])
    if alternatives and not any(sequence_matches(seq, trace.calls, expect.get("exact", False)) for seq in alternatives):
        findings.append(Finding("tool.expected", f"secuencia real {names}"))
    for name in sorted(set(names) & set(expect.get("forbidden", []))):
        findings.append(Finding("tool.forbidden", name))
    for name in sorted(set(names) - offered):
        findings.append(Finding("tool.not_offered", name))

    seen = trace.seen_text.casefold()
    previous: Call | None = None
    for call in trace.calls:
        for found in UUID_RE.findall(str(call.input)):
            if found.casefold() not in seen:
                findings.append(Finding("tool.invented_id", f"{call.name}: {found}"))
        seen += " " + str(call.outcome).casefold()
        failed = previous and previous.outcome.get("status") == "error"
        retryable = previous and previous.outcome.get("error", {}).get("retryable")
        if failed and not retryable and (previous.name, previous.input) == (call.name, call.input):
            findings.append(Finding("tool.repeat_after_error", call.name))
        previous = call
    return findings


def grade_answer(expect: dict[str, Any], answer: str) -> list[Finding]:
    findings: list[Finding] = []
    lowered = answer.casefold()
    for group in expect.get("must_include", []):
        options = group if isinstance(group, list) else [group]
        if not any(option.casefold() in lowered for option in options):
            findings.append(Finding("answer.missing", " | ".join(options)))
    for pattern in expect.get("must_not_match", []):
        if re.search(pattern, answer, re.I):
            findings.append(Finding("answer.forbidden", pattern))
    return findings


def grade_style(expect: dict[str, Any], answer: str, tool_names: set[str], trace: Trace) -> list[Finding]:
    off = set(expect.get("style_off", []))
    lowered = answer.casefold()
    checks: list[tuple[str, list[str]]] = [
        ("style.emoji", EMOJI_RE.findall(answer)),
        ("style.exclamation", [c for c in answer if c in "!¡"]),
        ("style.banned_phrase", [p for p in BANNED_PHRASES if p in lowered]),
        ("style.formal", FORMAL_RE.findall(answer)),
        ("style.filler", [p for p in FILLERS if p in lowered]),
        ("style.coach", [p for p in COACH if p in lowered] + ANIMO_RE.findall(answer)),
        ("style.fantasy", [p for p in FANTASY if p in lowered]),
    ]
    codes = {str(c.outcome.get("error", {}).get("code")) for c in trace.calls if c.outcome.get("status") == "error"}
    leaks = UUID_RE.findall(answer) + [n for n in sorted(tool_names | codes) if re.search(rf"\b{re.escape(n)}\b", answer)]
    checks.append(("style.tech_leak", leaks))
    signatures = [s for s in SIGNATURES if s in lowered]
    checks.append(("style.signature_twice", signatures if len(signatures) > 1 else []))
    limit = expect.get("max_sentences")
    sentences = [s for s in SENTENCE_RE.findall(answer) if s.strip()]
    if limit and len(sentences) > limit:
        checks.append(("style.too_long", [f"{len(sentences)} frases, máximo {limit}"]))
    return [Finding(rule, ", ".join(hits)) for rule, hits in checks if hits and rule not in off]


def grade(case: dict[str, Any], trace: Trace, offered: set[str], catalog_names: set[str]) -> list[Finding]:
    expect = case["expect"]
    findings: list[Finding] = []
    if trace.round_limit_hit:
        findings.append(Finding("run.round_limit", str(trace.rounds)))
    if trace.stop_reason != "end_turn" or not trace.answer:
        findings.append(Finding("run.stop_reason", trace.stop_reason or "sin respuesta"))
    findings += grade_tools(expect, trace, offered)
    findings += grade_answer(expect, trace.answer)
    findings += grade_style(expect, trace.answer, catalog_names, trace)
    return findings
