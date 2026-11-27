"""Hands of the floating mode: `act_in_app` and `open_target` (CONTRACT §8.2, §14).

Two barriers: this module (setting, HANDS_OFF, Drakter windows, RISKY, password fields, stale views) and the
helper's own. The hands are off until the user turns on `floating_hands_enabled` in the interface. In a
tainted session the gate turns these WRITE tools into a confirmation; `confirm_if` does the same for a risky
plan or `confirm=true` (B1). Typed text never reaches the audit, the trail or the confirmation summary.

An approval covers the window it named (same `window_id` and app) and only the risky steps the summary
named: each of those goes to the helper alone with `confirmed`, the rest without it (security review I1).
Background jobs never reach these tools (review C1).
"""

from __future__ import annotations

import os
import sqlite3
import stat
import unicodedata
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit
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
from drakter_contracts.hands_ipc import (
    HAct,
    HActResult,
    HApp,
    HAppsResult,
    HEmpty,
    HelperWindow,
    HEvtProgress,
    HOpen,
    HStepResult,
)
from pydantic import BaseModel, model_validator

from app.integrations.hands import desktop, records
from app.integrations.hands.client import HandsError
from app.integrations.hands.lists import hands_off_name, secret_title
from app.integrations.hands.safety import MASK, args_risk, check_url_dns, runnable, step_phrase, step_risk
from app.tools.envelope import untrusted_envelope
from app.tools.screen import MESSAGES, client_or_error, read_into_record, refuse_job_lane, setting_on, tool_error
from app.tools.spec import RiskClass, ToolContext, ToolError, ToolSpec

HANDS_SETTING: Final = "floating_hands_enabled"
ACT_ERRORS: Final = ("validation_error", "hands_disabled", "hands_off_app", "drakter_window", "risky_step",
                     "secret_field", "window_not_found", "window_changed", "stale_read", "stale_screenshot",
                     "stale_window", "step_failed", "input_unavailable", "companion_unavailable",
                     "job_lane_forbidden")
OPEN_ERRORS: Final = ("validation_error", "hands_disabled", "target_not_allowed", "app_not_found",
                      "path_not_allowed", "not_found", "companion_unavailable", "job_lane_forbidden")
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
NEED_WINDOW: Final = ("Un plan que pide confirmación necesita window_id (de list_windows, read_window o "
                      "look_screen): ponlo para que el usuario sepa en qué ventana se actúa.")
SUMMARY_SHOWN: Final = 12
URL_SHOWN: Final = 200


def _err(code: str, message: str | None = None, **kw: Any) -> ToolError:
    return ToolError(code, message or MESSAGES.get(code, "No se pudo completar."), **kw)


def _ctx_confirmed(ctx: ToolContext) -> bool:
    """`ToolContext.confirmed` (B1): True only when the handler runs from an approval."""
    return ctx.confirmed is True


def hands_enabled(ctx: ToolContext) -> bool:
    """`floating_hands_enabled` is `"true"` in the settings table. Off when unknown."""
    return setting_on(ctx, HANDS_SETTING)


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
class ActInAppToolArgs(ActInAppArgs):
    """`ActInAppArgs` plus I1: a plan that asks for confirmation by itself must name its window.

    A plan raised only by a tainted session cannot be told apart here: its summary says it will not run
    and the handler refuses it on approval.
    """

    @model_validator(mode="after")
    def _window_when_confirmed(self) -> ActInAppToolArgs:
        if self.window_id is None and (self.confirm or args_risk(self) is not None):
            raise ValueError(NEED_WINDOW)
        return self


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


def _app_ids(w: HelperWindow | None) -> tuple[str | None, ...]:
    return (w.app_id, w.wm_class) if w is not None else ()


# What a summary showed: window_id → app ids. The approval must find the same app in that window (I1).
_summarized: dict[str, tuple[str | None, ...]] = {}


def _summary_app(window_id: str | None) -> tuple[str | None, ...]:
    if window_id is None:
        return ()
    if (seen := _summarized.get(str(window_id))) is not None:
        return seen
    return _app_ids(desktop.known_window(window_id))


def approved_steps(args: ActInAppArgs) -> dict[int, str]:
    """Index → risk of the risky steps a confirmation of these arguments names: the only ones it approves.

    Pure function of the arguments, the read they name and the window the summary showed, so the approval
    recomputes exactly what the user read.
    """
    controls = _named_controls(args)
    app = _summary_app(args.window_id)
    out: dict[int, str] = {}
    for i, step in enumerate(args.steps):
        if (kind := step_risk(step, controls, app)) is not None:
            out[i] = kind
    return out


