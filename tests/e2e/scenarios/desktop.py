"""Escritorio real: la ventana de Electron recorrida por CDP.

Lo que el árbol del escritorio aún no tiene (backend conectado, chat real, personaje real,
confirmaciones) se detecta por ausencia de la capacidad y da NO COMPROBADO, nunca PASA ni FALLA.
"""
from __future__ import annotations

import json
import re
import time

from harness.cdp import Cdp, find_page
from harness.model import NotChecked, check

# Contrato del puente (desktop/electron/shared/bridge.ts): ni una función más.
BRIDGE_API = ["getAppInfo", "reportRendererError", "showDesktopNotification"]
STUB_MARK = "[DEV-STUB]"
CHAT_PROMPT = "[stub:conversacion] hola"

# Ruido de Chromium que se ignora SOLO si aparece en consola. Cada patrón debe estar demostrado
# en una pasada real; con la lista vacía todo error de consola o excepción es FALLA.
IGNORED_NOISE: tuple[str, ...] = ()


def _cdp(ctx) -> Cdp:
    if ctx.cdp is None:
        raise NotChecked("sin conexión CDP: desktop.arranca no llegó a conectar con la ventana")
    return ctx.cdp


def _q(value: str) -> str:
    return json.dumps(value)


def _settle(cdp: Cdp, seconds: float = 0.4) -> None:
    """Espera fuentes cargadas y un par de fotogramas antes de capturar o leer."""
    cdp.evaluate("document.fonts.ready.then(() => new Promise(r => requestAnimationFrame(() => "
                 "requestAnimationFrame(r))))")
    time.sleep(seconds)


def _shot(ctx, name: str):
    _settle(ctx.cdp)
    return ctx.cdp.screenshot(ctx.report_dir / "capturas" / f"{name}.png")


def _mark(cdp: Cdp, finder: str, tag: str, timeout: float = 10) -> None:
    """Etiqueta con data-e2e el elemento que devuelve `finder` para poder pulsarlo con ratón real."""
    cdp.wait_for(f"(() => {{ document.querySelectorAll('[data-e2e={_q(tag)}]').forEach("
                 f"e => e.removeAttribute('data-e2e')); const el = ({finder}); if (!el) return false;"
                 f" el.setAttribute('data-e2e', {_q(tag)}); return true; }})()", timeout)


def _find_button(pattern: str) -> str:
    return (f"[...document.querySelectorAll('button')].find(b => !b.disabled && "
            f"b.getAttribute('aria-disabled') !== 'true' && /{pattern}/i.test("
            f"(b.innerText || '') + ' ' + (b.getAttribute('aria-label') || '')))")


def _go(cdp: Cdp, href: str) -> None:
    cdp.click(f'nav a[href="{href}"]')
    cdp.wait_for(f'document.querySelector(\'nav a[href="{href}"]\')?.getAttribute("aria-current") === "page"')


def _main_text(cdp: Cdp) -> str:
    return cdp.evaluate("(document.querySelector('main') || document.body).innerText.trim()")


def _sections(cdp: Cdp) -> list[dict]:
    return cdp.evaluate("[...document.querySelectorAll('nav a[href^=\"#/\"]')].map(a => "
                        "({href: a.getAttribute('href'), label: a.innerText.trim()}))")


# --- arranque y ventana ----------------------------------------------------------------


@check("desktop.arranca", "Electron abre la ventana y React pinta la interfaz", phase="desktop", needs=())
def starts(ctx):
    if "desktop" in ctx.stack.failed:
        raise AssertionError(ctx.stack.why_unavailable("desktop"))
    if not ctx.stack.available("desktop"):
        raise NotChecked(ctx.stack.why_unavailable("desktop"))
    proc = ctx.stack.procs["desktop"]
    assert proc.poll() is None, f"Electron salió con código {proc.returncode}; ver desktop.log"
    try:
        ctx.cdp = Cdp(find_page(ctx.stack.cdp_port))
    except Exception as exc:  # noqa: BLE001 - sin CDP no hay nada que recorrer: es un fallo del arranque.
        raise AssertionError(f"sin ventana por CDP: {exc}") from exc
    cdp = ctx.cdp
    cdp.wait_for("document.readyState === 'complete'", 30)
    cdp.wait_for("(() => { const r = document.getElementById('root');"
                 " return !!r && r.children.length > 0 && r.innerText.trim().length > 0; })()", 30)
    _settle(cdp)
    info = cdp.evaluate("({title: document.title, w: innerWidth, h: innerHeight,"
                        " dark: document.documentElement.classList.contains('dark')})")
    return f"ventana «{info['title']}» {info['w']}x{info['h']}, readyState=complete y #root con contenido"


