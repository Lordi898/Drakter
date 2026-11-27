"""Hands of the floating mode: `act_in_app` and `open_target` (CONTRACT §8.2, §14).

Two barriers: this module (setting, HANDS_OFF, Drakter windows, RISKY, password fields, stale views) and the
helper's own. The hands are off until the user turns on `floating_hands_enabled` in the interface. In a
tainted session the gate turns these WRITE tools into a confirmation; `confirm_if` does the same for a risky
plan or `confirm=true` (B1). Typed text never reaches the audit, the trail or the confirmation summary.
"""

from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import closing
from typing import Any, Final
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from drakter_contracts.floating import (
    ActInAppArgs,
    ActInAppResult,
    HandsStepBounds,
    OpenTargetArgs,
    OpenTargetResult,
    OverlayHands,
    OverlayTrail,
    StepClickAt,
    StepFill,
    StepOutcome,
    StepSet,
    StepType,
    TrailStep,
)
from drakter_contracts.hands_ipc import HAct, HActResult, HApp, HAppsResult, HEmpty, HEvtProgress, HOpen
from pydantic import BaseModel

from app.integrations.hands import desktop, records
from app.integrations.hands.client import HandsError
from app.integrations.hands.lists import hands_off_name
from app.integrations.hands.safety import args_risk, check_url_dns, runnable, step_phrase, step_risk
from app.tools.envelope import untrusted_envelope
from app.tools.screen import MESSAGES, client_or_error, read_into_record, tool_error
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

HANDS_SETTING: Final = "floating_hands_enabled"
ACT_ERRORS: Final = ("validation_error", "hands_disabled", "hands_off_app", "drakter_window", "risky_step",
                     "secret_field", "window_not_found", "window_changed", "stale_read", "stale_screenshot",
                     "step_failed", "input_unavailable", "companion_unavailable")
OPEN_ERRORS: Final = ("validation_error", "hands_disabled", "target_not_allowed", "app_not_found",
                      "path_not_allowed", "not_found", "companion_unavailable")
_REFUSALS: Final = ("hands_off_app", "drakter_window", "risky_step", "secret_field", "window_changed",
                    "window_not_found", "input_unavailable")
_STEP_MSG: Final = {
    "risky_step": "Paso arriesgado sin confirmación.",
    "secret_field": "Campo de contraseña: no se escribe.",
    "hands_off_app": "App protegida.",
    "drakter_window": "Ventana de Drakter.",
    "window_changed": "La ventana cambió o perdió el foco.",
    "step_failed": "No se pudo hacer este paso.",
    "input_unavailable": "No hay inyector de entrada.",
}


def _err(code: str, message: str | None = None, **kw: Any) -> ToolError:
    return ToolError(code, message or MESSAGES.get(code, "No se pudo completar."), **kw)


def _ctx_confirmed(ctx: ToolContext) -> bool:
    """`ToolContext.confirmed` (B1): True only when the handler runs from an approval."""
    return ctx.confirmed is True


def hands_enabled(ctx: ToolContext) -> bool:
    """`floating_hands_enabled` is `"true"` in the settings table. Off when unknown."""
    settings = getattr(ctx.state, "settings", None)
    db_path = getattr(settings, "db_path", None)
    if db_path is None:
        return False
    try:
        from app.database.connection import connect
        from app.repositories import settings as repo

        with closing(connect(db_path)) as conn:
            if not repo.table_exists(conn, "settings"):
                return False
            item = repo.read_all(conn).get(HANDS_SETTING)
    except (sqlite3.Error, OSError):
        return False
    return item is not None and str(item.value).lower() == "true"


def _hub(ctx: ToolContext) -> Any:
    return getattr(getattr(ctx.state, "agent_runtime", None), "hub", None)


def _publish(hub: Any, type: str, payload: BaseModel, turn: UUID) -> None:
    if hub is None:
        return
    try:
        hub.publish(type, payload, correlation_id=str(turn))
    except Exception:  # noqa: BLE001 - the overlay is decoration: never stop the hands for it
        pass


# ── act_in_app ───────────────────────────────────────────────────────────────
def _named_controls(args: ActInAppArgs) -> dict | None:
    """Controls of the read the steps point at, to name `id` targets in the confirmation.

    `summarize` and `confirm_if` only get the arguments, so only an explicit `read_id` can be
    resolved; a stale read (the window changed) does not name anything.
    """
    if args.read_id is None:
        return None
    rec = records.read_record(args.read_id)
    if rec is None or rec.stale:
        return None
    return rec.by_id()


def _uses_ids(args: ActInAppArgs) -> bool:
    return any(getattr(s, "id", None) is not None for s in args.steps)


