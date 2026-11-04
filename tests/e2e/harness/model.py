"""Veredictos y registro de comprobaciones.

Regla del arnés: PASA solo sale de una comprobación que se ejecutó y acertó.
Lo que no se pudo ejecutar es NO COMPROBADO, nunca PASA.
"""
from __future__ import annotations

import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

PHASES = ("pre", "desktop", "post")  # pre: backend y stub; desktop: Electron; post: tras parar


class Status(str, Enum):
    PASA = "PASA"
    FALLA = "FALLA"
    NO_COMPROBADO = "NO COMPROBADO"


class NotChecked(Exception):
    """La comprobación no pudo ejecutarse: el motivo va al informe."""


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    fn: Callable[[Any], str | None]
    phase: str = "pre"
    needs: tuple[str, ...] = ("backend",)  # backend, stub, desktop
    uses_stub: bool = False  # su evidencia pasa por el stub: nunca prueba Haiku 5.5


@dataclass
class Result:
    id: str
    title: str
    status: Status
    evidence: str
    uses_stub: bool
    seconds: float


REGISTRY: dict[str, Check] = {}


def register(item: Check) -> None:
    if item.id in REGISTRY:
        raise ValueError(f"comprobación duplicada: {item.id}")
    if item.phase not in PHASES:
        raise ValueError(f"fase desconocida: {item.phase}")
    REGISTRY[item.id] = item


def check(id: str, title: str, *, phase: str = "pre", needs: tuple[str, ...] = ("backend",),
          uses_stub: bool = False):
    """Registra `fn(ctx) -> evidencia`. Un AssertionError o cualquier excepción es FALLA."""

    def decorator(fn):
        register(Check(id, title, fn, phase, needs, uses_stub))
        return fn

    return decorator


def run_check(item: Check, ctx: Any) -> Result:
    started = time.monotonic()

    def result(status: Status, evidence: str) -> Result:
        seconds = round(time.monotonic() - started, 2)
        return Result(item.id, item.title, status, ctx.scrub(evidence), item.uses_stub, seconds)

    missing = [name for name in item.needs if not ctx.stack.available(name)]
    if missing:
        reasons = "; ".join(f"{name}: {ctx.stack.why_unavailable(name)}" for name in missing)
        return result(Status.NO_COMPROBADO, f"no disponible: {reasons}")
    try:
        evidence = item.fn(ctx) or "ejecutada sin incidencias"
    except NotChecked as exc:
        return result(Status.NO_COMPROBADO, str(exc))
    except AssertionError as exc:
        return result(Status.FALLA, str(exc) or traceback.format_exc(limit=2))
    except Exception as exc:  # noqa: BLE001 - un fallo inesperado nunca puede acabar en PASA.
        return result(Status.FALLA, f"{type(exc).__name__}: {exc}")
    return result(Status.PASA, evidence)