def _window_phrase(window_id: str | None) -> str:
    if window_id is None:
        return "la ventana activa (sin identificar: esta aprobación no se ejecutará)"
    w = desktop.known_window(window_id)
    if w is None:
        return "una ventana que Drakter no ha podido identificar (no se ejecutará)"
    title = MASK if secret_title(w.title) else " ".join((w.title or "Sin título").split())[:80]
    return f"«{desktop.app_label(w)}», ventana «{title}»"


def _summary(args: BaseModel) -> str:
    """Built by the backend for the confirmation. Typed text: only its length."""
    assert isinstance(args, ActInAppArgs)
    if args.window_id is not None and (w := desktop.known_window(args.window_id)) is not None:
        _summarized[str(args.window_id)] = _app_ids(w)
    controls = _named_controls(args)
    where = _window_phrase(args.window_id)
    steps = "; ".join(f"{i + 1}. {step_phrase(s, controls)}" for i, s in enumerate(args.steps[:SUMMARY_SHOWN]))
    more = f"; y {len(args.steps) - SUMMARY_SHOWN} pasos más" if len(args.steps) > SUMMARY_SHOWN else ""
    risky = approved_steps(args)
    tail = "".join(f" Paso {i + 1} arriesgado ({kind}): {step_phrase(args.steps[i], controls)}."
                   for i, kind in risky.items())
    if risky:
        tail += " Solo se aprueban los pasos arriesgados nombrados aquí."
    unnamed = ""
    if _uses_ids(args) and (controls is None or any(
        getattr(s, "id", None) is not None and s.id not in controls for s in args.steps
    )):
        unnamed = (" Atención: no se ha podido nombrar algún control señalado por número; "
                   "si resulta arriesgado, no se pulsará.")
    return f"Vas a usar {where}: {steps}{more}.{tail}{unnamed}"


def _confirm_if_act(args: BaseModel) -> str | None:
    assert isinstance(args, ActInAppArgs)
    risky = approved_steps(args)
    if risky:
        i, kind = next(iter(risky.items()))
        return f"Paso {i + 1} arriesgado: {kind}."
    return "Has pedido confirmación." if args.confirm else None


def segments(n: int, approved: set[int]) -> list[tuple[int, int, bool]]:
    """Runs of steps for the helper: each approved risky step alone with `confirmed`, the rest without it.

    So the helper's barrier still refuses any risky step the user did not see named (I1).
    """
    out: list[tuple[int, int, bool]] = []
    start = 0
    for i in range(n):
        if i in approved:
            if start < i:
                out.append((start, i, False))
            out.append((i, i + 1, True))
            start = i + 1
    if start < n:
        out.append((start, n, False))
    return out


def _trail(steps: list[Any], controls: dict, states: list[str], head: str, act_id: UUID, final: bool) -> OverlayTrail:
    shown = []
    for i, s in enumerate(steps[:8]):
        text = step_phrase(s, controls)
        shown.append(TrailStep(text=(text[0].upper() + text[1:])[:48], state=states[i]))  # type: ignore[arg-type]
    return OverlayTrail(act_id=act_id, steps=shown, head=head[:40], final=final)


