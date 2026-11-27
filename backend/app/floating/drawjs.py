"""Port literal a Python de `showcase/tauri/sidecar/draw.mjs` de Roamies (docs/floating/CONTRACT.md §9.1).

Origen: KenKaiii/Roamies@8f0adaa, `showcase/tauri/sidecar/draw.mjs` (y `stripNulls` de `lean.mjs`).
Licencia: AGPL-3.0 (la misma que Drakter, ver THIRD_PARTY_NOTICES.md). Cada bloque cita su línea
original como `# draw.mjs:N`. Los mensajes en inglés son los de Roamies, tal cual: el modelo los lee.
`countries.json` sale de `countries.mjs` (Natural Earth 110m admin-0, dominio público), mismo orden.

Qué no se porta (no hace falta en el backend de Drakter): el esquema zod (está ya como JSON Schema en
`contracts/floating/draw_args.schema.json`), `resolveTarget(s)` salvo sus líneas 416-421 (`enrich_mark`),
`shapeRadius`, `pickTextMatch`, `fitWindow`, `windowSized`, fotos y favicons, `createLists` y `quizNote`.

Desviaciones inevitables de la semántica JS (documentadas, sin efecto en datos ya validados por el esquema):
- `undefined` es una clave ausente; `null` no llega (se quita antes con `strip_nulls`). `String(undefined)` es
  `'undefined'` (`js_str(None)`).
- Las longitudes y `slice` de textos cuentan unidades UTF-16 como JS (`u16len`, `u16slice`); los índices de
  `parse_smiles`/`parse_tex` recorren puntos de código (un carácter fuera del BMP cuenta como uno, no como dos).
- `\\s` de Python y de JS difieren en unos pocos caracteres de control (`\\x1c-\\x1f`, `\\ufeff`); `trim` sí usa el
  conjunto de JS (`js_trim`). `\\d` y `\\b` se escriben como ASCII, igual que en JS.
- Las propiedades heredadas del prototipo de `Object` (`'constructor' in TEX_SPACE`…) no se emulan.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections.abc import Callable, Iterable
from functools import cmp_to_key
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------- semántica de JS (auxiliares, no son de draw.mjs)
_JS_WS = "\t\n\v\f\r \xa0                　﻿"
_TRIM_RE = re.compile(f"^[{re.escape(_JS_WS)}]+|[{re.escape(_JS_WS)}]+$")


def js_trim(s: str) -> str:
    """`String.prototype.trim`."""
    return _TRIM_RE.sub("", s)


def truthy(v: Any) -> bool:
    """Verdad de JS: `[]` y `{}` son verdaderos; `''`, `0`, `NaN`, `null`, `undefined` y `false`, falsos."""
    if v is None or v is False:
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v == v and v != 0
    if isinstance(v, str):
        return v != ""
    return True


def is_num(v: Any) -> bool:
    """`typeof v === 'number'`."""
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def js_round(x: float) -> int:
    """`Math.round` (las mitades van hacia +∞)."""
    return math.floor(x + 0.5)


def _num_str(v: float) -> str:
    if v != v:
        return "NaN"
    if v in (math.inf, -math.inf):
        return "Infinity" if v > 0 else "-Infinity"
    if float(v).is_integer() and abs(v) < 1e21:
        return str(int(v))
    return repr(float(v))


def js_str(v: Any) -> str:
    """`String(v)` (y `${v}`)."""
    if v is None:
        return "undefined"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return v
    if is_num(v):
        return _num_str(v)
    if isinstance(v, list):
        return ",".join("" if x is None else js_str(x) for x in v)
    if isinstance(v, dict):
        return "[object Object]"
    return str(v)


def u16len(s: str) -> int:
    """`s.length` (unidades UTF-16)."""
    return len(s.encode("utf-16-le", "surrogatepass")) // 2


def u16slice(s: str, end: int) -> str:
    """`s.slice(0, end)` (unidades UTF-16)."""
    return s.encode("utf-16-le", "surrogatepass")[: end * 2].decode("utf-16-le", "surrogatepass")


def _len(v: Any) -> int | None:
    """`v?.length`: None si no es una lista o un texto."""
    if isinstance(v, list):
        return len(v)
    if isinstance(v, str):
        return u16len(v)
    return None


def _ge(a: int | None, b: int) -> bool:
    """`a >= b` con `a` posiblemente `undefined` (falso)."""
    return a is not None and a >= b


def _coalesce(*thunks: Callable[[], Any]) -> Any:
    """`a ?? b ?? …`, perezoso."""
    for t in thunks:
        v = t()
        if v is not None:
            return v
    return None


def _get(o: Any, k: str) -> Any:
    """`o?.[k]`."""
    return o.get(k) if isinstance(o, dict) else None


def _first(v: Any) -> Any:
    """`v?.[0]`."""
    return v[0] if isinstance(v, list) and v else None


def strip_nulls(v: Any) -> Any:
    """lean.mjs:16-20: algunos modelos mandan null por un campo que omiten (ningún campo de Roamies admite null)."""
    if isinstance(v, list):
        return [strip_nulls(x) for x in v]
    if isinstance(v, dict):
        return {k: strip_nulls(x) for k, x in v.items() if x is not None}
    return v


# ---------------------------------------------------------------- draw.mjs:9-23
LIMITS: dict[str, int] = {"beats": 12, "marks": 40, "points": 200, "parts3d": 40, "atoms": 120, "photoBytes": 800_000, "iconBytes": 64_000,
  "nodes": 16, "links": 24, "columns": 6, "rows": 12, "bars": 12, "labels": 8, "pins": 12, "shade": 40, "routes": 8, "steps": 10, "tex": 300, "vertices": 16, "questions": 6, "cardsShown": 8}  # draw.mjs:9-10
TONES = ["accent", "teal", "amber", "coral", "lilac", "sky", "lime", "red", "white"]  # draw.mjs:11
# Marks on the real screen (they need a place on it), actions in apps, and cards drawn on calm space.  # draw.mjs:12
SCREEN = ["point", "target", "hover", "ring", "frame", "underline", "strike", "check", "cross", "connect", "trace", "num", "label", "write", "scroll", "spotlight", "highlight", "line", "curve", "arrow", "circle", "rect"]  # draw.mjs:13
ACTIONS = ["emote", "sfx", "type", "copy", "open", "handoff", "button"]  # draw.mjs:14
CARDS = ["card", "note", "list", "mindmap", "clip", "sources", "photo", "graph", "legend", "timeline", "molecule", "model", "flow", "table", "bars", "map", "math", "geometry", "quiz", "ticket", "medal"]  # draw.mjs:15
KINDS = [*SCREEN, *ACTIONS, *CARDS]  # draw.mjs:16
# Drawn from a list of points (screenshot pixels) instead of one place.  # draw.mjs:17
PATHS = {"trace", "line", "curve", "arrow"}  # draw.mjs:18
EMOTES = ["hype", "wave", "upset", "remind", "motivate"]  # draw.mjs:19
SOUNDS = ["pop", "tick", "blip", "whoosh", "scan", "done", "page", "hype", "focus", "expand"]  # draw.mjs:20
SHAPES = ["box", "sphere", "cylinder", "cone", "torus"]  # draw.mjs:21
MOTIONS = ["spin", "orbit", "slide", "pulse"]  # draw.mjs:22
NODE_SHAPES = ["box", "round", "diamond"]  # draw.mjs:23

# draw.mjs:25-77: el esquema zod (`Target`, `Mark`) vive en contracts/floating/draw_args.schema.json.


# ---------------------------------------------------------------- draw.mjs:78-114
# Some models (Gemini Flash-Lite, #81) put a lone mark's fields on its beat or on the call itself instead of in marks,
# a button's text as label, a card's heading as title: moved where they go before the schema sees them.
BEAT_KEYS = {"say", "marks", "wait"}  # draw.mjs:80
CALL_KEYS = {"target", "beats", "edit", "deep", "keep"}  # draw.mjs:80


def is_obj(v: Any) -> bool:  # draw.mjs:81
    return isinstance(v, dict)


def loose(o: dict[str, Any], keep: set[str]) -> dict[str, Any]:  # draw.mjs:82
    return {k: v for k, v in o.items() if k not in keep}


# The model sees a card's list items only as objects (drawModelSchema), so the shapes it guesses are set right here:
# {x, y, z} (or {x, y}) for [x, y, z], {min, max} for a range, a row keyed by column, {text} for a plain list item.
def as_vec(v: Any) -> Any:  # draw.mjs:85-86
    if not is_obj(v):
        return v
    if "x" in v and "y" in v:
        return [v[k] for k in ("x", "y", "z") if k in v]
    if "min" in v and "max" in v:
        return [v["min"], v["max"]]
    if is_num(v.get("from")) and is_num(v.get("to")):
        return [v["from"], v["to"]]
    return v


def as_vecs(v: Any) -> Any:  # draw.mjs:87
    return [as_vec(x) for x in v] if isinstance(v, list) else v


def as_text(v: Any) -> Any:  # draw.mjs:88
    return v["text"] if is_obj(v) and isinstance(v.get("text"), str) else v


def each(v: Any, f: Callable[[dict[str, Any]], Any]) -> Any:  # draw.mjs:89
    return [f(x) if is_obj(x) else x for x in v] if isinstance(v, list) else v


# A 3D place written flat ({x, y} or [x, y]) gets z = 0; a size as {w, h, d} is [w, h, d] (two numbers stay wrong).
def vec3(v: Any, k: str) -> Any:  # draw.mjs:91-94
    a = [v["w"], v["h"], *([v["d"]] if "d" in v else [])] if is_obj(v) and "w" in v and "h" in v else as_vec(v)
    return [*a, 0] if k != "size" and isinstance(a, list) and len(a) == 2 and all(is_num(n) for n in a) else a


def vecs(o: dict[str, Any], keys: list[str]) -> dict[str, Any]:  # draw.mjs:95
    return {k: (vec3(v, k) if k in keys else v) for k, v in o.items()}


# Lists and places sent as JSON text ("[{…}]"), as DeepSeek does, are read as what they say.
SHAPED = {"at", "to", "tie", "points", "items", "branches", "sources", "x_range", "y_range", "plots", "dots", "keys", "events", "parts",
  "nodes", "links", "columns", "rows", "bars", "labels", "shade", "pins", "routes", "steps", "vertices", "lines", "angles", "circles", "questions", "action", "marks", "beats", "edit"}  # draw.mjs:97-98
_JSONISH = re.compile(r"^\s*[\[{]")


def unjson(v: Any) -> Any:  # draw.mjs:99
    if not isinstance(v, str) or not _JSONISH.search(v):
        return v
    try:
        return json.loads(v)
    except ValueError:
        return v


def parsed(o: dict[str, Any]) -> dict[str, Any]:  # draw.mjs:100
    return {k: (unjson(v) if k in SHAPED else v) for k, v in o.items()}


def _has_key(o: dict[str, Any], c: Any) -> bool:
    """`c in o` de JS: la clave se convierte a texto."""
    return js_str(c) in o


def fix_shapes(m: dict[str, Any]) -> dict[str, Any]:  # draw.mjs:101-114
    out = parsed(m)
    for k in ("x_range", "y_range"):
        if k in out:
            out[k] = as_vec(out[k])
    if "points" in out:
        out["points"] = as_vecs(out["points"])
    if "plots" in out:
        out["plots"] = each(out["plots"], lambda p: {**p, **({"points": as_vecs(p["points"])} if "points" in p else {})})
    if "parts" in out:
        out["parts"] = each(out["parts"], lambda p: {**vecs(p, ["at", "size", "rot"]), **({"motion": vecs(p["motion"], ["around", "to"])} if is_obj(p.get("motion")) else {})})
    if isinstance(out.get("items"), list):
        out["items"] = [as_text(x) for x in out["items"]]
    if "branches" in out:
        out["branches"] = each(out["branches"], lambda b: ({**b, "items": [as_text(x) for x in b["items"]]} if isinstance(b.get("items"), list) else b))
    if isinstance(out.get("rows"), list):
        cols = out["columns"] if isinstance(out.get("columns"), list) else []
        out["rows"] = [
            r if not is_obj(r)
            else [r[js_str(c)] for c in cols] if len(cols) and all(_has_key(r, c) for c in cols)
            else list(r.values())
            for r in out["rows"]
        ]
    return out


def tidy_mark(m: Any) -> Any:  # draw.mjs:115-127
    # A bare string is a kind on its own ("check"): some models send that.
    if isinstance(m, str) and js_trim(m):
        return {"kind": js_trim(m)}
    if not is_obj(m):
        return m
    # at, to and tie given as words are a text place.
    for k in ("at", "to", "tie"):
        if isinstance(m.get(k), str) and js_trim(m[k]):
            m = {**m, k: {"text": js_trim(m[k])}}
    # An empty field (text: "") is one left out, not a mistake to send back.
    if any(isinstance(v, str) and v == "" for v in m.values()):
        m = {k: v for k, v in m.items() if not (isinstance(v, str) and v == "")}
    m = fix_shapes(m)
    if m.get("kind") == "button" and not truthy(m.get("text")) and isinstance(m.get("label"), str):
        return {**m, "text": m["label"]}
    if m.get("kind") == "card" and not truthy(m.get("text")) and not truthy(m.get("heading")) and isinstance(m.get("title"), str):
        return {**m, "heading": m["title"]}
    return m


def tidy_beat(b: Any) -> Any:  # draw.mjs:128-139
    if not is_obj(b):
        return b
    b = parsed(b)
    extra = loose(b, BEAT_KEYS)
    marks = b["marks"] if b.get("marks") is not None else []
    if len(extra) and isinstance(marks, list):
        if not len(marks) and truthy(extra.get("kind")):
            marks = [extra]
        elif len(marks) == 1 and is_obj(marks[0]) and (not truthy(extra.get("kind")) or extra.get("kind") == marks[0].get("kind")):
            marks = [{**extra, **marks[0]}]
    # No line to say (#117): it draws without a caption instead of the whole drawing failing.
    return {**b, "say": b["say"] if isinstance(b.get("say"), str) else "", "marks": [tidy_mark(x) for x in marks] if isinstance(marks, list) else marks}


# ---------------------------------------------------------------- draw.mjs:140-148
# Reading a card (#143): a deep explanation closes each card as the next opens, so a card stays at least as long as its
# words take to read, about 200 a minute, between 3 and 30 seconds. Names, places and settings aren't read.
NOT_READ = {"kind", "tone", "card_size", "at", "part", "id", "url", "link", "photo", "image", "icon", "query", "smiles", "points", "tie", "action", "color", "side"}  # draw.mjs:142
_WS_SPLIT = re.compile(r"\s+")


def words_in(v: Any, key: str = "") -> int:  # draw.mjs:143-144
    if key in NOT_READ:
        return 0
    if isinstance(v, str):
        return len([w for w in _WS_SPLIT.split(v) if w])
    if isinstance(v, list):
        return sum(words_in(x) for x in v)
    if isinstance(v, dict):
        return sum(words_in(x, k) for k, x in v.items())
    return 0


def read_secs(marks: list[Any] | None) -> int:  # draw.mjs:145-148
    words = sum(words_in(m) for m in (marks if marks is not None else []) if _get(m, "kind") in CARDS)
    return min(30, max(3, js_round(words / 3.3))) if words else 0


def tidy_draw(a: Any) -> Any:  # draw.mjs:149-159
    if is_obj(a):
        a = parsed(a)
    # A lone mark sent as the whole call, with no beats (DeepSeek).
    if is_obj(a) and "beats" not in a and not truthy(a.get("edit")) and isinstance(a.get("kind"), str):
        a = {**a, "beats": [{"marks": []}]}
    if not is_obj(a) or not isinstance(a.get("beats"), list):
        return a
    extra = loose(a, CALL_KEYS)
    beats = [{**extra, **a["beats"][0]}] if len(extra) and len(a["beats"]) == 1 and is_obj(a["beats"][0]) else a["beats"]
    # The line on the call instead of its first beat.
    if isinstance(a.get("say"), str) and beats and is_obj(beats[0]) and not isinstance(beats[0].get("say"), str):
        beats = [{**beats[0], "say": a["say"]}, *beats[1:]]
    return {**a, "beats": [tidy_beat(b) for b in beats]}


# draw.mjs:160-168: `Beat`, `Edit` y `DrawArgs` (zod) están en contracts/floating/draw_args.schema.json.


def draw_model_schema(lean: dict[str, Any]) -> dict[str, Any]:  # draw.mjs:170-179
    """What the model is shown of draw, from its lean schema: every field and type, but a card's list items (bars, nodes,
    parts …) only as objects with their counts; their fields are in draw's description."""
    marks = lean["properties"]["beats"]["items"]["properties"]["marks"]["items"]["properties"]
    # Places (at, to, tie) keep their fields: shown only as objects, Claude tied cards to guessed pixels.
    # additionalProperties says the items take any fields: OpenAI's strict mode can't, so draw goes to it non-strict
    # (a bare object became one with no fields allowed, and OpenAI refused every request, #156).
    for k, p in list(marks.items()):
        if p.get("type") == "array" and _get(p.get("items"), "type") == "object":
            marks[k] = {"type": "array", "items": {"type": "object", "additionalProperties": True},
                        **({"minItems": p["minItems"]} if truthy(p.get("minItems")) else {}),
                        **({"maxItems": p["maxItems"]} if truthy(p.get("maxItems")) else {})}
    return lean


