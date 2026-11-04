"""Motor de flujos declarativos de `tests/e2e/catalog.toml`.

Un flujo es una lista de pasos HTTP. Si el PRIMER paso, o uno con `unrouted_ok = true`,
da 404/405 de enrutado, esa pieza aún no está integrada: NO COMPROBADO. Cualquier otro
desvío es FALLA.
"""
from __future__ import annotations

import re
import tomllib
import uuid
from pathlib import Path
from typing import Any

from .model import Check, NotChecked, register

PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
UNROUTED = {"http_404", "http_405"}


def dig(value: Any, dotted: str) -> Any:
    for part in dotted.split("."):
        if isinstance(value, list):
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise AssertionError(f"la respuesta no contiene {dotted!r}")
    return value


def expand(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            if match.group(1) not in variables:
                raise AssertionError(f"variable sin capturar: {match.group(1)}")
            return str(variables[match.group(1)])
        return PLACEHOLDER.sub(replace, value)
    if isinstance(value, dict):
        return {key: expand(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [expand(item, variables) for item in value]
    return value


def run_flow(flow: dict[str, Any], ctx: Any) -> str:
    variables: dict[str, Any] = {"run": uuid.uuid4().hex[:8]}
    done: list[str] = []
    for index, step in enumerate(flow["step"]):
        name = step.get("name", f"paso {index + 1}")
        method, path = step["method"], expand(step["path"], variables)
        reply = ctx.api.request(method, path, json_body=expand(step.get("json"), variables))
        if (index == 0 or step.get("unrouted_ok")) and reply.error_code in UNROUTED:
            raise NotChecked(f"ruta no integrada: {method} {path} → {reply.status}")
        expected = step.get("expect", [200])
        if reply.status not in expected:
            raise AssertionError(f"{name}: {method} {path} → {reply.status} "
                                 f"(esperado {expected}, código {reply.error_code})")
        for dotted, wanted in step.get("assert", {}).items():
            got = dig(reply.body, dotted)
            wanted = expand(wanted, variables)
            if got != wanted:
                raise AssertionError(f"{name}: {dotted} = {got!r}, esperado {wanted!r}")
        for variable, dotted in step.get("capture", {}).items():
            variables[variable] = dig(reply.body, dotted)
        done.append(f"{name} ({reply.status})")
    return "; ".join(done)


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        catalog = tomllib.load(handle)
    for flow in catalog.get("flow", []):
        register(Check(flow["id"], flow["title"], lambda ctx, f=flow: run_flow(f, ctx),
                       "pre",
                       tuple(flow.get("needs", ("backend",))), bool(flow.get("uses_stub", False))))
    return catalog
