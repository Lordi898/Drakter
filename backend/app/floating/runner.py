"""DrawRunner: reproduce un dibujo beat a beat y lleva las guías (docs/floating/CONTRACT.md §8.2, §9.3, §9.4).

Port de `draw()` y de `inkEvents` de Roamies (`showcase/tauri/sidecar/tools.mjs:680-819`, KenKaiii/Roamies@8f0adaa,
AGPL-3.0), partido en dos herramientas acotadas: `draw` vuelve en cuanto un beat espera (`waiting`) y
`guide_wait` espera el clic, resuelve y envía los beats siguientes hasta la próxima espera o el final.

Un solo proceso y un solo usuario: hay un runner por proceso (`RUNNER`). Hermes nunca ve esto: solo las
herramientas de `app/tools/overlay.py`, que llaman aquí.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Final, Literal
from uuid import UUID, uuid4

from drakter_contracts.floating import (
    DrawToolResult,
    FloatingPresence,
    GuideWaitResult,
    MissingTarget,
    OverlayClientEvent,
    OverlayClipboard,
    OverlayDraw,
    OverlayInkStale,
)
from drakter_contracts.speech_markup import strip_tags

from app.floating import drawjs, ports, presence
from app.floating.parts import InkState
from app.floating.safety import BLOCK, check_url
from app.integrations.hands.safety import check_url_dns
from app.tools.spec import ToolError

logger = logging.getLogger("drakter.floating.runner")

START_TIMEOUT_S: Final = 15.0  # tools.mjs:746
WAIT_CLICK_S: Final = 110.0  # CONTRACT.md §8.2 (Roamies: 120 s, tools.mjs:752)
WAIT_HOVER_S: Final = 60.0
AFTER_CLICK_S: Final = 0.35  # tools.mjs:758
_MAX_NOTE: Final = 300
_MAX_SAID: Final = 240

Outcome = Literal["started", "clicked", "hovered", "skipped", "timeout", "stopped", "discarded"]


def plain(text: str) -> str:
    """intro.mjs:64 `plain`, con las etiquetas de expresión de Drakter (`speech_markup.strip_tags`)."""
    s = strip_tags(str(text or ""))
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ([,.!?])", r"\1", s)
    return s.strip()


def _cut(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


@dataclass
class Guide:
    guide_id: UUID
    turn_id: UUID
    session_id: UUID
    call_id: str
    target: str
    beats: list[dict[str, Any]]
    edits: list[dict[str, Any]]
    deep: bool
    next: int = 0
    waiting: tuple[int, str] | None = None  # (n, 'click'|'hover')
    finished: bool = False
    stopped: bool = False
    said: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    drawn: list[str] = field(default_factory=list)
    shut: list[str] = field(default_factory=list)
    missing: list[MissingTarget] = field(default_factory=list)
    speech_ids: set[int] = field(default_factory=set)
    futures: dict[tuple[str, int], asyncio.Future[Outcome]] = field(default_factory=dict)

    @property
    def segs(self) -> int:
        return max(1, len(self.beats))  # tools.mjs:701


class DrawRunner:
    def __init__(self) -> None:
        self._hub: Any = None
        self._voice: Any = None
        self._runtime: Any = None
        self._watch: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.ink = InkState(self._publish)
        self.guides: dict[UUID, Guide] = {}
        self.active = 0  # tools.mjs:709 (ink.active)
        self.last_session: UUID | None = None
        self._hands_off: list[Callable[[], None]] = []
        presence.on_presence(self._on_presence)

    # ── enganche con el backend ──────────────────────────────────────────────
    def bind(self, state: Any) -> None:
        """`state` es el `tool_state` del runtime (herramientas) o `app.state` (REST)."""
        runtime = getattr(state, "agent_runtime", None)
        if runtime is not None:
            self._runtime = runtime
            self._hub = getattr(runtime, "hub", None) or self._hub
        self._hub = self._hub or getattr(state, "event_hub", None)
        voice = getattr(state, "voice", None)
        if voice is not None:
            self._voice = voice
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        if self._hub is not None and (self._watch is None or self._watch.done() or self._loop is not loop):
            self._loop = loop
            self._watch = loop.create_task(self._watch_hub(self._hub))
        if not self._hands_off:
            for kind in ("focus.changed", "windows.changed"):
                off = ports.on_hands_event(kind, lambda evt, kind=kind: self._on_hands(kind, evt))
                if off is not None:
                    self._hands_off.append(off)

    def _publish(self, type: str, payload: Any) -> None:
        if self._hub is None:
            logger.warning("no hub: %s dropped", type, extra={"event": "floating_publish_no_hub"})
            return
        try:
            self._hub.publish(type, payload)
        except Exception:  # noqa: BLE001
            logger.exception("overlay publish failed", extra={"event": "floating_publish_failed"})

    # ── herramientas ─────────────────────────────────────────────────────────
    async def draw(self, *, turn_id: UUID, session_id: UUID, call_id: str, args: dict[str, Any]) -> DrawToolResult:
        """`args` ya validados (`validate.validate_draw`). tools.mjs:680-771."""
        self._require_floating()
        if any(g.turn_id == turn_id and not g.finished for g in self.guides.values()):
            raise ToolError("guide_busy", "There is a walkthrough playing in this turn: call guide_wait or wait for it.")
        ink = self.ink
        edits = list(args.get("edit") or [])
        # tools.mjs:691
        for e in edits:
            if e["do"] != "clear" and not ink.parts.has(e.get("part")):
                there = f" (there is: {ink.parts.describe()})" if ink.parts.ids else " (nothing is drawn)"
                raise ToolError("part_not_found", f"There's no {e.get('part')} on screen now{there}. Draw it again instead.")
        # Un dibujo de otro turno para lo que quedara sonando (CONTRACT.md §9.3).
        for g in list(self.guides.values()):
            if g.turn_id != turn_id and not g.finished:
                self._stop(g)
        # tools.mjs:694-697
        if ink.turn != turn_id and not edits and ink.parts.ids:
            if args.get("keep"):
                ink.clear_screen_ink(True)
            else:
                ink.clear_all_ink()
        if ink.turn != turn_id:
            ink.fresh = set()
        ink.turn = turn_id
        for e in edits:
            if e["do"] == "erase":
                ink.parts.remove(e["part"])
                ink.buttons.pop(e["part"], None)
            elif e["do"] == "clear":
                ink.parts.clear()
                ink.buttons.clear()
                ink.pinned.clear()
        guide = Guide(
            guide_id=uuid4(), turn_id=turn_id, session_id=session_id, call_id=call_id[:64],
            target=str(args.get("target") or "front"), beats=list(args.get("beats") or []), edits=edits,
            deep=bool(args.get("deep")),
        )
        self.guides[guide.guide_id] = guide
        said0, notes0, drawn0 = 0, 0, 0
        try:
            status = await self._play(guide)
        except BaseException:
            self._finish(guide)
            raise
        pure_edit = not guide.beats
        return DrawToolResult(
            guide_id=guide.guide_id,
            status="edited" if pure_edit else status,
            waiting_beat=guide.waiting[0] if status == "waiting" and guide.waiting else None,
            wait=guide.waiting[1] if status == "waiting" and guide.waiting else None,  # type: ignore[arg-type]
            drawn=[d for d in (ink.drawn_part(p) for p in guide.drawn[drawn0:]) if d is not None],
            on_screen=ink.on_screen(),
            missing=guide.missing,
            said=guide.said[said0:],
            notes=self._notes(guide, notes0, said0, status),
        )

    async def guide_wait(self, guide_id: UUID) -> GuideWaitResult:
        """CONTRACT.md §8.2 `guide_wait`."""
        guide = self.guides.get(guide_id)
        if guide is None or guide.finished or guide.waiting is None:
            raise ToolError("guide_not_found", "No walkthrough with that guide_id is waiting (it finished or never started).")
        if not presence.is_active():
            self._stop(guide)
            raise ToolError("floating_inactive", "El modo flotante no está activo.")
        n, w = guide.waiting
        fut = guide.futures.get(("wait", n)) or self._future(guide, "wait", n)
        said0, notes0 = len(guide.said), len(guide.notes)
        try:
            r = await asyncio.wait_for(asyncio.shield(fut), WAIT_CLICK_S if w == "click" else WAIT_HOVER_S)
        except TimeoutError:
            r = "timeout"
        except BaseException:
            self._stop(guide)
            raise
        guide.waiting = None
        if r == "stopped" or guide.stopped:
            self._finish(guide)
            raise ToolError("interrupted", "The user stopped the walkthrough (voice, Esc or clearing the drawing).")
        result: Literal["clicked", "hovered", "timeout", "skipped"] = r if r in ("clicked", "hovered", "skipped") else "timeout"  # type: ignore[assignment]
        # tools.mjs:754-755
        if result == "timeout":
            guide.notes.append(f"Paso {n}: nadie hizo {'clic' if w == 'click' else 'hover'} en {int(WAIT_CLICK_S if w == 'click' else WAIT_HOVER_S)} s, así que paré ahí.")
            self._finish(guide)
            status: Literal["waiting", "done", "stopped"] = "done"
        else:
            verb = {"clicked": "hizo clic", "hovered": "pasó el ratón", "skipped": "se saltó la espera"}[result]
            guide.notes.append(f"El usuario {verb} en el paso {n}.")
            # tools.mjs:757-758: la pantalla ha cambiado bajo la captura anterior.
            ports.invalidate_turn_views(guide.turn_id)
            await asyncio.sleep(AFTER_CLICK_S)
            try:
                status = await self._play(guide)
            except BaseException:
                self._finish(guide)
                raise
        return GuideWaitResult(
            guide_id=guide.guide_id,
            beat=n,
            result=result,
            status=status,
            waiting_beat=guide.waiting[0] if status == "waiting" and guide.waiting else None,
            wait=guide.waiting[1] if status == "waiting" and guide.waiting else None,  # type: ignore[arg-type]
            said=guide.said[said0:],
            notes=self._notes(guide, notes0, said0, status),
        )

    # ── reproducción ─────────────────────────────────────────────────────────
    async def _play(self, guide: Guide) -> Literal["waiting", "done"]:
        """Envía segmentos desde `guide.next` hasta un beat con espera o el final (tools.mjs:713-759)."""
        ink = self.ink
        beats = guide.beats
        self.active += 1
        try:
            while guide.next < guide.segs:
                k = guide.next
                if guide.stopped:
                    raise ToolError("interrupted", "Stopped.")
                after = k > 0 and bool(beats[k - 1].get("wait"))
                try:
                    seg = await ports.resolve_marks(
                        beats[k : k + 1], target=guide.target, turn_id=guide.turn_id, after_wait=after
                    ) if beats else ports.Seg(beats=[{"say": "", "marks": [], "wait": None}])
                    self._prepare(seg, k, guide)
                except ToolError as exc:
                    if not k:
                        raise
                    guide.notes.append(_cut(f"Paré antes del paso {k + 1}: {exc.message}", _MAX_NOTE))
                    break
                except Exception as exc:  # noqa: BLE001 - un objetivo que no se resuelve
                    if not k:
                        raise ToolError("draw_invalid", str(exc)[:2000]) from exc
                    guide.notes.append(_cut(f"Paré antes del paso {k + 1}: {exc}", _MAX_NOTE))
                    break
                if guide.stopped:
                    raise ToolError("interrupted", "Stopped.")
                seg_beats = seg.beats[:1]
                ids = ink.parts.assign(seg_beats)  # tools.mjs:729
                ink.fresh.update(ids)
                guide.drawn.extend(ids)
                # tools.mjs:736: solo unas pocas tarjetas a la vez; en `deep`, una.
                for p in ink.parts.trim_cards(1 if guide.deep else drawjs.LIMITS["cardsShown"],
                                              lambda q: q in ink.loose or q in ink.pinned):
                    guide.shut.append(p)
                    ink.buttons.pop(p, None)
                for b in seg_beats:  # tools.mjs:737
                    for m in b["marks"]:
                        if m.get("action") and m.get("part"):
                            ink.buttons[m["part"]] = dict(m["action"])
                out = []
                for j, b in enumerate(seg_beats):  # tools.mjs:741
                    n = k + j + 1
                    caption = plain(b.get("say") or "")
                    speech_id: int | None = None
                    voiced = False
                    if caption and beats:
                        sid = ports.reserve_speech_id(self._voice)
                        voiced = await ports.speak_beat(
                            self._voice, str(guide.turn_id), sid, str(guide.guide_id), n, caption[:_MAX_SAID]
                        )
                        if voiced:
                            speech_id = sid
                            guide.speech_ids.add(sid)
                    beat = {
                        "say": b.get("say") or "", "marks": b["marks"][: drawjs.LIMITS["marks"]],
                        "wait": b.get("wait") or None, "n": n, "caption": caption[:_MAX_SAID], "voiced": voiced,
                    }
                    if guide.deep and n < len(beats):
                        beat["read"] = drawjs.read_secs(b["marks"])
                    out.append((beat, speech_id))
                if beats:
                    guide.said.extend(_cut(b["caption"], _MAX_SAID) for b, _ in out if b["caption"])
                last = k == guide.segs - 1
                beat, speech_id = out[0]
                payload = OverlayDraw(
                    guide_id=guide.guide_id, turn_id=guide.turn_id, call_id=guide.call_id, seg=k, last=last,
                    beats=[beat], edits=[] if k else guide.edits, win=seg.win, busy=[] if k else seg.busy[:300],
                    deep=True if guide.deep else None, speech_id=speech_id,
                )
                started = self._future(guide, "start", k) if not k else None
                w = beat["wait"]
                if w:
                    self._future(guide, "wait", beat["n"])
                self._publish("overlay.draw", payload)
                guide.next = k + 1
                # tools.mjs:745-749: el primer segmento tiene que verse.
                if started is not None:
                    try:
                        r = await asyncio.wait_for(asyncio.shield(started), START_TIMEOUT_S)
                    except TimeoutError:
                        r = "timeout"
                    if r == "stopped":
                        raise ToolError("interrupted", "Stopped.")
                    if r != "started":
                        raise ToolError("overlay_unavailable", "The drawing didn't show (the overlay isn't responding).")
                if w:
                    guide.waiting = (beat["n"], w)
                    return "waiting"
        finally:
            self.active -= 1
        self._finish(guide)
        return "done"

    def _prepare(self, seg: ports.Seg, k: int, guide: Guide) -> None:
        """Lo que en Roamies hacen `resolveTargets` (draw.mjs:416-421) y `prepare` (tools.mjs:646-663) tras resolver.

        Drakter no descarga nada en v1: `photo` sale con `missing:true` y las fuentes sin favicon (CONTRACT.md §9.1).
        """
        for b in seg.beats:
            marks = []
            for m in b.get("marks") or []:
                o = drawjs.enrich_mark(m)
                if o.get("kind") == "photo":
                    o["missing"] = True
                    guide.notes.append(_cut(f"No hay foto de {o.get('query') or 'ese enlace'} (en Drakter no se descargan imágenes): dibujé solo el marco y el pie.", _MAX_NOTE))
                marks.append(o)
            b["marks"] = marks
        for miss in seg.missing:
            guide.missing.append(miss.model_copy(update={"beat": min(12, k + miss.beat)}))

    # ── fin, paradas y notas ─────────────────────────────────────────────────
    def _future(self, guide: Guide, kind: str, n: int) -> asyncio.Future[Outcome]:
        fut: asyncio.Future[Outcome] = asyncio.get_running_loop().create_future()
        guide.futures[(kind, n)] = fut
        return fut

    @staticmethod
    def _resolve(guide: Guide, key: tuple[str, int], value: Outcome) -> bool:
        fut = guide.futures.get(key)
        if fut is None or fut.done():
            return False
        fut.set_result(value)
        return True

    def _finish(self, guide: Guide) -> None:
        guide.finished = True
        guide.waiting = None
        for fut in guide.futures.values():
            if not fut.done():
                fut.set_result("stopped")

    def _stop(self, guide: Guide) -> None:
        guide.stopped = True
        self._finish(guide)

    def stop_all(self, *, cancelled: bool = False, turn_id: UUID | None = None) -> None:
        """tools.mjs:795-798 (`inkEvents.stop`)."""
        stopped = False
        for g in list(self.guides.values()):
            if not g.finished and (turn_id is None or g.turn_id == turn_id):
                self._stop(g)
                stopped = True
        if cancelled and self.ink.turn == turn_id and self.ink.parts.ids:
            self.ink.cancel_ink()
        elif stopped:
            self.ink.clear_screen_ink(True)

    def _notes(self, guide: Guide, notes0: int, said0: int, status: str) -> list[str]:
        """tools.mjs:762-770, en español para el modelo."""
        notes = [_cut(n, _MAX_NOTE) for n in guide.notes[notes0:]]
        if guide.finished and guide.shut:
            notes.append(_cut(
                f"Una explicación a fondo enseña una tarjeta cada vez: se cerraron {', '.join(guide.shut)}."
                if guide.deep else
                f"Solo caben {drawjs.LIMITS['cardsShown']} tarjetas a la vez: se cerraron las más antiguas ({', '.join(guide.shut)}).",
                _MAX_NOTE,
            ))
        if status == "waiting" and guide.waiting:
            what = "el clic" if guide.waiting[1] == "click" else "el hover"
            notes.append(f"Llama a guide_wait con guide_id={guide.guide_id} para esperar {what}.")
        if any(m.get("kind") == "quiz" for b in guide.beats for m in b.get("marks") or []):
            notes.append("El usuario responde el test haciendo clic en la tarjeta: no le preguntes las respuestas ni la nota.")
        spoken = [s for s in guide.said[said0:] if s]
        if spoken:
            heard = "Ya dicho en voz alta mientras dibujaba: " + " ".join(f"«{s}»" for s in spoken)
            notes.append(_cut(heard, _MAX_NOTE - 70) + " No lo repitas ni lo reformules en tu respuesta.")
        return notes[:20]

    def _require_floating(self) -> None:
        p = presence.current_presence()
        if p is None or not p.active:
            raise ToolError("floating_inactive", "El modo flotante no está activo: actívalo con ui_set_floating.")
        if p.companion != "ok":
            raise ToolError("companion_unavailable", "La extensión de GNOME no responde.")
        if not p.ready:
            raise ToolError("overlay_unavailable", "La ventana flotante aún no está lista.")

    # ── eventos de la página (POST /api/v1/overlay/events) ──────────────────
    async def client_event(self, event: OverlayClientEvent, *, state: Any = None) -> bool:
        """False = la guía o la parte ya no existe (404). tools.mjs:773-803 y sidekick.mjs:3040-3050."""
        if state is not None:
            self.bind(state)
        kind = event.type
        if kind in ("draw_started", "draw_done", "draw_wait_done"):
            guide = self.guides.get(event.guide_id)  # type: ignore[union-attr]
            if guide is None or guide.finished:
                return False
            if kind == "draw_started":
                self._resolve(guide, ("start", event.seg), "started")  # type: ignore[union-attr]
            elif kind == "draw_wait_done":
                r = event.result  # type: ignore[union-attr]
                # tools.mjs:775: lo que no es clicked/hovered/skipped cuenta como skipped.
                self._resolve(guide, ("wait", event.beat), r if r in ("clicked", "hovered", "skipped") else "skipped")  # type: ignore[union-attr,arg-type]
            else:
                # D2 descarta un segmento inválido y manda draw_done para que la guía no se quede colgada (§9.5).
                for (k, n), fut in guide.futures.items():
                    if not fut.done():
                        fut.set_result("discarded" if k == "start" else "skipped")
            return True
        if kind == "ink_closed":
            self.ink.closed(event.part)  # type: ignore[union-attr]
            return True
        if kind == "ink_pinned":
            self.ink.pin(event.part, event.on)  # type: ignore[union-attr]
            return True
        if kind == "ink_cleared":
            # tools.mjs:800: Esc o «borrar todo»
            for g in list(self.guides.values()):
                if not g.finished:
                    self._stop(g)
            self.ink.forget_ink()
            return True
        if kind == "ink_action":
            return await self._ink_action(event.part)  # type: ignore[union-attr]
        return False

    async def _ink_action(self, part: str) -> bool:
        """CONTRACT.md §9.3 `ink_action`: la acción guardada para la parte; la página nunca manda el valor."""
        action = self.ink.buttons.get(part)
        if not action:
            return False
        do, value = action.get("do"), str(action.get("value") or "")
        if do == "copy":
            self._publish("overlay.clipboard", OverlayClipboard(part=part, text=value[:600]))
        elif do == "open":
            # check_url_dns too: a public name may resolve to this machine, and one that does not
            # resolve is blocked (security review M1).
            if check_url(value).level == BLOCK or await asyncio.to_thread(check_url_dns, value) is not None:
                logger.warning("button url blocked", extra={"event": "floating_button_url_blocked"})
                return True
            await ports.open_url(value)
        elif do == "ask":
            runtime = self._runtime
            if runtime is None or runtime.active_turn() is not None:
                return True  # con un turno en curso, se descarta
            session = self.last_session
            if session is None:
                created = await runtime.create_session()
                session = created.id if hasattr(created, "id") else created.session_id
            await runtime.submit_message(session, value[:4000], None)
        return True

    # ── vigilancia: voz, turnos, presencia y pantalla ───────────────────────
    async def _watch_hub(self, hub: Any) -> None:
        while True:
            sub = hub.subscribe(None, None)
            try:
                while True:
                    envelope = await sub.queue.get()
                    kind = getattr(envelope, "type", None)
                    if kind is None:  # CLOSE: we lagged; subscribe again
                        break
                    try:
                        self._on_envelope(kind, envelope.payload or {})
                    except Exception:  # noqa: BLE001
                        logger.exception("floating watcher failed", extra={"event": "floating_watch_failed"})
            finally:
                hub.unsubscribe(sub)

    def _on_envelope(self, kind: str, payload: dict[str, Any]) -> None:
        if kind == "agent.turn_started":
            try:
                self.last_session = UUID(str(payload.get("session_id")))
            except ValueError:
                pass
        elif kind == "voice.playback" and payload.get("state") == "interrupted":
            sid = payload.get("speech_id")
            for g in list(self.guides.values()):
                if not g.finished and sid in g.speech_ids:
                    # Barge-in sobre un beat: para la guía y lo que está sonando (CONTRACT.md §9.3).
                    self._stop(g)
                    self.ink.clear_screen_ink(True, guide_id=g.guide_id)
        elif kind == "agent.turn_finished":
            try:
                turn = UUID(str(payload.get("turn_id")))
            except ValueError:
                return
            outcome = payload.get("outcome")
            if outcome in ("cancelled", "interrupted"):
                self.stop_all(cancelled=True, turn_id=turn)
            else:
                for g in list(self.guides.values()):
                    if g.turn_id == turn:
                        self._finish(g)
                # tools.mjs:792 (endRequest): un turno que no dibujó retira las marcas de pantalla de antes.
                if self.ink.turn != turn and self.ink.parts.screen_count:
                    self.ink.clear_screen_ink()
            for gid in [gid for gid, g in self.guides.items() if g.finished]:
                del self.guides[gid]

    def _on_presence(self, p: FloatingPresence | None) -> None:
        if p is not None and not p.active:
            loop = self._loop
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(self._deactivated)
            else:
                self._deactivated()

    def _deactivated(self) -> None:
        for g in list(self.guides.values()):
            if not g.finished:
                self._stop(g)
        self.ink.forget_ink()

    def _on_hands(self, kind: str, evt: Any) -> None:
        """`overlay.ink_stale` una vez por cambio, con marcas de pantalla vistas y nada sonando ni esperando."""
        reason = getattr(evt, "reason", None)
        if kind == "windows.changed" and reason not in ("geometry", "closed"):
            return
        if self.active or any(g.waiting for g in self.guides.values() if not g.finished):
            return
        if not self.ink.window_bound() or not self.ink.parts.screen_count:
            return
        why: Literal["focus_changed", "window_moved", "window_closed"] = (
            "focus_changed" if kind == "focus.changed" else "window_closed" if reason == "closed" else "window_moved"
        )
        self.ink.forget_ink()  # tools.mjs:516-523 (screenChanged)
        loop = self._loop
        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._publish, "overlay.ink_stale", OverlayInkStale(reason=why))
        else:
            self._publish("overlay.ink_stale", OverlayInkStale(reason=why))


RUNNER: Final = DrawRunner()