def _risk_with_names(args: ActInAppArgs, controls: dict | None) -> str | None:
    """Risk by what the model wrote and, if the read is known, by the names of the `id` targets."""
    if (reason := args_risk(args)) is not None:
        return reason
    for i, step in enumerate(args.steps):
        if (kind := step_risk(step, controls)) is not None:
            return f"Paso {i + 1} arriesgado: {kind}."
    return None


def _summary(args: BaseModel) -> str:
    """Built by the backend for the confirmation. Typed text: only its length."""
    assert isinstance(args, ActInAppArgs)
    controls = _named_controls(args)
    where = "la ventana activa" if args.window_id is None else f"la ventana {args.window_id}"
    steps = "; ".join(f"{i + 1}. {step_phrase(s, controls)}" for i, s in enumerate(args.steps[:12]))
    more = f"; y {len(args.steps) - 12} pasos más" if len(args.steps) > 12 else ""
    reason = _risk_with_names(args, controls)
    tail = f" {reason}" if reason else ""
    unnamed = ""
    if _uses_ids(args) and (controls is None or any(
        getattr(s, "id", None) is not None and s.id not in controls for s in args.steps
    )):
        unnamed = (" Atención: no se ha podido nombrar algún control señalado por número; "
                   "comprueba en la pantalla qué se va a pulsar antes de aprobar.")
    return f"Vas a usar {where}: {steps}{more}.{tail}{unnamed}"


def _confirm_if_act(args: BaseModel) -> str | None:
    assert isinstance(args, ActInAppArgs)
    if (reason := _risk_with_names(args, _named_controls(args))) is not None:
        return reason
    return "Has pedido confirmación." if args.confirm else None


def _trail(steps: list[Any], controls: dict, states: list[str], head: str, act_id: UUID, final: bool) -> OverlayTrail:
    shown = []
    for i, s in enumerate(steps[:8]):
        text = step_phrase(s, controls)
        shown.append(TrailStep(text=(text[0].upper() + text[1:])[:48], state=states[i]))  # type: ignore[arg-type]
    return OverlayTrail(act_id=act_id, steps=shown, head=head[:40], final=final)


