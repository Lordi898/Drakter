#!/usr/bin/env python3
"""Genera contracts/ts/index.ts desde los modelos Pydantic. Sin dependencias fuera de pydantic.

Uso (desde contracts/python): python ../scripts/gen_ts.py [salida]
"""

from __future__ import annotations

import enum
import inspect
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "python"))

from pydantic import BaseModel, TypeAdapter  # noqa: E402

from drakter_contracts import common, errors, events, models, tools  # noqa: E402
from drakter_contracts.common import ContractModel  # noqa: E402

SKIP = {"Page", "ContractModel", "OutModel"}
IDENT = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def public_types() -> tuple[dict[str, type[BaseModel]], dict[str, type[enum.Enum]]]:
    classes: dict[str, type[BaseModel]] = {}
    enums: dict[str, type[enum.Enum]] = {}
    for mod in (common, errors, tools, events, *models.MODULES, models._base):
        for name, obj in vars(mod).items():
            if name.startswith("_") or not inspect.isclass(obj) or obj.__module__ != mod.__name__:
                continue
            if name in SKIP:
                continue
            target = enums if issubclass(obj, enum.Enum) else classes if issubclass(obj, BaseModel) else None
            if target is None:
                continue
            if name in classes or name in enums:
                raise SystemExit(f"nombre duplicado: {name}")
            target[name] = obj  # type: ignore[assignment]
    return classes, enums


def ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def key(name: str) -> str:
    return name if IDENT.match(name) else repr(name).replace("'", '"')


def lit(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(value)


def ts(schema: dict[str, Any], indent: int = 0) -> str:
    if "$ref" in schema:
        return ref_name(schema["$ref"])
    if "const" in schema:
        return lit(schema["const"])
    if "enum" in schema:
        return " | ".join(lit(v) for v in schema["enum"])
    for k in ("anyOf", "oneOf"):
        if k in schema:
            parts: list[str] = []
            for s in schema[k]:
                t = ts(s, indent)
                if t not in parts:
                    parts.append(t)
            return " | ".join(parts)
    if "allOf" in schema:
        return " & ".join(ts(s, indent) for s in schema["allOf"])
    t = schema.get("type")
    if isinstance(t, list):
        return " | ".join(ts({**schema, "type": x}, indent) for x in t)
    if t == "string":
        return "string"
    if t in ("integer", "number"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "null":
        return "null"
    if t == "array":
        if "prefixItems" in schema:
            return "[" + ", ".join(ts(s, indent) for s in schema["prefixItems"]) + "]"
        item = ts(schema.get("items", {}), indent)
        return f"({item})[]" if " | " in item or " & " in item else f"{item}[]"
    if t == "object" or "properties" in schema or "additionalProperties" in schema:
        if "properties" in schema:
            return obj_body(schema, indent)
        ap = schema.get("additionalProperties", True)
        return f"Record<string, {ts(ap, indent) if isinstance(ap, dict) else 'unknown'}>"
    return "unknown"


def obj_body(schema: dict[str, Any], indent: int = 0) -> str:
    pad = "  " * (indent + 1)
    req = set(schema.get("required", []))
    lines = []
    for name, sub in schema.get("properties", {}).items():
        opt = "" if name in req else "?"
        lines.append(f"{pad}{key(name)}{opt}: {ts(sub, indent + 1)};")
    return "{\n" + "\n".join(lines) + "\n" + "  " * indent + "}" if lines else "Record<string, never>"


def doc(text: str | None) -> str:
    if not text:
        return ""
    clean = " ".join(text.split()).replace("*/", "*\\/")
    return f"/** {clean} */\n"


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "ts" / "index.ts"
    classes, enums = public_types()
    chunks: list[str] = []
    extra_defs: dict[str, dict[str, Any]] = {}

    for name, e in sorted(enums.items()):
        chunks.append(f"export type {name} = {' | '.join(lit(m.value) for m in e)};\n")

    for name, cls in sorted(classes.items()):
        mode = "validation" if issubclass(cls, ContractModel) else "serialization"
        schema = cls.model_json_schema(mode=mode, ref_template="#/$defs/{model}")
        if mode == "serialization":  # el servidor siempre emite los campos con valor por defecto
            schema["required"] = list(schema.get("properties", {}))
        for dn, ds in schema.get("$defs", {}).items():
            if dn not in classes and dn not in enums:
                if mode == "serialization" and "properties" in ds:
                    ds["required"] = list(ds["properties"])
                extra_defs.setdefault(dn, ds)
        body = ts(schema)
        decl = f"interface {name} {body}" if body.startswith("{") else f"type {name} = {body};"
        chunks.append(f"{doc(cls.__doc__)}export {decl}\n")

    for dn, ds in sorted(extra_defs.items()):
        if "enum" in ds:
            chunks.append(f"export type {dn} = {ts(ds)};\n")
        else:
            chunks.append(f"export interface {dn} {ts(ds)}\n")

    outcome = TypeAdapter(tools.ToolOutcome).json_schema(ref_template="#/$defs/{model}")
    members = " | ".join(ref_name(s["$ref"]) for s in outcome["oneOf"])
    disc = outcome["discriminator"]["propertyName"]
    chunks.append(f"/** Unión discriminada por `{disc}`. */\nexport type ToolOutcome = {members};\n")

    event_lines = "\n".join(f"  {lit(t)}: {m.__name__};" for t, m in events.EVENTS.items())
    chunks.append(f"export interface EventPayloads {{\n{event_lines}\n}}\n")
    chunks.append("export type EventType = keyof EventPayloads;\n")
    chunks.append(
        "export type TypedEvent = {\n"
        "  [K in EventType]: Omit<EventEnvelope, \"type\" | \"payload\"> & { type: K; payload: EventPayloads[K] };\n"
        "}[EventType];\n"
    )

    header = (
        "// Generado: no editar. Fuente: contracts/python/drakter_contracts (scripts/gen_ts.py).\n"
        f"export const CONTRACT_VERSION = {lit(__import__('drakter_contracts').CONTRACT_VERSION)};\n"
        f"export const SCHEMA_VERSION = {__import__('drakter_contracts').SCHEMA_VERSION};\n\n"
        "/** Listado con cursor opaco: `limit` lo acota el servidor. */\n"
        "export interface Page<T> {\n  items: T[];\n  next_cursor: string | null;\n  total?: number | null;\n}\n\n"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(header + "\n".join(chunks), encoding="utf-8")
    print(f"{out}: {len(classes)} interfaces, {len(enums)} enumerados, {len(events.EVENTS)} eventos")


if __name__ == "__main__":
    main()
