"""Validación del dibujo en el backend (docs/floating/CONTRACT.md §9.1), en este orden:

1. `strip_nulls` (lean.mjs) + `tidy_draw` (port literal de draw.mjs, en `drawjs.py`). Drakter es más
   estricto que zod: las claves que tidy recolocó se quitan de donde estaban; cualquier otra clave de más
   llega al esquema y da `validation_error`.
2. JSON Schema `contracts/floating/draw_args.schema.json` (Draft 2020-12, el estricto) → `validation_error`.
3. `check_draw` (port literal) → `draw_invalid`, con sus líneas en inglés como Roamies.
4. Reglas de Drakter → `draw_action_forbidden`: marcas `type`, `copy`, `open`, `handoff`; botones `open` cuya
   URL no pasa `check_url`, y los que no pasan `checkDrawAction` (safety.mjs:504). Además (revisión del
   PR #76, M4): en una sesión contaminada no hay botones `copy` ni `open`, y un botón `copy` siempre enseña
   en su texto el valor que copia, para que una inyección no pueda pegar en el portapapeles otra cosa.

Además, `lean_schema()` da lo que ve el modelo: el esquema sin `minLength`/`maxLength` y con los elementos de
lista de las tarjetas como objetos sueltos (port de `leanSchema` + `drawModelSchema`).
"""

from __future__ import annotations

import copy
import json
import re
from functools import cache
from pathlib import Path
from typing import Any, Final

import drakter_contracts
from jsonschema import Draft202012Validator

from app.floating import drawjs
from app.floating.safety import BLOCK, check_draw_action, check_url
from app.tools.spec import ToolError

FORBIDDEN_KINDS: Final = ("type", "copy", "open", "handoff")
_MAX_DETAILS: Final = 20
_SCHEMA_PATH: Final = Path(drakter_contracts.__file__).resolve().parents[2] / "floating" / "draw_args.schema.json"
# lean.mjs:7 (NOISE), salvo `additionalProperties`: el registro exige `false` en todo objeto con propiedades.
_NOISE: Final = frozenset({"$schema", "$id", "minLength", "maxLength"})


@cache
def strict_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


@cache
def _validator() -> Draft202012Validator:
    return Draft202012Validator(strict_schema())


def _quiet(v: Any) -> Any:
    """lean.mjs:8-9 `quiet`, más las claves `x-drakter-*` del esquema congelado."""
    if isinstance(v, list):
        return [_quiet(x) for x in v]
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k in _NOISE or k.startswith("x-drakter"):
                continue
            if k == "additionalProperties" and "properties" not in v:
                continue
            out[k] = _quiet(x)
        return out
    return v


@cache
def lean_schema() -> dict[str, Any]:
    """Lo que ve el modelo de `draw` (lean.mjs `leanSchema` + draw.mjs:172 `drawModelSchema`)."""
    return drawjs.draw_model_schema(_quiet(copy.deepcopy(strict_schema())))


def _moved_keys(a: Any) -> tuple[set[str], dict[int, set[str]]]:
    """Qué claves recolocó `tidy_draw` (draw.mjs:149-158 y 128-136), recalculado con sus mismas condiciones."""
    if not drawjs.is_obj(a):
        return set(), {}
    a1 = drawjs.parsed(a)
    # draw.mjs:152
    if a1.get("beats") is None and not a1.get("edit") and isinstance(a1.get("kind"), str):
        a1 = {**a1, "beats": [{"marks": []}]}
    if not isinstance(a1.get("beats"), list):
        return set(), {}
    extra = drawjs.loose(a1, drawjs.CALL_KEYS)
    beats = a1["beats"]
    merged = bool(extra) and len(beats) == 1 and drawjs.is_obj(beats[0])  # draw.mjs:155
    call_moved: set[str] = set(extra) if merged else set()
    if merged:
        beats = [{**extra, **beats[0]}]
    # draw.mjs:157: el say de la llamada pasa al primer beat
    if isinstance(a1.get("say"), str) and beats and drawjs.is_obj(beats[0]) and not isinstance(beats[0].get("say"), str):
        call_moved.add("say")
    beat_moved: dict[int, set[str]] = {}
    for i, b in enumerate(beats):
        if not drawjs.is_obj(b):
            continue
        b1 = drawjs.parsed(b)
        bx = drawjs.loose(b1, drawjs.BEAT_KEYS)
        marks = b1.get("marks") if b1.get("marks") is not None else []
        # draw.mjs:133-136
        if bx and isinstance(marks, list) and (
            (not marks and bx.get("kind"))
            or (len(marks) == 1 and drawjs.is_obj(marks[0]) and (not bx.get("kind") or bx.get("kind") == marks[0].get("kind")))
        ):
            beat_moved[i] = set(bx)
    return call_moved, beat_moved


def tidy_strict(raw: Any) -> Any:
    """strip_nulls → tidy_draw literal → quita lo recolocado → preprocess de zod para `parts[].size` (draw.mjs:53)."""
    a = drawjs.strip_nulls(copy.deepcopy(raw))
    call_moved, beat_moved = _moved_keys(copy.deepcopy(a))
    out = drawjs.tidy_draw(a)
    if not drawjs.is_obj(out):
        return out
    for k in call_moved:
        out.pop(k, None)
    beats = out.get("beats")
    if isinstance(beats, list):
        for i, keys in beat_moved.items():
            if i < len(beats) and drawjs.is_obj(beats[i]):
                for k in keys:
                    beats[i].pop(k, None)
        for b in beats:
            marks = b.get("marks") if drawjs.is_obj(b) else None
            for m in marks if isinstance(marks, list) else []:
                parts = m.get("parts") if drawjs.is_obj(m) else None
                for p in parts if isinstance(parts, list) else []:
                    size = p.get("size") if drawjs.is_obj(p) else None
                    if isinstance(size, int | float) and not isinstance(size, bool):
                        p["size"] = [size] * 3
    return out