async def act_in_app(ctx: ToolContext, args: ActInAppArgs) -> ActInAppResult:
    turn: UUID = ctx.turn_id
    confirmed = _ctx_confirmed(ctx)
    if not hands_enabled(ctx):
        raise _err("hands_disabled")
    client = await client_or_error(ACT_ERRORS)
    try:
        wins = await desktop.list_windows(client)
        w = desktop.pick(wins, args.window_id)
    except HandsError as exc:
        raise tool_error(exc, ACT_ERRORS) from None
    if desktop.is_drakter(w):
        raise _err("drakter_window")
    if desktop.is_hands_off(w):
        raise _err("hands_off_app")

    # ids → the turn's read; click_at → the turn's capture (CONTRACT §8.2 step 4)
    controls: dict = {}
    rec = None
    if any(getattr(s, "id", None) is not None for s in args.steps):
        rec = records.read_record(args.read_id) if args.read_id else records.latest_read(turn)
        # From an approval the context has a turn of its own: the read_id names the read then.
        foreign = rec is not None and rec.turn_id != turn and not (confirmed and args.read_id)
        if rec is None or foreign or rec.stale or rec.window_id != w.window_id:
            raise _err("stale_read", retryable=True)
        controls = rec.by_id()
        for s in args.steps:
            cid = getattr(s, "id", None)
            if cid is not None and cid not in controls:
                raise _err("stale_read", retryable=True)
    steps_out: list[Any] = []
    for i, s in enumerate(args.steps):
        if isinstance(s, StepClickAt):
            if args.shot_id:
                shot = records.shot_record(turn, args.shot_id) or (records.find_shot(args.shot_id) if confirmed else None)
            else:
                shot = records.latest_shot(turn)
            if shot is None or shot.stale:
                raise _err("stale_screenshot", retryable=True)
            x, y = shot.to_logical(s.x, s.y)
            steps_out.append(s.model_copy(update={"x": max(0.0, x), "y": max(0.0, y)}))
        else:
            steps_out.append(s)
        target = controls.get(getattr(s, "id", None)) if getattr(s, "id", None) is not None else None
        if isinstance(s, (StepFill, StepSet, StepType)) and target is not None and target.secret:
            raise _err("secret_field", details=[{"field": f"steps.{i}", "code": "secret_field", "message": "contraseña"}])
        if not confirmed and (kind := step_risk(s, controls)) is not None:
            raise _err("risky_step", f"El paso {i + 1} ({step_phrase(s, controls)}) necesita confirmación: "
                                     ("repite con confirm=true" + (f" y read_id={rec.read_id}, para que la confirmación muestre "
                                     "el nombre del control." if rec is not None else ".")), retryable=True,
                       details=[{"field": f"steps.{i}", "code": "risky_step", "message": kind[:60]}])

    act_id = uuid4()
    hub = _hub(ctx)
    head = f"Usando {desktop.app_label(w)}"
    states = ["now"] + [""] * (len(args.steps) - 1)
    _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, on=True), turn)
    _publish(hub, "overlay.trail", _trail(args.steps, controls, states, head, act_id, False), turn)

    def progress(evt: BaseModel) -> None:
        if not isinstance(evt, HEvtProgress) or evt.act_id != str(act_id):
            return
        if evt.state == "step" and evt.bounds is not None:
            b = evt.bounds
            _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, step=HandsStepBounds(
                bounds=[float(b.x), float(b.y), float(b.w), float(b.h)], hover=evt.hover)), turn)
            if 0 <= evt.index < len(states):
                for k in range(evt.index):
                    states[k] = states[k] or "ok"
                    if states[k] == "now":
                        states[k] = "ok"
                states[evt.index] = "now"
                _publish(hub, "overlay.trail", _trail(args.steps, controls, states, head, act_id, False), turn)

    off = client.on_event("act.progress", progress)
    try:
        res = await client.call("act", HAct(act_id=str(act_id), window_id=w.window_id, steps=steps_out,
                                            confirmed=confirmed, controls=list(controls.values())[:260]))
        assert isinstance(res, HActResult)
    except HandsError as exc:
        res = None
        failure = exc
    finally:
        off()
        _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, on=False), turn)
    if res is None:
        _publish(hub, "overlay.trail", _trail(args.steps, controls, ["bad"] + [""] * (len(args.steps) - 1),
                                              head, act_id, True), turn)
        raise tool_error(failure, ACT_ERRORS) from None

    outcomes: list[StepOutcome] = []
    refused: tuple[int, str] | None = None
    for r in res.steps:
        if r.index >= len(args.steps):
            continue
        code = r.code if r.code in ACT_ERRORS else ("step_failed" if r.status == "failed" else r.code)
        if r.status == "refused" and refused is None:
            refused = (r.index, code or "step_failed")
        outcomes.append(StepOutcome(index=r.index, do=args.steps[r.index].do, status=r.status,
                                    code=(code or None) and code[:40],
                                    message=_STEP_MSG.get(code or "") if r.status in ("failed", "refused") else None))
    final_states = []
    by_index = {o.index: o.status for o in outcomes}
    for i in range(len(args.steps)):
        st = by_index.get(i, "skipped")
        final_states.append("ok" if st == "ok" else "bad" if st in ("failed", "refused") else "")
    _publish(hub, "overlay.trail", _trail(args.steps, controls, final_states, head, act_id, True), turn)
    if refused is not None and refused[1] in _REFUSALS:
        i, code = refused
        raise _err(code, f"Paso {i + 1} ({step_phrase(args.steps[i], controls)}): {MESSAGES.get(code, code)}",
                   retryable=code in ("risky_step", "window_changed"),
                   details=[{"field": f"steps.{i}", "code": code, "message": _STEP_MSG.get(code, code)}])

    # A fresh read of the window: the model does not need another read_window.
    read_id = None
    envelope = None
    try:
        wins = await desktop.list_windows(client)
        fresh = next((x for x in wins.windows if x.window_id == w.window_id), None)
        if fresh is not None:
            read_id, _c, content, cut, _n = await read_into_record(client, turn, fresh, max_controls=120)
            envelope = untrusted_envelope("window_read", str(read_id), content, truncated=cut)
            w = fresh
    except HandsError:
        pass
    return ActInAppResult(act_id=act_id, status=res.status, steps=outcomes, window=desktop.window_ref(w),
                          read_id=read_id, envelope=envelope)  # type: ignore[arg-type]


# ── open_target ──────────────────────────────────────────────────────────────
def _summary_open(args: BaseModel) -> str:
    assert isinstance(args, OpenTargetArgs)
    if args.url is not None:
        return f"Vas a abrir {(urlsplit(args.url).hostname or args.url)[:80]} en el navegador."
    if args.app_id is not None:
        return f"Vas a abrir la aplicación {args.app_id}."
    return f"Vas a abrir el archivo {args.relative_path} del almacén."


def _confirm_if_open(args: BaseModel) -> str | None:
    return "Has pedido confirmación." if getattr(args, "confirm", False) else None