# ---------------------------------------------------------------- draw.mjs:181-226
def has_at(t: Any) -> bool:  # draw.mjs:181
    return truthy(t) and is_obj(t) and (t.get("text") is not None or t.get("id") is not None or (t.get("x") is not None and t.get("y") is not None))


def check_draw(args: dict[str, Any]) -> list[str]:  # draw.mjs:182-226
    """Everything wrong with a draw call that the schema can't say, as lines for the model; [] when it's fine."""
    out: list[str] = []
    beats = args.get("beats") if args.get("beats") is not None else []
    edits = args.get("edit") if args.get("edit") is not None else []
    if not len(beats) and not len(edits):
        out.append("Give beats to draw, or edit to change what is drawn.")
    for i, b in enumerate(beats):
        if not js_trim(b["say"]) and not len(b["marks"]):
            out.append(f"beat {i + 1}: needs say or marks.")
        for j, m in enumerate(b["marks"]):
            kind = m.get("kind")
            where = f"beat {i + 1} mark {j + 1} ({js_str(kind)})"

            def need(ok: Any, what: str, where: str = where) -> None:
                if not truthy(ok):
                    out.append(f"{where}: needs {what}.")

            if kind in PATHS:
                need(_ge(_len(m.get("points")), 2) or has_at(m.get("at")), "points ([x, y] screenshot pixels, at least 2) or at")
            elif kind == "connect":
                need(has_at(m.get("at")), "at")
                need(has_at(m.get("to")), "to")
            elif kind in SCREEN:
                need(has_at(m.get("at")), "at (text, id, or x and y)")
            if kind in ("label", "write"):
                need(truthy(m.get("text")) or truthy(m.get("label")), "text")
            if kind == "emote":
                need(m.get("name") in EMOTES, f"name, one of {', '.join(EMOTES)}")
            if kind == "sfx":
                need(m.get("name") in SOUNDS, f"name, one of {', '.join(SOUNDS)}")
            if kind == "type":
                need(has_at(m.get("at")), "at (the field)")
                need(m.get("text"), "text")
            if kind == "copy":
                need(m.get("text"), "text")
            if kind == "open":
                need(m.get("url"), "url")
            if kind == "button":
                need(truthy(m.get("text")) and u16len(js_str(m["text"])) <= 40, "text (under 40 characters)")
                need(m.get("action"), "action ({do: ask|open|copy, value})")
            if kind == "card":
                need(truthy(m.get("text")) or truthy(m.get("heading")), "text or heading")
            if kind == "note":
                need(m.get("text"), "text")
            if kind == "list":
                need(_len(m.get("items")), "items")
            if kind == "clip":
                need(truthy(m.get("title")) and truthy(m.get("text")), "title and text")
            if kind == "sources":
                need(_len(m.get("sources")), "sources")
            if kind == "photo":
                need(truthy(m.get("query")) or truthy(m.get("url")), "query (a thing with a Wikipedia page) or url")
            if kind == "scroll" and m.get("dir") == "right":
                out.append(f"{where}: dir for scroll is up or down.")
            # The kinds with a structure of their own: each says what is wrong in words the model can fix.
            more = CHECKS.get(kind) if isinstance(kind, str) else None
            if more is None:
                more = CHECKS["labels"] if kind == "photo" and truthy(m.get("labels")) else None
            if more:
                out.extend(f"{where}: {s}" for s in more(m))
            if kind == "graph":
                need(truthy(_len(m.get("plots"))) or truthy(_len(m.get("dots"))), "plots or dots")
            if kind == "mindmap":
                need(_ge(_len(m.get("branches")), 2), "branches (at least 2, each {text, items})")
            if kind == "legend":
                need(_len(m.get("keys")), "keys")
            if kind == "timeline":
                need(_ge(_len(m.get("events")), 2), "events (at least 2)")
            if kind == "molecule":
                need(m.get("smiles"), "smiles")
                if truthy(m.get("smiles")):
                    try:
                        parse_smiles(m["smiles"])
                    except ValueError as e:
                        out.append(f"{where}: {e}")
            if kind == "ticket":
                need(m.get("title"), "title")
            if kind == "medal":
                need(m.get("text"), "text")
        if truthy(b.get("wait")) and not any(mk.get("kind") in SCREEN and has_at(mk.get("at")) for mk in b["marks"]):
            out.append(f"beat {i + 1}: wait needs a mark on the thing to {js_str(b['wait'])} (a target or hover with at).")
    for i, e in enumerate(edits):
        if e.get("do") != "clear" and not truthy(e.get("part")):
            out.append(f"edit {i + 1} ({js_str(e.get('do'))}): needs part (an id like p3).")
        if e.get("do") == "recolor" and not truthy(e.get("tone")):
            out.append(f"edit {i + 1}: recolor needs tone.")
        if e.get("do") == "move" and e.get("dx") is None and e.get("dy") is None:
            out.append(f"edit {i + 1}: move needs dx or dy (screen points).")
    return out