@check("desktop.ventana_segura", "El renderer está aislado: sin Node, puente mínimo y CSP", phase="desktop",
       needs=("desktop",))
def secure_window(ctx):
    cdp = _cdp(ctx)
    probe = cdp.evaluate("({require: typeof require, process: typeof process, module: typeof module,"
                         " Buffer: typeof Buffer, global: typeof global,"
                         " bridge: typeof window.drakter,"
                         " keys: window.drakter ? Object.keys(window.drakter).sort() : null,"
                         " kinds: window.drakter ? Object.values(window.drakter).map(v => typeof v) : null,"
                         " csp: document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]')"
                         "?.getAttribute('content') ?? null})")
    leaks = {k: probe[k] for k in ("require", "process", "module", "Buffer", "global") if probe[k] != "undefined"}
    assert not leaks, f"el renderer ve globales de Node: {leaks}"
    assert probe["bridge"] == "object", f"window.drakter es {probe['bridge']}"
    assert probe["keys"] == BRIDGE_API, f"puente con {probe['keys']}, el contrato es {BRIDGE_API}"
    assert set(probe["kinds"]) == {"function"}, f"el puente expone algo que no es función: {probe['kinds']}"
    csp = probe["csp"]
    assert csp, "no hay <meta> Content-Security-Policy"
    assert "default-src 'none'" in csp and "script-src 'self'" in csp, f"CSP débil: {csp}"
    assert "'unsafe-eval'" not in csp and "script-src 'self' 'unsafe-inline'" not in csp, f"CSP permisiva: {csp}"
    return f"sin require/process/module/Buffer; window.drakter = {BRIDGE_API}; CSP default-src 'none', script-src 'self'"


# --- navegación ------------------------------------------------------------------------


@check("desktop.navegacion", "Cada sección del lateral abre una página con contenido", phase="desktop",
       needs=("desktop",))
def navigation(ctx):
    cdp = _cdp(ctx)
    sections = _sections(cdp)
    assert len(sections) >= 2, f"el lateral expone {len(sections)} secciones: {sections}"
    seen: dict[str, str] = {}
    previous = _main_text(cdp)
    notes: list[str] = []
    for section in sections:
        href, label = section["href"], section["label"]
        already = cdp.evaluate(f'document.querySelector(\'nav a[href="{href}"]\')?.getAttribute("aria-current") === "page"')
        _go(cdp, href)
        cdp.wait_for("(document.querySelector('main') || document.body).innerText.trim().length > 20")
        _settle(cdp)
        text = _main_text(cdp)
        assert not cdp.evaluate("!!document.querySelector('main [role=\"alert\"]')"), \
            f"«{label}» muestra un error de sección: {text[:120]!r}"
        heading = cdp.evaluate("(document.querySelector('main h1') || {}).innerText || ''").strip()
        assert heading, f"«{label}» no tiene título h1"
        assert len(text) > 40, f"«{label}» casi vacía: {text!r}"
        assert already or text != previous, f"«{label}» no cambió el contenido respecto a la anterior"
        assert text not in seen.values(), f"«{label}» repite el contenido de otra sección"
        # Una página cuyo cuerpo no ocupa nada o se desborda en horizontal está rota aunque tenga texto.
        geometry = cdp.evaluate("(() => { const m = document.querySelector('main') || document.body;"
                                " return {h: m.scrollHeight, over: document.documentElement.scrollWidth"
                                " > innerWidth + 1}; })()")
        assert geometry["h"] > 100 and not geometry["over"], f"«{label}» con geometría rota: {geometry}"
        seen[href] = text
        previous = text
        _shot(ctx, f"nav-{href.removeprefix('#/')}")
        notes.append(label)
    ctx.state["desktop_sections"] = [s["href"] for s in sections]
    return f"{len(sections)} secciones recorridas con clic real ({', '.join(notes)}); capturas en capturas/nav-*.png"


