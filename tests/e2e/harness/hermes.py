"""Preflight de Hermes: comprueba el commit instalado, no el texto de versión."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

MIN_PYTHON = (3, 14)


def installed_commit(venv: Path) -> str | None:
    """Commit según PEP 610 (`direct_url.json`) o, si es editable, el del clon local."""
    for record in venv.glob("lib/python*/site-packages/hermes*.dist-info/direct_url.json"):
        data = json.loads(record.read_text())
        if commit := data.get("vcs_info", {}).get("commit_id"):
            return commit
        url = data.get("url", "")
        if url.startswith("file://"):
            probe = subprocess.run(["git", "-C", url.removeprefix("file://"), "rev-parse", "HEAD"],
                                   capture_output=True, text=True, check=False)
            return probe.stdout.strip() or None
    return None


def problems(venv: Path, commit: str, env: dict[str, str]) -> list[str]:
    """Lista vacía si el venv cumple. Solo inspecciona: no arranca Hermes."""
    python, binary = venv / "bin" / "python", venv / "bin" / "hermes"
    if not python.is_file():
        return [f"el venv no tiene {python}"]
    found = []
    if not binary.is_file():
        found.append(f"falta {binary}")
    code = ("import sys, importlib.util as u;"
            "print(*sys.version_info[:2]); print(u.find_spec('aiohttp') is not None)")
    probe = subprocess.run([str(python), "-I", "-c", code], capture_output=True, text=True,
                           env=env, timeout=30, check=False)
    lines = probe.stdout.split("\n")
    if probe.returncode != 0 or len(lines) < 2:
        return [*found, f"{python} no se pudo ejecutar"]
    version = tuple(int(part) for part in lines[0].split())
    if version < MIN_PYTHON:
        found.append(f"Python {version[0]}.{version[1]}; se exige >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]}")
    if lines[1] != "True":
        found.append("aiohttp no está disponible")
    installed = installed_commit(venv)
    if installed is None:
        found.append("commit no verificable: sin direct_url.json con commit")
    elif installed != commit:
        found.append(f"commit {installed[:12]}; se exige {commit[:12]}")
    return found