# ---------------------------------------------------------------- draw.mjs:228-322
def quoted(lst: Iterable[Any]) -> str:  # draw.mjs:228
    return ", ".join(f'"{js_str(s)}"' for s in lst)


# The closest id, when a model writes "node-1" for "node1" or drops a character: a suggestion, never a substitution.
def clean_id(s: Any) -> str:  # draw.mjs:230
    return re.sub(r"[^a-z0-9]", "", js_str(s if s is not None else "").lower())


def near_id(id_: Any, ids: list[Any]) -> Any:  # draw.mjs:231-241
    c = clean_id(id_)
    if not c:
        return None
    best, bd = None, math.inf
    for k in ids:
        d = edit_distance(c, clean_id(k))
        if d < bd:
            bd = d
            best = k
    max_ = 0 if len(c) <= 2 else max(1, math.floor(len(c) / 3))
    return best if truthy(best) and best != id_ and bd <= max_ else None


# Ids that must be there and be different: nodes of a flow, vertices of a figure.
def id_problems(lst: list[dict[str, Any]], what: str) -> list[str]:  # draw.mjs:243-247
    seen: set[Any] = set()
    out: list[str] = []
    for n in lst:
        key = js_str(n.get("id"))
        if key in seen:
            out.append(f'two {what} share the id "{key}"; give each its own.')
        seen.add(key)
    return out


def _check_model(m: dict[str, Any]) -> list[str]:  # draw.mjs:249-259
    if not truthy(_len(m.get("parts"))):
        return ["needs parts."]
    out: list[str] = []
    for k, p in enumerate(m["parts"]):
        mo = p.get("motion")
        who = f"part {k + 1}" + (f" ({js_str(p.get('label'))})" if truthy(p.get("label")) else "")
        if not truthy(mo):
            continue
        if mo.get("do") == "slide" and not truthy(mo.get("to")):
            out.append(f"{who}: slide needs to ([x, y, z]: where it slides to and back from at).")
        secs = mo.get("secs")
        if secs is not None and not (secs >= 0.3 and secs <= 60):
            out.append(f"{who}: secs (one full cycle) must be between 0.3 and 60.")
    return out


def _check_table(m: dict[str, Any]) -> list[str]:  # draw.mjs:261-267
    cols = _len(m.get("columns"))
    cols = cols if cols is not None else 0
    out: list[str] = []
    if cols < 2:
        out.append("needs columns (2 to 6 headings).")
    if not truthy(_len(m.get("rows"))):
        out.append("needs rows (each a list of cells, one per column).")
    if cols >= 2:
        for k, r in enumerate(m.get("rows") if m.get("rows") is not None else []):
            if len(r) != cols:
                out.append(f'row {k + 1} has {len(r)} cell{"" if len(r) == 1 else "s"} but there are {cols} columns; give every row one cell per column ("" for an empty one).')
    return out


def _is_finite(v: Any) -> bool:
    """`Number.isFinite`."""
    return is_num(v) and math.isfinite(v)


def _check_bars(m: dict[str, Any]) -> list[str]:  # draw.mjs:268-274
    if not _ge(_len(m.get("bars")), 2):
        return ["needs bars (at least 2, each {label, value})."]
    out: list[str] = []
    for k, b in enumerate(m["bars"]):
        if not _is_finite(b.get("value")) or b["value"] < 0:
            out.append(f'bar {k + 1} ("{js_str(b.get("label"))}"): value must be 0 or more (for values below zero use graph).')
    if not out and not any(is_num(b.get("value")) and b["value"] > 0 for b in m["bars"]):
        out.append("every value is 0; at least one bar needs a value above 0.")
    return out


