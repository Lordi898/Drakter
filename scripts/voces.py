#!/usr/bin/env python3
"""Perfiles de voz de Drakter: listar, comprobar contra Fish y probar. Se lanza con voces.sh.

La clave FISH_API_KEY se lee de ~/.config/drakter/.env y nunca se imprime ni se registra.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from drakter_contracts.voice_profiles import (
    ALLOWED_MODELS,
    VoiceConfig,
    VoiceConfigError,
    ensure_voices_file,
    load_voice_config,
    mask_id,
    voices_path,
)

API = "https://api.fish.audio"
TIMEOUT_S = 30.0
MAX_TEXT = 300
DEFAULT_TEXT = "Hola, esta es mi voz."


def env_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    return root / "drakter" / ".env"


def read_api_key() -> str | None:
    """Solo busca FISH_API_KEY; el resto del .env no se interpreta."""
    try:
        for line in env_path().read_text(encoding="utf-8").splitlines():
            name, sep, value = line.partition("=")
            if sep and name.strip() == "FISH_API_KEY":
                value = value.strip().strip("'\"")
                return value or None
    except OSError:
        return None
    return None


def load() -> tuple[Path, VoiceConfig]:
    path, created = ensure_voices_file()
    if created:
        print(f"Creado {path} desde la plantilla (con los IDs vacíos).")
    return path, load_voice_config(path)


def need_ids_message(path: Path) -> str:
    return f"Ningún perfil tiene ID de voz. Pon los IDs en {path}"


def cmd_listar(_: argparse.Namespace) -> int:
    path, cfg = load()
    print(f"Archivo: {path}")
    print(f"Modelo:  {cfg.tts.modelo}   Por defecto: {cfg.default}\n")
    for name, p in cfg.perfiles.items():
        state = "configurado" if p.configured else "sin configurar"
        print(f"{name}{' (por defecto)' if name == cfg.default else ''}")
        print(f"  {p.descripcion}")
        print(f"  alias:  {', '.join(p.alias) or '-'}")
        print(f"  ID:     {mask_id(p.reference_id) or '-'}")
        print(f"  estado: {state}")
    if not any(p.configured for p in cfg.perfiles.values()):
        print(f"\n{need_ids_message(path)}")
    return 0


def client(key: str) -> httpx.Client:
    return httpx.Client(
        base_url=API, headers={"Authorization": f"Bearer {key}"}, timeout=TIMEOUT_S
    )


def fail_http(exc: Exception) -> str:
    # Nunca el texto de la excepción: puede incluir cabeceras o la URL.
    return f"error de red ({type(exc).__name__})"


def cmd_comprobar(_: argparse.Namespace) -> int:
    path, cfg = load()
    configured = {n: p for n, p in cfg.perfiles.items() if p.configured}
    if not configured:
        print(need_ids_message(path))
        return 1
    key = read_api_key()
    if key is None:
        print(f"Falta FISH_API_KEY en {env_path()} (clave: https://fish.audio/app/api-keys/).")
        return 1
    bad = 0
    with client(key) as http:
        for name, p in cfg.perfiles.items():
            if not p.configured:
                print(f"{name}: sin configurar (pon su ID en {path})")
                continue
            try:
                res = http.get(f"/model/{p.reference_id}")
            except httpx.HTTPError as exc:
                print(f"{name}: {fail_http(exc)}")
                bad += 1
                continue
            if res.status_code == 404:
                print(f"{name}: NO EXISTE en Fish ({mask_id(p.reference_id)}). Revisa el ID.")
                bad += 1
            elif res.status_code in (401, 403):
                print(f"{name}: Fish rechaza la clave (HTTP {res.status_code}). Revisa FISH_API_KEY.")
                return 1
            elif res.status_code != 200:
                print(f"{name}: Fish respondió HTTP {res.status_code}")
                bad += 1
            else:
                data = res.json()
                state = data.get("state", "?")
                langs = ", ".join(data.get("languages") or []) or "?"
                ok = state == "trained"
                bad += 0 if ok else 1
                print(f"{name}: existe, estado {state}{'' if ok else ' (NO está trained)'}, idioma {langs}")
    return 1 if bad else 0


def play(path: Path) -> bool:
    for player in (["pw-play"], ["aplay", "-q"]):
        if shutil.which(player[0]):
            return subprocess.run([*player, str(path)], check=False).returncode == 0
    print("No hay reproductor (pw-play ni aplay).")
    return False


def cmd_probar(args: argparse.Namespace) -> int:
    path, cfg = load()
    model = cfg.tts.modelo
    if model not in ALLOWED_MODELS and not cfg.tts.allow_paid:
        print(f"Me niego: el modelo {model!r} no está en la lista blanca ({', '.join(ALLOWED_MODELS)}).")
        return 1
    name = cfg.resolve(args.perfil)
    if name is None:
        print(f"No existe el perfil {args.perfil!r}. Hay: {', '.join(cfg.perfiles)}.")
        return 1
    profile = cfg.perfiles[name]
    if not profile.configured:
        print(f"El perfil {name!r} está sin configurar. Pon su ID en {path}")
        return 1
    text = (args.texto or DEFAULT_TEXT).strip()
    if not text or len(text) > MAX_TEXT:
        print(f"El texto debe tener entre 1 y {MAX_TEXT} caracteres.")
        return 1
    key = read_api_key()
    if key is None:
        print(f"Falta FISH_API_KEY en {env_path()}.")
        return 1
    body = {"text": text, "reference_id": profile.reference_id, "format": "wav", "latency": "normal"}
    try:
        with client(key) as http:
            # La cabecera `model` es obligatoria: sin ella Fish cobra con s2.1-pro.
            res = http.post("/v1/tts", json=body, headers={"model": model})
    except httpx.HTTPError as exc:
        print(f"No se pudo generar: {fail_http(exc)}")
        return 1
    if res.status_code != 200:
        print(f"Fish respondió HTTP {res.status_code}; no se ha generado audio.")
        return 1
    with tempfile.TemporaryDirectory(prefix="drakter-voz-") as tmp:
        wav = Path(tmp) / "prueba.wav"
        wav.write_bytes(res.content)
        print(f"Reproduciendo con {name} ({model})…")
        return 0 if play(wav) else 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="voces.sh", description="Perfiles de voz de Drakter.")
    sub = parser.add_subparsers(dest="orden", required=True)
    sub.add_parser("listar", help="perfiles, alias, ID enmascarado y estado").set_defaults(run=cmd_listar)
    sub.add_parser("comprobar", help="comprueba cada voz contra Fish").set_defaults(run=cmd_comprobar)
    probar = sub.add_parser("probar", help="genera y reproduce una frase corta")
    probar.add_argument("perfil")
    probar.add_argument("texto", nargs="?")
    probar.set_defaults(run=cmd_probar)
    args = parser.parse_args()
    try:
        return int(args.run(args))
    except VoiceConfigError as exc:
        print(f"{exc}\nArchivo: {voices_path()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