def _path(parts: Any) -> str:
    field = ".".join(str(p) for p in parts) or "<root>"
    return re.sub(r"[^\w.\-]", "?", field)[:100]


def _schema_message(error: Any) -> str:
    """Sin repetir el valor recibido: el validador, el límite del esquema o la lista de valores admitidos."""
    kind = error.validator
    expected = error.validator_value
    if kind == "enum":
        return f"must be one of: {', '.join(map(str, expected))}"
    if kind == "const":
        return f"must be {expected!r}"
    if kind == "type":
        return f"must be of type {expected}"
    if kind == "required":
        missing = [k for k in expected if isinstance(error.instance, dict) and k not in error.instance]
        return f"missing {', '.join(missing) or 'a required field'}"
    if kind == "additionalProperties":
        allowed = set((error.schema.get("properties") or {}).keys())
        extra = [k for k in error.instance if k not in allowed] if isinstance(error.instance, dict) else []
        names = ", ".join(re.sub(r"[^\w\-]", "?", str(k))[:24] for k in extra[:4])
        return f"unknown field{'s' if len(extra) != 1 else ''}: {names} (allowed: {', '.join(sorted(allowed))})"
    if kind in ("maxItems", "minItems", "maxLength", "minLength", "maximum", "minimum", "exclusiveMinimum", "exclusiveMaximum"):
        return f"{kind} {expected}"
    return f"does not match the schema ({kind})"


def session_tainted(ctx: Any) -> bool:
    """Falla cerrada: si no se llega al registro de turnos, la sesión cuenta como contaminada."""
    turns = getattr(getattr(ctx.state, "agent_runtime", None), "turns", None)
    return True if turns is None else bool(turns.is_tainted(ctx.session_id))


def _shown(text: Any) -> str:
    return " ".join(text.split()) if isinstance(text, str) else ""


def _action_rule(m: dict[str, Any], action: dict[str, Any], tainted: bool) -> str | None:
    """M4: lo que un botón no puede hacer aunque pase `checkDrawAction`."""
    do = action.get("do")
    if tainted and do in ("copy", "open"):
        return ("en esta conversación hay contenido no confiable (pantalla, documentos o memoria): "
                "no se dibujan botones que copien o abran. Di el valor en el chat.")
    if do == "copy":
        value = _shown(action.get("value"))
        if not value or value not in _shown(m.get("text")):
            return "un botón copy tiene que enseñar en su text exactamente el valor que copia."
    return None


def validate_draw(raw: dict[str, Any], *, tainted: bool = True) -> dict[str, Any]:
    """Devuelve los args ya ordenados y válidos, o lanza `ToolError` con el código del contrato.

    `tainted` es el estado de la sesión; por omisión, contaminada (falla cerrada).
    """
    args = tidy_strict(raw)
    errors = sorted(_validator().iter_errors(args), key=lambda e: list(e.absolute_path))
    if errors:
        details = [
            {"field": _path(e.absolute_path), "code": str(e.validator), "message": _schema_message(e)}
            for e in errors[:_MAX_DETAILS]
        ]
        lines = "\n".join(f"{d['field']}: {d['message']}" for d in details[:6])
        raise ToolError("validation_error", f"Invalid draw arguments.\n{lines}", details=details)
    problems = drawjs.check_draw(args)
    if problems:
        raise ToolError(
            "draw_invalid",
            "\n".join(problems)[:4000],
            details=[{"field": "draw", "code": "draw_invalid", "message": p[:300]} for p in problems[:_MAX_DETAILS]],
        )
    forbidden: list[str] = []
    for i, b in enumerate(args.get("beats") or []):
        for j, m in enumerate(b["marks"]):
            where = f"beat {i + 1} mark {j + 1} ({m['kind']})"
            if m["kind"] in FORBIDDEN_KINDS:
                forbidden.append(f"{where}: en Drakter no se dibuja; para actuar usa act_in_app u open_target.")
                continue
            action = m.get("action")
            if m["kind"] == "button" or action:
                # tools.mjs:648-654 (prepare): todo lo que lleva botón se comprueba como botón; en Drakter
                # `open` además pasa `check_url` (CONTRACT.md §9.1).
                if action and action.get("do") == "open":
                    verdict = check_url(action.get("value"))
                else:
                    verdict = check_draw_action({"kind": "button", "action": action or {}})
                if verdict.level == BLOCK:
                    forbidden.append(f"{where}: Blocked for safety: {verdict.reason}")
                elif action and (rule := _action_rule(m, action, tainted)):
                    forbidden.append(f"{where}: {rule}")
    if forbidden:
        raise ToolError(
            "draw_action_forbidden",
            "\n".join(forbidden)[:4000],
            details=[{"field": "draw", "code": "draw_action_forbidden", "message": p[:300]} for p in forbidden[:_MAX_DETAILS]],
        )
    return args