def _check_labels(m: dict[str, Any]) -> list[str]:  # draw.mjs:275-279
    out: list[str] = []
    for k, lb in enumerate(m["labels"]):
        x, y = lb.get("x"), lb.get("y")
        if not (is_num(x) and is_num(y) and x >= 0 and x <= 1 and y >= 0 and y <= 1):
            out.append(f'label {k + 1} ("{js_str(lb.get("text"))}"): x and y are fractions of the picture from its top left (0 to 1), not pixels.')
    return out


def _check_map(m: dict[str, Any]) -> list[str]:  # draw.mjs:280-287
    out: list[str] = []
    pins = m.get("pins") if m.get("pins") is not None else []
    if not truthy(m.get("region")) and not truthy(_len(m.get("shade"))) and not len(pins):
        return ["needs region, shade (countries to colour in) or pins."]
    for p in pins:
        if not (abs(p["lat"]) <= 90 and abs(p["lon"]) <= 180):
            out.append(f'pin "{js_str(p.get("name"))}": lat must be between -90 and 90 and lon between -180 and 180 (south and west are negative).')
    for k, r in enumerate(m.get("routes") if m.get("routes") is not None else []):
        for end in (r.get("from"), r.get("to")):
            if not any(p.get("name") == end for p in pins):
                tail = f" (pins: {quoted(p.get('name') for p in pins)})" if len(pins) else " (routes run between pins: add pins with name, lat, lon)"
                out.append(f'route {k + 1}: no pin is named "{js_str(end)}"{tail}.')
    try:
        resolve_region(m)
    except ValueError as e:
        out.append(str(e))
    return out


def _check_math(m: dict[str, Any]) -> list[str]:  # draw.mjs:288-293
    if not truthy(_len(m.get("steps"))):
        return ["needs steps (each {tex, note})."]
    out: list[str] = []
    for k, s in enumerate(m["steps"]):
        try:
            parse_tex(s.get("tex"))
        except ValueError as e:
            out.append(f"step {k + 1}: {e}")
    return out


def _check_geometry(m: dict[str, Any]) -> list[str]:  # draw.mjs:294-310
    vs = m.get("vertices") if m.get("vertices") is not None else []
    ids = list(dict.fromkeys(v.get("id") for v in vs))  # new Set(...): ordenado por inserción
    if len(vs) < 2:
        return ["needs vertices (at least 2, each {id, x, y} in your own units, y up)."]
    out = id_problems(vs, "vertices")

    def known(id_: Any, who: str) -> None:
        if id_ in ids:
            return
        s = near_id(id_, ids)
        nospace = re.sub(r"\s+", "", js_str(id_))
        if re.search(r"\s", js_str(id_)) and nospace in ids:
            why = f""" (ids can't contain spaces; write "{nospace}")"""
        elif truthy(s):
            why = f'; did you mean "{js_str(s)}"'
        else:
            why = ""
        out.append(f'{who}: no vertex has the id "{js_str(id_)}"{why} (vertices: {quoted(ids)}).')

    if not truthy(_len(m.get("lines"))) and not truthy(_len(m.get("circles"))):
        out.append("needs lines ({from, to}) or circles ({at, r}) between its vertices.")
    for k, ln in enumerate(m.get("lines") if m.get("lines") is not None else []):
        known(ln.get("from"), f"line {k + 1}")
        known(ln.get("to"), f"line {k + 1}")
        if ln.get("from") == ln.get("to"):
            out.append(f'line {k + 1} goes from "{js_str(ln.get("from"))}" to itself.')
    for k, a in enumerate(m.get("angles") if m.get("angles") is not None else []):
        for id_ in (a.get("at"), a.get("from"), a.get("to")):
            known(id_, f"angle {k + 1}")
        if a.get("at") == a.get("from") or a.get("at") == a.get("to") or a.get("from") == a.get("to"):
            out.append(f"angle {k + 1}: at (its corner), from and to (a point on each arm) must be three different vertices.")
    for k, c in enumerate(m.get("circles") if m.get("circles") is not None else []):
        known(c.get("at"), f"circle {k + 1}")
        if not (is_num(c.get("r")) and c["r"] > 0):
            out.append(f"circle {k + 1}: r must be above 0 (in the same units as the vertices).")
    if all(v.get("x") == vs[0].get("x") and v.get("y") == vs[0].get("y") for v in vs):
        out.append("every vertex is at the same place.")
    return out


def _check_quiz(m: dict[str, Any]) -> list[str]:  # draw.mjs:311-320
    if not truthy(_len(m.get("questions"))):
        return ["needs questions (each {text, options, answer, explain})."]
    out: list[str] = []
    for k, q in enumerate(m["questions"]):
        opts = [same_text(o) for o in q["options"]]
        if len(set(opts)) != len(opts):
            out.append(f"question {k + 1}: two options are the same.")
        if same_text(q.get("answer")) not in opts:
            out.append(f"question {k + 1}: answer must be one of its options, word for word (options: {quoted(q['options'])}).")
    return out


CHECKS: dict[str, Callable[[dict[str, Any]], list[str]]] = {  # draw.mjs:248-321
    "model": _check_model,
    "flow": lambda m: check_flow(m),
    "table": _check_table,
    "bars": _check_bars,
    "labels": _check_labels,
    "map": _check_map,
    "math": _check_math,
    "geometry": _check_geometry,
    "quiz": _check_quiz,
}


def same_text(s: Any) -> str:  # draw.mjs:322
    return re.sub(r"\s+", " ", js_trim(js_str(s))).lower()


# draw.mjs:324-428 (where marks go): no se porta salvo las líneas 416-421, en `enrich_mark`.
def enrich_mark(m: dict[str, Any]) -> dict[str, Any]:
    """draw.mjs:416-421: lo que llega ya calculado al overlay (molécula, capas del flujo, mapa, árboles de LaTeX y la
    respuesta del quiz). `m` ya pasó `check_draw`. Devuelve una copia."""
    o = dict(m)
    kind = m.get("kind")
    if kind == "molecule":
        o["mol"] = parse_smiles(m["smiles"])  # draw.mjs:416
    # The rest arrive already worked out, like a molecule: the overlay only lays them out.
    if kind == "flow":
        o["lay"] = flow_layers(m["nodes"], m["links"])  # draw.mjs:418
    if kind == "map":
        o.update(resolve_region(m))  # draw.mjs:419
    if kind == "math":
        o["steps"] = [{**s, "tree": parse_tex(s["tex"])} for s in m["steps"]]  # draw.mjs:420
    if kind == "quiz":  # draw.mjs:421
        o["questions"] = []
        for q in m["questions"]:
            opts = [same_text(x) for x in q["options"]]
            a = same_text(q["answer"])
            o["questions"].append({**q, "right": opts.index(a) if a in opts else -1})
    return o


# ---------------------------------------------------------------- draw.mjs:430-527 parts drawn so far
def quote(s: Any) -> str:  # draw.mjs:431
    return "“" + u16slice(_WS_SPLIT.sub(" ", js_str(s)), 40) + "”"


def part_desc(m: dict[str, Any]) -> str:  # draw.mjs:432-437
    """What a mark is, in a few words, for the tool result: ring “Export”, card “Compound interest”."""
    words = _coalesce(
        lambda: m.get("label"), lambda: m.get("title"), lambda: m.get("heading"), lambda: _get(m.get("at"), "name"),
        lambda: m.get("text"), lambda: m.get("query"), lambda: m.get("smiles"), lambda: m.get("region"),
        lambda: _get(_first(m.get("nodes")), "text"),
        lambda: ", ".join("" if c is None else js_str(c) for c in m["columns"]) if isinstance(m.get("columns"), list) else None,
        lambda: _get(_first(m.get("bars")), "label"), lambda: _get(_first(m.get("steps")), "tex"),
        lambda: _get(_first(m.get("questions")), "text"), lambda: _get(_first(m.get("shade")), "name"),
        lambda: _get(_first(m.get("pins")), "name"),
        lambda: "".join(js_str(_get(v, "id")) if _get(v, "id") is not None else "" for v in m["vertices"]) if isinstance(m.get("vertices"), list) else None,
        lambda: "",
    )
    return f"{js_str(m.get('kind'))}{f' {quote(words)}' if truthy(words) else ''}"


# draw.mjs:438-490 (quizNote, createLists): no se portan.

SILENT = {"emote", "sfx", "copy", "open", "handoff"}  # draw.mjs:491


