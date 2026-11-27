"""Comprobación breve de la seguridad del modo flotante, sin escritorio (revisión del PR #76).

I1 (window_id obligatorio, el resumen nombra app y título), I2, I3 (ajuste de pantalla), I4, C1, M1, I6 y M7.
Las barreras con helper real (HANDS_OFF, RISKY, contraseñas, ventanas de Drakter) necesitan un gnome-shell
headless y no están aquí.

Uso, desde backend/: PYTHONPATH=. .venv/bin/python tests/check_floating_safety.py
"""
import asyncio
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from drakter_contracts.floating import LookScreenArgs, OpenTargetArgs, ReadWindowArgs

from app.floating import presence
from app.integrations.hands.safety import check_url_dns, step_risk
from app.services.settings_models import SETTING_CHOICES, SETTING_DEFAULTS, SETTING_KEYS
from app.tools import hands, screen
from app.tools.spec import ToolContext, ToolError

OK = []


def report(name, ok, info=""):
    OK.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  — {info}" if info else ""))


# I2
s = hands._summary_open(OpenTargetArgs(url="https://ejemplo.com/buscar?q=" + "x" * 300 + "#frag"))
report("I2 URL completa recortada a ~200 con aviso de query", "https://ejemplo.com/buscar?q=xxx" in s and "…" in s
       and "Atención" in s and len(s) < 400, s)
s = hands._summary_open(OpenTargetArgs(url="https://es.wikipedia.org/wiki/Gato"))
report("I2 URL limpia sin aviso", "«https://es.wikipedia.org/wiki/Gato»" in s and "Atención" not in s, s)
s = hands._summary_open(OpenTargetArgs(url="mailto:a@b.com?subject=hola&body=datos"))
report("I2 mailto con body/subject avisa", "mailto:a@b.com?subject=hola&body=datos" in s and "asunto" in s, s)
s = hands._summary_open(OpenTargetArgs(url="https://ejemplo.com/‮abc"))
report("I2 caracteres bidi fuera", "‮" not in s, repr(s))

# M1
report("M1 DNS que no resuelve bloquea", check_url_dns("https://no-existe-de-verdad.invalid/") is not None)

# settings
report("I3 floating_screen_enabled en SETTING_KEYS, false por defecto",
       "floating_screen_enabled" in SETTING_KEYS and SETTING_DEFAULTS["floating_screen_enabled"] == "false"
       and SETTING_CHOICES["floating_screen_enabled"] == {"true", "false"})

# I4 / I3 gating
db = Path(tempfile.mkdtemp()) / "d.db"
con = sqlite3.connect(db)
con.close()
state = SimpleNamespace(settings=SimpleNamespace(db_path=db))


def ctx(job=None):
    return ToolContext(turn_id=uuid4(), session_id=uuid4(), call_id="c", principal="agent", state=state, job_id=job)


async def code_of(coro):
    try:
        await coro
    except ToolError as e:
        return e.code
    return "ok"


async def main():
    report("I3 look_screen sin ajuste → screen_disabled",
           await code_of(screen.look_screen(ctx(), LookScreenArgs(target="screen"))) == "screen_disabled")
    report("I3 read_window sin ajuste → screen_disabled",
           await code_of(screen.read_window(ctx(), ReadWindowArgs())) == "screen_disabled")
    screen.setting_on = lambda _c, _k: True
    presence.current_presence = lambda: None
    report("I4 look_screen sin modo flotante → floating_inactive",
           await code_of(screen.look_screen(ctx(), LookScreenArgs(target="screen"))) == "floating_inactive")
    report("I4 read_window sin modo flotante → floating_inactive",
           await code_of(screen.read_window(ctx(), ReadWindowArgs())) == "floating_inactive")
    report("I4/C1 read_window en turno de tarea → job_lane_forbidden",
           await code_of(screen.read_window(ctx(uuid4()), ReadWindowArgs())) == "job_lane_forbidden")
    report("C1 open_target en turno de tarea → job_lane_forbidden",
           await code_of(hands.open_target(ctx(uuid4()), OpenTargetArgs(url="https://es.wikipedia.org"))) == "job_lane_forbidden")
    d = next(t for t in screen.TOOLS if t.name == "look_screen").description
    report("I4 descripción", "Úsala solo cuando el usuario te pida mirar o ayudar con algo en pantalla" in d)
    d = next(t for t in screen.TOOLS if t.name == "read_window").description
    report("I3 descripción de read_window menciona terminales", "terminales" in d)


asyncio.run(main())

# I6 / M7 classification
from drakter_contracts.floating import StepKey, StepType  # noqa: E402

report("I6 motivo «atajo del sistema»", step_risk(StepKey(do="key", combo="super+a")) == "atajo del sistema")
report("I6 alt+F4 sigue con su combo", step_risk(StepKey(do="key", combo="alt+F4")) == "alt+F4")
report("M7 Return en editor no es arriesgado", step_risk(StepKey(do="key", combo="Return"), None, ("org.gnome.TextEditor",)) is None)
report("M7 \\n en Telegram es arriesgado", step_risk(StepType(do="type", text="a\nb"), None, ("org.telegram.desktop",)) is not None)
report("segments", hands.segments(5, {1, 3}) == [(0, 1, False), (1, 2, True), (2, 3, False), (3, 4, True), (4, 5, False)])

# I1: window_id obligatorio y el resumen nombra la app y el título
from drakter_contracts.floating import ActInAppArgs  # noqa: E402
from drakter_contracts.hands_ipc import HelperWindow  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.integrations.hands import desktop  # noqa: E402

try:
    ActInAppArgs.model_validate({"steps": [{"do": "click_text", "text": "7"}]})
    report("I1 act_in_app sin window_id → validation_error", False)
except ValidationError:
    report("I1 act_in_app sin window_id → validation_error", True)
rect = {"x": 0, "y": 0, "w": 300, "h": 400}
desktop._known.clear()
desktop._known["42"] = HelperWindow(window_id="42", app_id="org.gnome.Calculator", title="Calculadora", pid=1,
                                    client="wayland", frame=rect, buffer=rect, monitor=0, stack=0, focused=True)
s = hands._summary(ActInAppArgs(window_id="42", steps=[{"do": "click_text", "text": "7"}]))
report("I1 el resumen nombra la app y el título", "Calculadora" in s and "ventana «Calculadora»" in s, s)
print(f"\n{sum(OK)}/{len(OK)} PASS")
raise SystemExit(0 if all(OK) else 1)