# --- configuración y notificaciones -----------------------------------------------------


@check("desktop.configuracion", "Una preferencia inocua cambia y su efecto se ve", phase="desktop",
       needs=("desktop",))
def settings(ctx):
    cdp = _cdp(ctx)
    if "#/settings" not in [s["href"] for s in _sections(cdp)]:
        raise NotChecked("el lateral no tiene sección de ajustes (#/settings)")
    _go(cdp, "#/settings")
    cdp.wait_for("!!document.querySelector('main [role=\"switch\"]')")
    _mark(cdp, "document.querySelector('#setting-reduce-motion') || document.querySelector('main [role=\"switch\"]')",
          "pref")
    read = ("({checked: document.querySelector('[data-e2e=pref]').getAttribute('aria-checked'),"
            " motion: document.documentElement.dataset.reduceMotion})")
    before = cdp.evaluate(read)
    assert before["motion"] in ("true", "false"), f"el documento no refleja la preferencia: {before}"
    cdp.click("[data-e2e=pref]")
    cdp.wait_for(f"document.documentElement.dataset.reduceMotion !== {_q(before['motion'])}")
    after = cdp.evaluate(read)
    assert after["checked"] != before["checked"], f"el interruptor no cambió: {before} → {after}"
    assert cdp.evaluate("localStorage.length") > 0, "la preferencia no se guardó en el almacenamiento local"
    _shot(ctx, "ajustes-reducir-movimiento")
    cdp.click("[data-e2e=pref]")  # se deja como estaba
    cdp.wait_for(f"document.documentElement.dataset.reduceMotion === {_q(before['motion'])}")
    return (f"«Reducir movimiento»: aria-checked {before['checked']}→{after['checked']}, "
            f"<html data-reduce-motion> {before['motion']}→{after['motion']}, guardada y restaurada")


@check("desktop.notificaciones", "Una notificación de la interfaz aparece como aviso y en el centro",
       phase="desktop", needs=("desktop",))
def notifications(ctx):
    cdp = _cdp(ctx)
    if "#/settings" not in [s["href"] for s in _sections(cdp)]:
        raise NotChecked("no hay sección de ajustes desde la que disparar la notificación de prueba")
    _go(cdp, "#/settings")
    try:
        _mark(cdp, _find_button("notificaci[oó]n de prueba"), "notify", timeout=5)
    except AssertionError as exc:
        raise NotChecked("la interfaz no ofrece un disparador de notificación de prueba") from exc
    bell = "document.querySelector('button[aria-label^=\"Notificaciones\"]')?.getAttribute('aria-label')"
    before = cdp.evaluate(bell)
    cdp.click("[data-e2e=notify]")
    cdp.wait_for("[...document.querySelectorAll('[data-sonner-toast]')].some(t => /prueba/i.test(t.innerText))", 8)
    _shot(ctx, "notificacion-aviso")
    after = cdp.wait_for(f"(() => {{ const l = {bell}; return l !== {_q(before)} ? l : null; }})()", 5)
    assert "sin leer" in after, f"la campana no marca la notificación como no leída: {after!r}"
    cdp.click("button[aria-label^=\"Notificaciones\"]")
    cdp.wait_for("[...document.querySelectorAll('[role=\"dialog\"]')].some(d => /prueba/i.test(d.innerText))")
    _shot(ctx, "notificacion-centro")
    cdp.press("Escape")
    return (f"aviso emergente visible, campana «{before}» → «{after}» y entrada en el centro de notificaciones "
            "(el aviso nativo del sistema no es observable por CDP)")