class Parts:  # draw.mjs:492-525
    """The parts on screen: ids never reused in a conversation, screen marks cleared on their own, cards until closed."""

    def __init__(self) -> None:
        self._all: dict[str, dict[str, Any]] = {}
        self._n = 0

    def assign(self, beats: list[dict[str, Any]]) -> list[str]:  # draw.mjs:497-507
        """Gives every drawn mark in these beats an id (part) and returns the new ids."""
        ids: list[str] = []
        for b in beats:
            for m in b["marks"]:
                if m.get("kind") in SILENT:
                    continue
                self._n += 1
                m["part"] = f"p{self._n}"
                self._all[m["part"]] = {"kind": m.get("kind"), "desc": part_desc(m),
                                        "screen": m.get("kind") in SCREEN or m.get("kind") == "type" or (m.get("kind") == "button" and truthy(m.get("at")))}
                ids.append(m["part"])
        return ids

    def has(self, id_: str) -> bool:  # draw.mjs:508
        return id_ in self._all

    def get(self, id_: str) -> dict[str, Any] | None:  # draw.mjs:509
        return self._all.get(id_)

    def remove(self, id_: str) -> None:  # draw.mjs:510
        self._all.pop(id_, None)

    def clear(self, keep: Callable[[str], bool] = lambda _id: False) -> None:  # draw.mjs:511-512
        """keep(id): parts that stay (a card the user pinned)."""
        for id_ in list(self._all):
            if not keep(id_):
                del self._all[id_]

    def clear_screen(self) -> None:  # draw.mjs:513
        for id_, p in list(self._all.items()):
            if p["screen"]:
                del self._all[id_]

    def trim_cards(self, max_: int, skip: Callable[[str], bool] = lambda _id: False) -> list[str]:  # draw.mjs:514-520
        """Only `max` cards stay up at once (the overlay closes the oldest as each new one is drawn): forgets the older
        ones and returns their ids. skip(id): cards that don't count (a drawing that goes by itself)."""
        cards = [id_ for id_, p in self._all.items() if p["kind"] in CARDS and not skip(id_)]
        gone = cards[: max(0, len(cards) - max_)]
        for id_ in gone:
            del self._all[id_]
        return gone

    @property
    def screen_count(self) -> int:  # draw.mjs:521
        return len([p for p in self._all.values() if p["screen"]])

    @property
    def ids(self) -> list[str]:  # draw.mjs:522
        return list(self._all)

    def describe(self, ids: list[str] | None = None) -> str:  # draw.mjs:523
        ids = list(self._all) if ids is None else ids
        return describe_parts([(id_, self._all[id_]) for id_ in ids if self._all.get(id_)])


def create_parts() -> Parts:  # draw.mjs:493
    return Parts()


def describe_parts(entries: list[tuple[str, dict[str, Any]]]) -> str:  # draw.mjs:526-527
    """"p1 ring “Export”, p2 card “Interest”" — the ids the model edits with."""
    return ", ".join(f"{id_} {p['desc']}" for id_, p in entries)


# draw.mjs:529-608 (photos and favicons): no se portan; en v1 el backend no descarga nada (CONTRACT §9.1).


# ---------------------------------------------------------------- draw.mjs:610-677 SMILES (a small, strict subset)
ORGANIC = ["Cl", "Br", "B", "C", "N", "O", "P", "S", "F", "I"]  # draw.mjs:611
AROMATIC = ["b", "c", "n", "o", "p", "s"]  # draw.mjs:612
VALENCE: dict[str, list[int]] = {"B": [3], "C": [4], "N": [3, 5], "O": [2], "P": [3, 5], "S": [2, 4, 6], "F": [1], "Cl": [1], "Br": [1], "I": [1]}  # draw.mjs:613
_BRACKET_RE = re.compile(r"([A-Z][a-z]?|se|as|[bcnops])(H[0-9]?)?([+-][0-9]?|\+\+|--)?")
_BOND = {"-": 1, "=": 2, "#": 3, ":": 1.5}


def parse_smiles(s: Any) -> dict[str, Any]:  # draw.mjs:614-677
    """Atoms (element, aromatic, charge, hydrogens) and bonds (order 1, 2, 3 or 1.5 aromatic) from a SMILES string.
    Supports organic-subset and bracket atoms ([NH4+], [O-], [nH], [Fe+2]), = # : - bonds, branches and ring
    closures (1-9, %10-%99). Anything else (chirality, / \\, dots, isotopes) is refused with a reason."""
    st = js_trim(js_str(s if s is not None else ""))
    if not st:
        raise ValueError("The SMILES is empty.")
    atoms: list[dict[str, Any]] = []
    bonds: list[dict[str, Any]] = []
    stack: list[int] = []
    rings: dict[int, dict[str, Any]] = {}
    prev: int | None = None
    bond: float | None = None
    i = 0

    def fail(why: str) -> None:
        raise ValueError(f"""Can't read SMILES "{u16slice(st, 40)}" at {i + 1}: {why}.""")

    def add_atom(a: dict[str, Any]) -> None:
        nonlocal prev, bond
        if len(atoms) >= LIMITS["atoms"]:
            fail(f"more than {LIMITS['atoms']} atoms")
        atoms.append(a)
        k = len(atoms) - 1
        if prev is not None:
            bonds.append({"a": prev, "b": k, "order": bond if bond is not None else (1.5 if a["arom"] and atoms[prev]["arom"] else 1)})
        prev = k
        bond = None

    while i < len(st):
        ch = st[i]
        if ch == "(":
            if prev is None:
                fail("a branch before any atom")
            stack.append(prev)  # type: ignore[arg-type]
            i += 1
            continue
        if ch == ")":
            if not stack:
                fail("a ) without its (")
            prev = stack.pop()
            i += 1
            continue
        if ch in ("-", "=", "#", ":"):
            if bond is not None:
                fail("two bonds in a row")
            bond = _BOND[ch]
            i += 1
            continue
        if ch in "0123456789%":
            if prev is None:
                fail("a ring number before any atom")
            if ch == "%":
                mm = re.match(r"%([0-9][0-9])", st[i:])
                if not mm:
                    fail("% needs two digits")
                n = int(mm[1])  # type: ignore[index]
                i += 3
            else:
                n = int(ch)
                i += 1
            if n in rings:
                o = rings.pop(n)
                if o["at"] == prev:
                    fail("a ring closing on itself")
                order = bond if bond is not None else o["bond"] if o["bond"] is not None else (1.5 if atoms[o["at"]]["arom"] and atoms[prev]["arom"] else 1)  # type: ignore[index]
                bonds.append({"a": o["at"], "b": prev, "order": order})
                bond = None
            else:
                rings[n] = {"at": prev, "bond": bond}
                bond = None
            continue
        if ch == "[":
            end = st.find("]", i)
            if end < 0:
                fail("a [ without its ]")
            mm = _BRACKET_RE.fullmatch(st[i + 1 : end])
            if not mm:
                fail(f'"[{st[i + 1 : end]}]" is not a supported bracket atom (no isotopes or chirality)')
            assert mm is not None
            arom = bool(re.match(r"[a-z]", mm[1]))
            el = mm[1][0].upper() + mm[1][1:] if arom else mm[1]
            h = (int(mm[2][1:]) if len(mm[2]) > 1 else 1) if mm[2] else 0
            c = (2 if mm[3] == "++" else -2 if mm[3] == "--" else (1 if mm[3][0] == "+" else -1) * (int(mm[3][1:]) if len(mm[3]) > 1 else 1)) if mm[3] else 0
            add_atom({"el": el, "arom": arom, "charge": c, "h": h, "bracket": True})
            i = end + 1
            continue
        org = next((e for e in ORGANIC if st.startswith(e, i)), None)
        if org:
            add_atom({"el": org, "arom": False, "charge": 0, "h": None})
            i += len(org)
            continue
        if ch in AROMATIC:
            add_atom({"el": ch.upper(), "arom": True, "charge": 0, "h": None})
            i += 1
            continue
        fail(f'"{ch}" is not supported')
    if stack:
        fail("a ( without its )")
    if rings:
        fail(f"ring {next(iter(rings))} is never closed")
    if bond is not None:
        fail("a bond with nothing after it")
    # Implicit hydrogens for organic-subset atoms: the smallest normal valence that fits, minus the bonds.
    for k, a in enumerate(atoms):
        if a["h"] is not None:
            continue
        # Aromatic n, o, s, p carry no implicit hydrogen (pyrrole's is written [nH]); an aromatic bond counts once, plus
        # one for the ring's shared double bond.
        if a["arom"] and a["el"] != "C" and a["el"] != "B":
            a["h"] = 0
            continue
        mine = [b for b in bonds if b["a"] == k or b["b"] == k]
        used = sum(1 if b["order"] == 1.5 else b["order"] for b in mine) + (1 if any(b["order"] == 1.5 for b in mine) else 0)
        v = next((x for x in VALENCE.get(a["el"], [0]) if x >= used), used)
        a["h"] = max(0, v - used)
    return {"atoms": [{"el": a["el"], "arom": a["arom"], "charge": a["charge"], "h": a["h"]} for a in atoms], "bonds": bonds}