def _store_path(ctx: ToolContext, location_id: UUID, relative: str) -> str:
    """Absolute path of a store file, validated by the store's own confined open (realpath, no escape)."""
    from app.database.connection import connect
    from app.repositories import storage as repo
    from app.services import storage_safefs as safefs
    from app.services.storage_index import location_root
    from app.services.storage_ports import tool_deps

    deps = tool_deps(ctx.state)
    conn = connect(ctx.state.settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        loc = repo.get_location(conn, str(location_id))
    finally:
        conn.close()
    if loc is None or not loc["enabled"]:
        raise _err("not_found")
    if "agent_read" in loc.keys() and not loc["agent_read"]:
        raise _err("path_not_allowed")
    root, identity = location_root(loc)
    try:
        with safefs.open_file(root, identity, relative, denied=deps.denied_roots) as opened:
            mode = os.fstat(opened.fd).st_mode
    except safefs.MissingFile:
        raise _err("not_found") from None
    except (safefs.PathNotAllowed, ValueError, OSError):
        raise _err("path_not_allowed") from None
    normalized = safefs.validate_relative_path(relative)
    if not stat.S_ISREG(mode) or runnable(normalized, mode):
        raise _err("target_not_allowed", "Es un script, instalador o ejecutable: no lo abro.")
    return str(os.path.realpath(root) + "/" + normalized)


async def open_target(ctx: ToolContext, args: OpenTargetArgs) -> OpenTargetResult:
    if not hands_enabled(ctx):
        raise _err("hands_disabled")
    if args.url is not None:
        if (reason := check_url_dns(args.url)) is not None:
            raise _err("target_not_allowed", f"No abro ese enlace: {reason}.")
        req, kind, display = HOpen(url=args.url), "url", (urlsplit(args.url).hostname or "enlace")
        if args.url.lower().startswith("mailto:"):
            display = "correo"
    elif args.app_id is not None:
        app_id = args.app_id[: -len(".desktop")] if args.app_id.endswith(".desktop") else args.app_id
        if hands_off_name(app_id):
            raise _err("target_not_allowed", "Esa aplicación está protegida: no la abro.")
        client = await client_or_error(OPEN_ERRORS)
        try:
            apps = await client.call("apps.list", HEmpty())
        except HandsError as exc:
            raise tool_error(exc, OPEN_ERRORS) from None
        assert isinstance(apps, HAppsResult)
        match: HApp | None = next((a for a in apps.apps if a.app_id == app_id), None)
        if match is None:
            raise _err("app_not_found")
        req, kind, display = HOpen(app_id=app_id), "app", match.name
    else:
        assert args.location_id is not None and args.relative_path is not None
        path = _store_path(ctx, args.location_id, args.relative_path)
        req, kind, display = HOpen(path=path), "file", os.path.basename(path)
    client = await client_or_error(OPEN_ERRORS)
    try:
        await client.call("open", req)
    except HandsError as exc:
        raise tool_error(exc, OPEN_ERRORS) from None
    return OpenTargetResult(opened=True, kind=kind, display=display[:120])  # type: ignore[arg-type]


TOOLS = (
    ToolSpec(
        name="act_in_app",
        description=(
            "Usa otra aplicación como lo haría el usuario: un plan de 1 a 40 pasos (clic por texto o id, "
            "rellenar, elegir, escribir, teclas, desplazar, pasar el ratón, esperar) sobre una ventana. Nunca en "
            "terminales, gestores de contraseñas, ajustes del sistema ni ventanas de Drakter, ni escribe en "
            "campos de contraseña. Si un paso es arriesgado (borrar, pagar, enviar, cerrar sesión…) pon "
            "confirm=true: el usuario lo aprueba antes. Necesita que el usuario haya activado las manos."
        ),
        domain="hands", args_model=ActInAppArgs, result_model=ActInAppResult, permission="hands.write",
        risk=RiskClass.WRITE, handler=act_in_app, errors=ACT_ERRORS, idempotent=False, timeout_s=90.0,
        returns_untrusted=True, summarize=_summary, confirm_if=_confirm_if_act,
        # steps hold typed text: hashed, never logged
        audit={"window_id": "log", "read_id": "log", "shot_id": "log", "confirm": "log", "steps": "hash"},
    ),
    ToolSpec(
        name="open_target",
        description=(
            "Abre una web (http, https o mailto), una aplicación instalada por su id o un archivo del almacén de "
            "Drakter (location_id + relative_path) con su programa predeterminado. No abre scripts, instaladores "
            "ni rutas fuera del almacén."
        ),
        domain="hands", args_model=OpenTargetArgs, result_model=OpenTargetResult, permission="hands.write",
        risk=RiskClass.WRITE, handler=open_target, errors=OPEN_ERRORS, idempotent=False, timeout_s=10.0,
        returns_untrusted=False, summarize=_summary_open, confirm_if=_confirm_if_open,
        audit={"app_id": "log", "location_id": "log", "confirm": "log", "url": "hash", "relative_path": "hash"},
    ),
)