async def act_in_app(ctx: ToolContext, args: ActInAppArgs) -> ActInAppResult:
    refuse_job_lane(ctx)
    turn: UUID = ctx.turn_id
    confirmed = _ctx_confirmed(ctx)
    if not hands_enabled(ctx):
        raise _err("hands_disabled")
    if confirmed and args.window_id is None:
        raise _err("validation_error", NEED_WINDOW)
    # Before the window list below refreshes what the summary named.
    approved = approved_steps(args) if confirmed else {}
    expected = _summarized.get(str(args.window_id)) if confirmed else None
    client = await client_or_error(ACT_ERRORS)
    try:
        wins = await desktop.list_windows(client)
        w = desktop.pick(wins, args.window_id)
    except HandsError as exc:
        if confirmed and exc.code == "window_not_found":
            raise _err("stale_window") from None
        raise tool_error(exc, ACT_ERRORS) from None
    if confirmed and (expected is None or _app_ids(w) != expected):
        raise _err("stale_window")
    if desktop.is_drakter(w):
        raise _err("drakter_window")
    if desktop.is_hands_off(w):
        raise _err("hands_off_app")
    app = _app_ids(w)

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
        if (kind := step_risk(s, controls, app)) is not None and i not in approved:
            detail = [{"field": f"steps.{i}", "code": "risky_step", "message": kind[:60]}]
            if confirmed:  # risky now, but not named in what the user approved
                raise _err("risky_step", f"El paso {i + 1} ({step_phrase(s, controls)}) es arriesgado y no "
                           "aparecía en lo que el usuario aprobó: no se ejecuta.", details=detail)
            again = (f"repite con confirm=true, window_id y read_id={rec.read_id}, para que la confirmación "
                     "muestre el nombre del control." if rec is not None else
                     "repite con confirm=true y window_id.")
            raise _err("risky_step", f"El paso {i + 1} ({step_phrase(s, controls)}) necesita confirmación: " + again,
                       retryable=True, details=detail)

    act_id = uuid4()
    hub = _hub(ctx)
    head = f"Usando {desktop.app_label(w)}"
    states = ["now"] + [""] * (len(args.steps) - 1)
    _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, on=True), turn)
    _publish(hub, "overlay.trail", _trail(args.steps, controls, states, head, act_id, False), turn)
    offset = 0  # index of the first step of the segment the helper is running

    def progress(evt: BaseModel) -> None:
        if not isinstance(evt, HEvtProgress) or evt.act_id != str(act_id):
            return
        if evt.state == "step" and evt.bounds is not None:
            b = evt.bounds
            _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, step=HandsStepBounds(
                bounds=[float(b.x), float(b.y), float(b.w), float(b.h)], hover=evt.hover)), turn)
            index = evt.index + offset
            if 0 <= index < len(states):
                for k in range(index):
                    states[k] = states[k] or "ok"
                    if states[k] == "now":
                        states[k] = "ok"
                states[index] = "now"
                _publish(hub, "overlay.trail", _trail(args.steps, controls, states, head, act_id, False), turn)

    off = client.on_event("act.progress", progress)
    res: HActResult | None = None
    failure: HandsError | None = None
    try:
        status = "done"
        results: list[HStepResult] = []
        for a, b, ok in segments(len(steps_out), set(approved)):
            offset = a
            part = await client.call("act", HAct(act_id=str(act_id), window_id=w.window_id, steps=steps_out[a:b],
                                                 confirmed=ok, controls=list(controls.values())[:260]))
            assert isinstance(part, HActResult)
            results.extend(r.model_copy(update={"index": r.index + a}) for r in part.steps if r.index < b - a)
            if part.status != "done":
                status = part.status
                seen = {r.index for r in results}
                results.extend(HStepResult(index=j, status="skipped") for j in range(a, len(steps_out)) if j not in seen)
                break
        res = HActResult(status=status, steps=results)  # type: ignore[arg-type]
    except HandsError as exc:
        failure = exc
    finally:
        off()
        _publish(hub, "overlay.hands", OverlayHands(act_id=act_id, on=False), turn)
    if res is None:
        _publish(hub, "overlay.trail", _trail(args.steps, controls, ["bad"] + [""] * (len(args.steps) - 1),
                                              head, act_id, True), turn)
        assert failure is not None
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
                   retryable=code in ("risky_step", "window_changed") and not confirmed,
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
def _shown_url(url: str) -> str:
    """The whole URL as the approver must read it: no control or bidi characters, ~200 characters."""
    clean = "".join(" " if unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") else ch for ch in url.strip())
    return clean if len(clean) <= URL_SHOWN else clean[: URL_SHOWN - 1] + "…"


def _url_warning(url: str) -> str:
    u = urlsplit(url.strip())
    if (u.scheme or "").lower() == "mailto":
        fields = {k.lower() for k in parse_qs(u.query, keep_blank_values=True)}
        if fields & {"body", "subject", "cc", "bcc"}:
            return " Atención: el correo ya lleva asunto, texto o destinatarios añadidos; revisa qué se envía."
        return ""
    if u.query or u.fragment:
        return " Atención: el enlace lleva datos añadidos (tras «?» o «#»); revisa que no se envíe nada tuyo."
    return ""


def _summary_open(args: BaseModel) -> str:
    assert isinstance(args, OpenTargetArgs)
    if args.url is not None:
        host = urlsplit(args.url.strip()).hostname or ""
        where = f" (servidor {host[:80]})" if host else ""
        return f"Vas a abrir «{_shown_url(args.url)}»{where}.{_url_warning(args.url)}"
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
    refuse_job_lane(ctx)
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
            "campos de contraseña. Si un paso es arriesgado (borrar, pagar, enviar, cerrar sesión, atajos del "
            "sistema, Intro en un navegador o un chat…) pon confirm=true y window_id: el usuario lo aprueba "
            "antes, y solo se ejecutan los pasos arriesgados que vio nombrados. Necesita que el usuario haya "
            "activado las manos."
        ),
        domain="hands", args_model=ActInAppToolArgs, result_model=ActInAppResult, permission="hands.write",
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