# ---------------------------------------------------------------- draw.mjs:679-746 flow diagrams
def check_flow(m: dict[str, Any]) -> list[str]:  # draw.mjs:680-695
    """What's wrong with a flow's nodes and links, as lines; [] when it's fine."""
    nodes = m.get("nodes") if m.get("nodes") is not None else []
    links = m.get("links") if m.get("links") is not None else []
    ids = list(dict.fromkeys(n.get("id") for n in nodes))
    if len(nodes) < 2:
        return ["needs nodes (at least 2, each {id, text})."]
    out = id_problems(nodes, "nodes")
    if not len(links):
        out.append("needs links (each {from, to}: the ids of two nodes).")
    if m.get("dir") == "up":
        out.append("dir for a flow is down or right.")
    for k, ln in enumerate(links):
        for end in (ln.get("from"), ln.get("to")):
            if end not in ids:
                s = near_id(end, ids)
                hint = f'; did you mean "{js_str(s)}"' if truthy(s) else ""
                out.append(f'link {k + 1}: no node has the id "{js_str(end)}"{hint} (nodes: {quoted(ids)}).')
        if ln.get("from") == ln.get("to"):
            out.append(f'link {k + 1} goes from "{js_str(ln.get("from"))}" to itself.')
    return out


def flow_layers(nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> dict[str, Any]:  # draw.mjs:696-746
    """Layers for a checked flow, top to bottom (or left to right): { layers: [[id …] …], via: { link index: [id …] },
    back: [link index …] }. A link that closes a loop (back) is turned round for layering, so the rest still reads one
    way; a link that skips layers passes through a placeholder ("~3.1") in each one, listed in via, so it gets its own
    lane instead of running under the nodes between. Nodes in a layer are ordered to keep links from crossing."""
    ids = [n["id"] for n in nodes]
    out: dict[Any, list[dict[str, Any]]] = {id_: [] for id_ in ids}
    edges = [e for e in ({"k": k, "a": ln["from"], "b": ln["to"]} for k, ln in enumerate(links)) if e["a"] != e["b"] and e["a"] in out and e["b"] in out]
    for e in edges:
        out[e["a"]].append(e)
    state: dict[Any, int] = {}
    back: dict[int, None] = {}  # Set ordenado por inserción

    def visit(id_: Any) -> None:
        state[id_] = 1
        for e in out[id_]:
            st = state.get(e["b"])
            if st == 1:
                back[e["k"]] = None
            elif not st:
                visit(e["b"])
        state[id_] = 2

    fed = {e["b"] for e in edges}
    for id_ in [*[x for x in ids if x not in fed], *ids]:
        if not state.get(id_):
            visit(id_)
    dag = [({"k": e["k"], "a": e["b"], "b": e["a"]} if e["k"] in back else e) for e in edges]
    # Each node as far down as its longest chain of links puts it; then a start with nothing above moves next to what it feeds.
    rank: dict[Any, int] = {id_: 0 for id_ in ids}
    for _pass in range(len(ids)):
        moved = False
        for e in dag:
            if rank[e["b"]] < rank[e["a"]] + 1:
                rank[e["b"]] = rank[e["a"]] + 1
                moved = True
        if not moved:
            break
    into = {e["b"] for e in dag}
    for id_ in ids:
        if id_ in into:
            continue
        kids = [rank[e["b"]] for e in dag if e["a"] == id_]
        if kids:
            rank[id_] = min(kids) - 1
    depth = (max(rank.values()) + 1) if rank else 0
    layers: list[list[Any]] = [[] for _ in range(depth)]
    via: dict[str, list[str]] = {}
    segs: list[tuple[Any, Any]] = []
    for id_ in ids:
        layers[rank[id_]].append(id_)
    for e in dag:
        chain = [e["a"]]
        for r in range(rank[e["a"]] + 1, rank[e["b"]]):
            d = f"~{e['k']}.{r}"
            layers[r].append(d)
            chain.append(d)
        chain.append(e["b"])
        if len(chain) > 2:
            via[str(e["k"])] = chain[1:-1]  # clave de objeto JS: texto
        for j in range(1, len(chain)):
            segs.append((chain[j - 1], chain[j]))
    # Fewer crossings: each layer sorted by where its neighbours sit in the layer before, down then up, a few times.
    pos: dict[Any, int] = {}

    def index() -> None:
        for lyr in layers:
            for j, id_ in enumerate(lyr):
                pos[id_] = j

    index()
    for sweep in range(4):
        down = sweep % 2 == 0
        r = 1 if down else depth - 2
        while (r < depth) if down else (r >= 0):
            near = set(layers[r + (-1 if down else 1)])

            def mid(id_: Any, near: set[Any] = near, down: bool = down) -> float:
                ns = [pos[a if down else b] for (a, b) in segs if ((b == id_ and a in near) if down else (a == id_ and b in near))]
                return sum(ns) / len(ns) if ns else pos[id_]

            want = {id_: mid(id_) for id_ in layers[r]}
            layers[r].sort(key=cmp_to_key(lambda a, b, want=want: (want[a] - want[b]) or (pos[a] - pos[b])))
            index()
            r += 1 if down else -1
    return {"layers": layers, "via": via, "back": list(back)}


# ---------------------------------------------------------------- draw.mjs:748-804 maps: countries and regions by name
COUNTRIES: list[dict[str, Any]] = json.loads((Path(__file__).with_name("countries.json")).read_text(encoding="utf-8"))
"""countries.mjs: Natural Earth 110m admin-0 countries, public domain (naturalearthdata.com). n: name, c: continent,
b: [west, south, east, north], at: [lon, lat] of its name, a: other names (lower case, no accents)."""

REGIONS: dict[str, list[float]] = {  # draw.mjs:749-754
  "world": [-169, -56, 180, 82], "africa": [-20, -36, 53, 38], "europe": [-25, 34, 45, 72], "asia": [25, -11, 180, 78], "north america": [-168, 7, -20, 84],
  "south america": [-82, -56, -34, 13], "oceania": [110, -48, 180, 0], "antarctica": [-180, -90, 180, -60],
  "middle east": [25, 12, 63, 42], "southeast asia": [92, -11, 141, 28], "east asia": [73, 18, 146, 54], "south asia": [60, 5, 98, 38],
  "scandinavia": [4, 54, 32, 71.5], "caribbean": [-86, 9, -59, 27], "central america": [-93, 7, -77, 19],
}
REGION_ALSO = {"australasia": "oceania", "south east asia": "southeast asia", "nordic countries": "scandinavia", "nordics": "scandinavia", "earth": "world", "globe": "world", "latin america": "south america"}  # draw.mjs:755


def norm_name(s: Any) -> str:  # draw.mjs:756
    t = re.sub("[̀-ͯ]", "", unicodedata.normalize("NFKD", js_str(s))).lower()
    t = js_trim(re.sub(r"[^a-z0-9]+", " ", t))
    return " ".join(w for w in t.split(" ") if w and w != "the")


# Places often asked for by name that are part of a country here.
PART_OF = {"england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom", "northern ireland": "United Kingdom", "alaska": "United States", "hawaii": "United States", "tibet": "China", "siberia": "Russia", "sicily": "Italy", "corsica": "France"}  # draw.mjs:758
BY_NAME: dict[str, int] = {}  # draw.mjs:759-760
for _i, _c in enumerate(COUNTRIES):
    for _k in [norm_name(_c["n"]), *_c["a"]]:
        BY_NAME[_k] = _i


def edit_distance(a: str, b: str) -> int:  # draw.mjs:761-765
    row = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        nxt = [i]
        for j in range(1, len(b) + 1):
            nxt.append(min(row[j] + 1, nxt[j - 1] + 1, row[j - 1] + (0 if a[i - 1] == b[j - 1] else 1)))
        row = nxt
    return row[len(b)]


def find_country(name: Any) -> int:  # draw.mjs:766-775
    """The country called that (any of its usual names): its index in COUNTRIES. Throws with the nearest names when
    there is none, since a country too small for this scale has no outline to draw."""
    key = norm_name(name)
    hit = BY_NAME.get(key)
    if hit is not None:
        return hit
    scored = []
    for c in COUNTRIES:
        n = norm_name(c["n"])
        scored.append((0 if (n in key or key in n) else edit_distance(key, n), c["n"]))
    near = [n for d, n in sorted((x for x in scored if len(key) >= 3 and x[0] <= max(2, math.floor(u16len(x[1]) / 3))), key=lambda x: x[0])][:3]
    whole = PART_OF.get(key)
    tail = f" (it is part of {whole}, which has one)" if whole else f" (nearest: {', '.join(near)})" if near else ""
    raise ValueError(f"""no country outline for "{u16slice(js_str(name), 40)}"{tail}. Countries only, and the very small ones aren't outlined: mark a city, a state or a small country with a pin (name, lat, lon) instead.""")


_REGION_SPLIT = re.compile(r",|;|\band\b|&", re.I | re.A)


def resolve_region(m: dict[str, Any]) -> dict[str, Any]:  # draw.mjs:776-804
    """What a map shows: { view: [west, south, east, north] in degrees (east can pass 180), shade: [{ i, name, tone, at }] }
    with i the country's index in the outlines. region: 'world', a continent or part of one, or country names (commas
    between); without it the view fits the shaded countries and the pins, with room to see what's round them."""
    shade = []
    for s in (m.get("shade") if m.get("shade") is not None else []):
        i = find_country(s.get("name"))
        shade.append({"i": i, "name": COUNTRIES[i]["n"], **({"tone": s["tone"]} if s.get("tone") is not None else {}), "at": COUNTRIES[i]["at"]})
    pins = [p for p in (m.get("pins") if m.get("pins") is not None else []) if abs(p["lat"]) <= 90 and abs(p["lon"]) <= 180]
    box: list[float] | None = None
    named = False

    def join(b: list[float]) -> None:
        nonlocal box
        box = [min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3])] if box else list(b)

    region = m.get("region")
    for piece in [p for p in (norm_name(x) for x in _REGION_SPLIT.split(js_str(region if region is not None else ""))) if p]:
        r = REGIONS.get(REGION_ALSO.get(piece, piece))
        if r:
            join(r)
            named = True
            continue
        try:
            i = find_country(piece)
        except ValueError as e:
            raise ValueError(f"region: {e} Regions by name: {', '.join(REGIONS)}.") from None
        join(COUNTRIES[i]["b"])
    fitted = box is not None
    # Pins are always in view; shaded countries too unless a region was named (a few countries coloured in on a world map).
    if not named:
        for s in shade:
            join(COUNTRIES[s["i"]]["b"])
    for p in pins:
        join([p["lon"], p["lat"], p["lon"], p["lat"]])
    if not box:
        raise ValueError("needs region, shade (countries to colour in) or pins.")
    # Room round it: a little for a named region, more for a view fitted to one country or a pin, so its neighbours show.
    w, s_, e, n = box
    pad = 0 if named else 0.12 if fitted else 0.4
    span = 0 if named else 7
    gx = max((e - w) * pad, (span - (e - w)) / 2, 0)
    gy = max((n - s_) * pad, (span - (n - s_)) / 2, 0)
    w -= gx
    e += gx
    s_ = max(-89, s_ - gy)
    n = min(89, n + gy)
    if e - w > 360:
        w, e = -180, 180

    def r1(v: float) -> float:
        return js_round(v * 10) / 10

    return {"view": [r1(w), r1(s_), r1(e), r1(n)], "shade": shade}


