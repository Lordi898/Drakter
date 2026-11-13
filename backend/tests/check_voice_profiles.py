#!/usr/bin/env python3
"""Comprobación breve de los perfiles de voz (CLAUDE.md §4: un fallo silencioso saldría caro).

    PYTHONPATH=.:../contracts/python .venv/bin/python tests/check_voice_profiles.py

Cubre: plantilla sin IDs, alias duplicados (sin mayúsculas ni tildes), modelo de pago bloqueado,
formato del ID, recarga, y las dos herramientas por el registro real con una BD temporal.
Los IDs de estos casos son inventados (todo `a`); no hay ningún ID real en el repositorio.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import stat
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from drakter_contracts.voice_profiles import (
    VoiceConfigError,
    VoiceProfileStore,
    ensure_voices_file,
    mask_id,
    parse_voice_config,
)

from app.core.config import Settings
from app.database.migrator import migrate
from app.events.hub import EventHub
from app.services import voice_profile
from app.tools import PermissionPolicy, ToolContext, ToolRegistry, TurnTracker, load_builtin_tools

FAKE_ID = "a" * 32
failures = 0


def check(ok: bool, label: str) -> None:
    global failures
    failures += 0 if ok else 1
    print(f"{'OK  ' if ok else 'FAIL'} {label}")


def rejects(text: str, fragment: str) -> bool:
    try:
        parse_voice_config(text)
    except VoiceConfigError as exc:
        return fragment in str(exc)
    return False


BASE = '[tts]\nmodelo = "s2.1-pro-free"\nperfil_por_defecto = "a"\n'


def loader(tmp: Path) -> None:
    path, created = ensure_voices_file(tmp / "drakter" / "voces.toml")
    text = path.read_text(encoding="utf-8")
    check(created and stat.S_IMODE(path.stat().st_mode) == 0o600, "plantilla creada con permisos 600")
    import re

    check(re.search(r"[0-9a-f]{32}", text) is None, "la plantilla no lleva ningún ID")
    store = VoiceProfileStore(path)
    cfg = store.get()
    check(all(not p.configured for p in cfg.perfiles.values()), "plantilla: todo 'sin configurar'")
    check(cfg.resolve("LA OTRA") == "neutral" and cfg.resolve("Cálida") == "natural", "alias sin mayúsculas ni tildes")
    check(ensure_voices_file(path) == (path, False), "no sobrescribe si ya existe")

    check(
        rejects(BASE + '[perfiles.a]\nalias=["Cálida"]\n[perfiles.b]\nalias=["calida"]\n', "no puede repetirse"),
        "alias duplicado (tildes/mayúsculas) rechazado",
    )
    paid = BASE.replace("s2.1-pro-free", "s2.1-pro") + "[perfiles.a]\n"
    check(rejects(paid, "lista blanca"), "modelo de pago bloqueado")
    check(parse_voice_config(paid.replace("[tts]\n", "[tts]\nallow_paid = true\n")).tts.modelo == "s2.1-pro", "allow_paid a mano lo permite")
    check(rejects(BASE + '[perfiles.a]\nreference_id = "xyz"\n', "32 caracteres"), "formato de ID rechazado")
    check(rejects(BASE.replace('"a"', '"zz"') + "[perfiles.a]\n", "perfil_por_defecto"), "perfil por defecto inexistente")
    check(mask_id(FAKE_ID) == "aaaa…aaaa", "ID enmascarado")

    time.sleep(0.01)
    path.write_text(text.replace('reference_id = ""   # <- pega aquí el ID (la parte', f'reference_id = "{FAKE_ID}"   # (la parte', 1), encoding="utf-8")
    check(store.get().perfiles["natural"].configured, "recarga al cambiar el archivo")
    path.write_text("[tts\n", encoding="utf-8")
    try:
        store.get()
        check(False, "archivo roto lanza error")
    except VoiceConfigError:
        check(True, "archivo roto lanza error (no sirve copia vieja)")


async def tools(tmp: Path) -> None:
    os.environ["XDG_CONFIG_HOME"] = str(tmp / "xdg")
    voice_profile._STORE._path = None  # noqa: SLF001 - reapunta al XDG temporal
    settings = Settings(data_dir=tmp / "data")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    migrate(settings.db_path, settings.backups_dir)
    hub = EventHub()
    state = SimpleNamespace(settings=settings, agent_runtime=SimpleNamespace(hub=hub))
    turns = TurnTracker()
    registry = ToolRegistry(turns, permissions=PermissionPolicy(["voice.*"]))
    load_builtin_tools(registry)
    session, turn = uuid4(), uuid4()
    turns.begin(session, turn)

    async def call(name: str, args: dict[str, object]):  # noqa: ANN202
        return await registry.dispatch(
            name, args, ToolContext(turn, session, uuid4().hex, "agent", state)
        )

    out = await call("voice_list_profiles", {})
    check(out.status == "ok" and out.data["active"] == "natural" and out.data["hint"], "voice_list_profiles con plantilla vacía")
    out = await call("voice_set_profile", {"profile": "la otra"})
    check(
        out.status == "error" and out.error.code == "profile_unconfigured" and "sin configurar" in out.error.message.lower(),
        "voice_set_profile sin ID: 'perfil sin configurar'",
    )
    out = await call("voice_set_profile", {"profile": "no existe"})
    check(out.status == "error" and out.error.code == "profile_not_found", "perfil inexistente")

    cfg_path = voice_profile.get_store().path
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8").replace('reference_id = ""', f'reference_id = "{FAKE_ID}"', 2),
        encoding="utf-8",
    )
    out = await call("voice_set_profile", {"profile": "La Otra"})
    check(out.status == "ok" and out.data["active"] == "neutral" and out.data["changed"], "voice_set_profile resuelve el alias")
    check(voice_profile.stored_profile(settings.db_path) == "neutral", "perfil activo persistido")
    check(FAKE_ID not in str(out.data), "el resultado no lleva el ID entero")
    events = [e for e in hub._buffer if e.type == "voice.profile_changed"]  # noqa: SLF001
    check(len(events) == 1 and events[0].payload["profile"] == "neutral", "evento voice.profile_changed")
    out = await call("voice_list_profiles", {})
    check(out.status == "ok" and [p["name"] for p in out.data["profiles"] if p["active"]] == ["neutral"], "lista marca el activo")
    out = await call("voice_set_profile", {"profile": "neutral", "extra": 1})
    check(out.status == "error", "argumentos extra rechazados")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="drakter-voces-"))
    try:
        loader(tmp)
        asyncio.run(tools(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("FALLOS" if failures else "TODO OK", failures or "")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