# --- capacidades que dependen de otras ramas -------------------------------------------


def _status_text(cdp: Cdp) -> str:
    return cdp.evaluate("document.querySelector('[role=\"status\"]')?.innerText.trim() ?? ''")


@check("desktop.conexion_backend", "La interfaz muestra el backend conectado", phase="desktop",
       needs=("desktop", "backend"))
def backend_connection(ctx):
    cdp = _cdp(ctx)
    if "#/home" in [s["href"] for s in _sections(cdp)]:
        _go(cdp, "#/home")
    status = _status_text(cdp)
    if not status:
        raise NotChecked("la interfaz no tiene indicador de estado ([role=status]) que comprobar")
    if re.search(r"desconectad|a[uú]n no est[aá] conectado", status, re.I):
        # El árbol actual declara «offline» a propósito con el texto «Aún no está conectado»: no hay
        # cliente del backend. Un «Desconectado» sin esa nota, con el backend vivo, sí es un fallo.
        if re.search(r"a[uú]n no est[aá] conectado", status, re.I):
            raise NotChecked(f"el escritorio aún no habla con el backend: el indicador dice {status!r} "
                             "(sin cliente REST/WebSocket en esta rama; el backend sí está vivo)")
        raise AssertionError(f"backend vivo pero la interfaz muestra {status!r}")
    _shot(ctx, "estado-conectado")
    return f"indicador de estado: {status!r} con el backend vivo"


@check("desktop.conversacion", "El chat envía un mensaje y muestra la respuesta del stub", phase="desktop",
       needs=("desktop", "backend", "stub", "hermes"), uses_stub=True)
def conversation(ctx):
    cdp = _cdp(ctx)
    composer = "document.querySelector('textarea[aria-label=\"Mensaje para Drakter\"]')"
    if not cdp.evaluate(f"!!{composer}"):
        raise NotChecked("no existe el campo de chat «Mensaje para Drakter»")
    if cdp.evaluate(f"{composer}.disabled"):
        raise NotChecked("el chat existe pero está deshabilitado: el escritorio aún no tiene envío "
                         "conectado al backend (SEND_WIRED=false)")
    count = "(document.body.innerText.split(" + _q(STUB_MARK) + ").length - 1)"
    before = cdp.evaluate(count)
    cdp.evaluate("window.__e2eStates = []; new MutationObserver(() => { document.querySelectorAll("
                 "'[data-character-state]').forEach(e => { const s = e.dataset.characterState;"
                 " if (window.__e2eStates.at(-1) !== s) window.__e2eStates.push(s); }); })"
                 ".observe(document.body, {subtree: true, attributes: true, childList: true,"
                 " attributeFilter: ['data-character-state']}); "
                 "document.querySelectorAll('[data-character-state]').forEach(e => window.__e2eStates"
                 ".push(e.dataset.characterState));")
    cdp.evaluate(f"{composer}.focus()")
    cdp.type_text(CHAT_PROMPT)
    cdp.press("Enter")
    cdp.wait_for(f"{count} > {before}", 30)
    ctx.state["desktop_character_states"] = cdp.evaluate("window.__e2eStates")
    _shot(ctx, "conversacion")
    return f"enviado «{CHAT_PROMPT}» y {STUB_MARK} apareció en el DOM (evidencia del stub, no de Haiku)"


@check("desktop.personaje", "El personaje expone un estado y cambia con eventos reales", phase="desktop",
       needs=("desktop",))