# ---------------------------------------------------------------- draw.mjs:806-938 maths (a small, strict subset of LaTeX)
GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "θ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω"}  # draw.mjs:807
TEX_ORD = {**GREEK, "infty": "∞", "partial": "∂", "nabla": "∇", "hbar": "ℏ", "ell": "ℓ", "degree": "°", "circ": "∘", "angle": "∠", "triangle": "△", "emptyset": "∅", "varnothing": "∅", "forall": "∀", "exists": "∃", "neg": "¬", "lnot": "¬", "prime": "′", "dots": "…", "ldots": "…", "cdots": "⋯", "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "sum": "∑", "prod": "∏", "int": "∫", "oint": "∮",
  "checkmark": "✓", "star": "⋆", "bullet": "•", "square": "□", "Box": "□", "blacksquare": "∎", "uparrow": "↑", "downarrow": "↓", "updownarrow": "↕", "colon": ":", "lbrace": "{", "rbrace": "}", "lvert": "|", "rvert": "|", "vert": "|", "backslash": "\\"}  # draw.mjs:808-809
TEX_OP = {"times": "×", "cdot": "·", "div": "÷", "pm": "±", "mp": "∓", "ast": "∗", "cup": "∪", "cap": "∩", "setminus": "∖", "land": "∧", "wedge": "∧", "lor": "∨", "vee": "∨", "oplus": "⊕"}  # draw.mjs:810
TEX_REL = {"le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "equiv": "≡", "sim": "∼", "simeq": "≃", "cong": "≅", "propto": "∝", "lt": "<", "gt": ">", "nleq": "≰", "ngeq": "≱", "doteq": "≐", "to": "→", "gets": "←", "longleftarrow": "←", "Longrightarrow": "⇒", "longleftrightarrow": "↔", "rightarrow": "→", "longrightarrow": "→", "leftarrow": "←", "leftrightarrow": "↔", "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔", "implies": "⇒", "iff": "⇔", "mapsto": "↦", "in": "∈", "notin": "∉", "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "perp": "⊥", "parallel": "∥", "ll": "≪", "gg": "≫", "therefore": "∴", "because": "∵", "mid": "∣"}  # draw.mjs:811
TEX_FN = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log", "ln", "lg", "exp", "lim", "max", "min", "det", "gcd", "mod", "deg", "arg", "sup", "inf", "Pr", "dim", "ker"}  # draw.mjs:812
TEX_SPACE = {",": 0.17, ":": 0.22, ";": 0.28, " ": 0.33, "!": 0, "quad": 1, "qquad": 2}  # draw.mjs:813
TEX_OVER = {"vec": "vec", "overrightarrow": "vec", "bar": "bar", "overline": "bar", "hat": "hat", "widehat": "hat", "tilde": "tilde", "widetilde": "tilde", "dot": "dot", "underline": "under", "cancel": "cancel"}  # draw.mjs:814
# Styles and sizes that change nothing drawn here: read past.
TEX_SKIP = {"displaystyle", "textstyle", "scriptstyle", "limits", "nolimits", "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "bigm", "mathstrut", "nonumber", "notag"}  # draw.mjs:816
TEX_STYLE = {"mathrm", "mathbf", "mathit", "boldsymbol", "mathsf", "mathcal", "mathtt", "bm", "mathnormal"}  # draw.mjs:817
TEX_BB = {"N": "ℕ", "Z": "ℤ", "Q": "ℚ", "R": "ℝ", "C": "ℂ"}  # draw.mjs:818
CHAR_OP = {"+": "+", "-": "−", "−": "−", "*": "·", "×": "×", "·": "·", "÷": "÷", "±": "±"}  # draw.mjs:819
CHAR_REL = {"=": "=", "<": "<", ">": ">", "≤": "≤", "≥": "≥", "≠": "≠", "≈": "≈", "→": "→", "⇒": "⇒"}  # draw.mjs:820
FENCES = {"(": "(", ")": ")", "[": "[", "]": "]", "|": "|", ".": "", "\\{": "{", "\\}": "}", "\\|": "‖", "\\langle": "⟨", "\\rangle": "⟩", "\\lfloor": "⌊", "\\rfloor": "⌋", "\\lceil": "⌈", "\\rceil": "⌉", "\\lvert": "|", "\\rvert": "|"}  # draw.mjs:821
TEX_HELP = "supported: \\frac, \\sqrt, ^, _, \\left( \\right), \\text, \\vec, \\bar, \\boxed, Greek letters, and symbols like \\times \\cdot \\pm \\le \\ne \\approx \\to \\pi \\infty \\sum \\int"  # draw.mjs:822
_FENCE_RE = re.compile(r"(\\[a-zA-Z]+|\\[{}|]|[()\[\]|.])")
_CMD_RE = re.compile(r"\\([a-zA-Z]+|[^a-zA-Z])", re.S)
_NUM_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)*")


def parse_tex(src: Any) -> dict[str, Any]:  # draw.mjs:823-938
    """One line of maths as a tree for the overlay to lay out. Nodes: { t: 's', s, k } a symbol (k: num, var, op, rel, fn,
    ord), 'row' { c }, 'frac' { a, b }, 'sqrt' { a, n? }, 'script' { a, sup?, sub? }, 'fence' { l, r, a }, 'text' { s },
    'over' { a, m } (m: vec, bar, hat, tilde, dot, under, cancel), 'box' { a }, 'sp' { w }. Supports fractions, roots,
    powers and subscripts, sized brackets, words, Greek and common symbols; a wrapping $…$ is dropped. Anything else
    (\\begin, &, \\\\, unknown commands) is refused with a reason, so nothing reaches the screen as raw LaTeX."""
    s = js_trim(js_str(src if src is not None else ""))  # draw.mjs:829
    s = re.sub(r"^\$\$?|\$\$?\Z", "", s)
    s = js_trim(re.sub(r"^\\[(\[]|\\[)\]]\Z", "", s))
    if not s:
        raise ValueError("The math is empty.")
    i = 0
    count = 0

    def at(k: int) -> str | None:  # s[k] (undefined fuera del texto)
        return s[k] if 0 <= k < len(s) else None

    def fail(why: str) -> Any:  # draw.mjs:832
        raise ValueError(f"""Can't read math "{u16slice(s, 40)}" at {min(i, len(s)) + 1}: {why}.""")

    def node(n: dict[str, Any]) -> dict[str, Any]:  # draw.mjs:833
        nonlocal count
        count += 1
        if count > LIMITS["tex"]:
            fail("too long for one step; split it over two")
        return n

    def sym(ch: str, k: str) -> dict[str, Any]:  # draw.mjs:834
        return node({"t": "s", "s": ch, "k": k})

    def ws() -> None:  # draw.mjs:835
        nonlocal i
        while i < len(s) and re.match(r"\s", s[i]):
            i += 1

    # What a command takes: {…}, or the single thing after it (\frac12, x^2).
    def arg(depth: int) -> dict[str, Any]:  # draw.mjs:837
        ws()
        if i >= len(s):
            fail("something is missing at the end")
        a = atom(depth, True)
        return a if a is not None else arg(depth)

    def braced(depth: int) -> dict[str, Any] | None:  # draw.mjs:838
        ws()
        if at(i) != "{":
            fail("expected {")
        return atom(depth)

    def fence() -> str:  # draw.mjs:839-845
        nonlocal i
        ws()
        m = _FENCE_RE.match(s, i)
        if not m or m[1] not in FENCES:
            fail("\\left and \\right need a bracket after them: ( ) [ ] | \\{ \\} or . for none")
        assert m is not None
        i += len(m[1])
        return FENCES[m[1]]

    def row(end: str | None, depth: int) -> dict[str, Any]:  # draw.mjs:846-868
        nonlocal i
        c: list[dict[str, Any]] = []
        while True:
            ws()
            if i >= len(s):
                break
            ch = s[i]
            if ch == "}":
                if end == "}":
                    break
                fail("a } without its {")
            if end == "]" and ch == "]":
                break
            if s.startswith("\\right", i) and not re.match(r"[a-zA-Z]", at(i + 6) or ""):
                if end == "right":
                    break
                fail("a \\right without its \\left")
            if ch in ("^", "_"):
                i += 1
                key = "sup" if ch == "^" else "sub"
                last = c.pop() if c else sym("", "ord")
                scr = last if last["t"] == "script" and not truthy(last.get(key)) else node({"t": "script", "a": last})
                scr[key] = arg(depth + 1)
                # A raised ring is a degree sign.
                if key == "sup" and scr["sup"]["t"] == "s" and scr["sup"]["s"] == "∘" and not truthy(scr.get("sub")):
                    c.append(scr["a"])
                    c.append(sym("°", "ord"))
                else:
                    c.append(scr)
                continue
            a = atom(depth)
            if a is not None:
                c.append(a)
        return c[0] if len(c) == 1 else node({"t": "row", "c": c})

    # The next thing; null for a command that draws nothing. one: a lone digit rather than a whole number (x^10 is x¹0).
    def atom(depth: int, one: bool = False) -> dict[str, Any] | None:  # draw.mjs:870-934
        nonlocal i
        if depth > 16:
            fail("nested too deep")
        ch = at(i)
        if ch == "{":
            i += 1
            r = row("}", depth + 1)
            if at(i) != "}":
                fail("a { without its }")
            i += 1
            return r
        if ch == "}":
            fail("a } without its {")
        if ch != "\\":
            assert ch is not None
            if re.match(r"[0-9]", ch):
                tok = ch if one else _NUM_RE.match(s, i)[0]  # type: ignore[index]
                i += len(tok)
                return sym(tok, "num")
            i += len(ch)
            if ch == "&":
                fail("& (tables and lined-up equations) is not supported: put each line in its own step")
            if ch in ("$", "#"):
                fail(f'"{ch}" is not needed: give the math without it')
            if ch == "~":
                return node({"t": "sp", "w": 0.33})
            if ch == "'":
                return sym("′", "ord")
            if ch in CHAR_OP:
                return sym(CHAR_OP[ch], "op")
            if ch in CHAR_REL:
                return sym(CHAR_REL[ch], "rel")
            return sym(ch, "var" if re.match(r"[a-zA-Z]", ch) else "ord")
        m = _CMD_RE.match(s, i)
        if not m:
            fail("a \\ with nothing after it")
        assert m is not None
        name = m[1]
        i += len(m[0])
        if name in ("frac", "dfrac", "tfrac"):
            a = arg(depth + 1)
            b = arg(depth + 1)
            return node({"t": "frac", "a": a, "b": b})
        if name == "sqrt":
            ws()
            n = None
            if at(i) == "[":
                i += 1
                n = row("]", depth + 1)
                if at(i) != "]":
                    fail("a [ without its ]")
                i += 1
            return node({"t": "sqrt", "a": arg(depth + 1), **({"n": n} if n is not None else {})})
        if name == "left":
            lf = fence()
            a = row("right", depth + 1)
            if not s.startswith("\\right", i):
                fail("a \\left without its \\right")
            i += 6
            return node({"t": "fence", "l": lf, "r": fence(), "a": a})
        if name == "right":
            fail("a \\right without its \\left")
        if name in ("text", "textbf", "textit", "textrm", "operatorname", "mbox"):
            ws()
            if at(i) != "{":
                fail(f"\\{name} needs its words in {{ }}")
            end = s.find("}", i)
            if end < 0:
                fail("a { without its }")
            words = s[i + 1 : end]
            if "{" in words:
                fail(f"\\{name} can only hold plain words")
            i = end + 1
            return node({"t": "text", "s": words})
        if name == "mathbb":
            a = braced(depth + 1)
            if a is not None and a["t"] == "s" and TEX_BB.get(a["s"]):
                return sym(TEX_BB[a["s"]], "ord")
            return a
        if name in TEX_STYLE:
            return arg(depth + 1)
        if name in TEX_OVER:
            return node({"t": "over", "m": TEX_OVER[name], "a": arg(depth + 1)})
        if name in ("boxed", "fbox"):
            return node({"t": "box", "a": arg(depth + 1)})
        # n over k in brackets: a fraction without its bar.
        if name in ("binom", "dbinom", "tbinom"):
            a = arg(depth + 1)
            b = arg(depth + 1)
            return node({"t": "fence", "l": "(", "r": ")", "a": node({"t": "frac", "a": a, "b": b, "bar": False})})
        # A colour is read past (the card has its own); what it colours stays.
        if name in ("color", "textcolor"):
            braced(depth + 1)
            return arg(depth + 1) if name == "textcolor" else None
        if name in ("phantom", "hphantom", "vphantom", "hspace"):
            braced(depth + 1)
            return node({"t": "sp", "w": 0.5})
        if name in TEX_SPACE:
            return node({"t": "sp", "w": TEX_SPACE[name]})
        if name in TEX_SKIP:
            return None
        if name in TEX_FN:
            return sym(name, "fn")
        if name in TEX_OP:
            return sym(TEX_OP[name], "op")
        if name in TEX_REL:
            return sym(TEX_REL[name], "rel")
        if name in TEX_ORD:
            return sym(TEX_ORD[name], "ord")
        if name in "{}%$_&#":
            return sym(name, "ord")
        if name == "|":
            return sym("‖", "ord")
        if name == "\\":
            fail("\\\\ (a new line) is not supported: put each line in its own step")
        if name in ("begin", "end"):
            fail(f"\\{name}{{…}} blocks (matrices, cases, lined-up equations) are not supported: one line per step")
        return fail(f"\\{name} is not supported ({TEX_HELP})")

    tree = row(None, 0)  # draw.mjs:935-937
    if i < len(s):
        fail("a ] without its [" if s[i] == "]" else f'"{s[i]}" is out of place')
    return tree