def character(ctx):
    cdp = _cdp(ctx)
    if "#/home" in [s["href"] for s in _sections(cdp)]:
        _go(cdp, "#/home")
    states = cdp.evaluate("[...document.querySelectorAll('[data-character-state]')]"
                          ".map(e => e.dataset.characterState)")
    if not states:
        raise NotChecked("no hay ningún elemento [data-character-state] en la portada")
    valid = {"idle", "listening", "thinking", "speaking", "executing", "success", "error", "interrupted", "offline"}
    assert set(states) <= valid, f"estado fuera del contrato: {states}"
    drawn = cdp.evaluate("!!document.querySelector('[data-character-state]')?.querySelector('svg, canvas')")
    seen = ctx.state.get("desktop_character_states")
    if not seen:
        raise NotChecked(f"el personaje expone {states[0]!r}"
                         + ("" if drawn else " (hueco de plano, sin personaje dibujado)")
                         + ", pero sin eventos reales no se puede ver que cambie: depende de desktop.conversacion")
    distinct = list(dict.fromkeys(seen))
    assert len(distinct) >= 2, f"el estado no cambió con la conversación: {distinct}"
    return f"estados observados durante la conversación: {' → '.join(distinct)}"


@check("desktop.confirmacion", "Una acción destructiva pide confirmación y cancelar conserva el dato",
       phase="desktop", needs=("desktop",))
def confirmation(ctx):
    cdp = _cdp(ctx)
    destructive = _find_button(r"(elimin|borr)")
    for section in ctx.state.get("desktop_sections") or [s["href"] for s in _sections(cdp)]:
        _go(cdp, section)
        if not cdp.evaluate(f"!!({destructive})"):
            continue
        _mark(cdp, destructive, "destroy", timeout=2)
        row = cdp.evaluate("(() => { const b = document.querySelector('[data-e2e=destroy]');"
                           " const r = b.closest('li, tr, article, [role=row]'); return r ? r.innerText.trim() : ''; })()")
        assert row, f"{section}: el botón destructivo no está dentro de un elemento identificable"
        label = cdp.evaluate("(() => { const b = document.querySelector('[data-e2e=destroy]');"
                             " return (b.innerText || b.getAttribute('aria-label') || '').trim(); })()")
        cdp.click("[data-e2e=destroy]")
        try:
            cdp.wait_for("!!document.querySelector('[role=\"alertdialog\"], [role=\"dialog\"]')", 5)
        except AssertionError as exc:
            toasts = cdp.evaluate("[...document.querySelectorAll('[data-sonner-toast]')]"
                                  ".map(t => t.innerText.trim()).join(' | ')")
            raise AssertionError(f"{section}: «{label}» en «{row[:40]}» no abrió diálogo de "
                                 f"confirmación en 5 s; avisos: {toasts or 'ninguno'}") from exc
        _mark(cdp, "[...document.querySelectorAll('[role=\"alertdialog\"] button, [role=\"dialog\"] button')]"
              ".find(b => /^\\s*(cancelar|no)\\b/i.test(b.innerText))", "cancel", timeout=3)
        cdp.click("[data-e2e=cancel]")
        cdp.wait_for("!document.querySelector('[role=\"alertdialog\"], [role=\"dialog\"]')", 5)
        assert row in _main_text(cdp), f"{section}: tras cancelar el dato desapareció: {row!r}"
        return f"{section}: diálogo de confirmación mostrado y cancelar conservó «{row[:40]}»"
    raise NotChecked("ninguna sección ofrece todavía una acción destructiva (eliminar/borrar): "
                     "no hay datos ni confirmaciones en el escritorio sin backend conectado")


# --- cierre: lo último, para cubrir todo el recorrido ------------------------------------


@check("desktop.errores", "Ni la consola ni la página registraron errores durante el recorrido",
       phase="desktop", needs=("desktop",))
def no_errors(ctx):
    cdp = _cdp(ctx)
    time.sleep(0.5)
    cdp.evaluate("1")  # vacía los eventos pendientes del socket hacia console_errors/exceptions
    errors = [e for e in cdp.console_errors if not any(n in e for n in IGNORED_NOISE)]
    ignored = len(cdp.console_errors) - len(errors)
    assert not errors and not cdp.exceptions, (
        f"consola: {errors[:5]}; excepciones: {[e[:200] for e in cdp.exceptions[:5]]}")
    return f"0 errores de consola y 0 excepciones en todo el recorrido ({ignored} ignorados por la lista de ruido)"
