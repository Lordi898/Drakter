"""Ejecuta un analisis en un proceso hijo con limites de recursos y salida acotada."""

from __future__ import annotations

import dataclasses
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import ArchiveLimit, ReadFailed, TooLarge, UnsupportedFormat

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

_BACKEND = Path(__file__).resolve().parents[3]
_ERRORS = {
    "ReadFailed": ReadFailed,
    "ArchiveLimit": ArchiveLimit,
    "TooLarge": TooLarge,
    "UnsupportedFormat": UnsupportedFormat,
}


def _kill(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def run_in_sandbox(kind: str, fd: int, params: dict[str, Any], limits: StorageLimits) -> dict[str, Any]:
    request = json.dumps(
        {"fd": fd, "params": params, "limits": dataclasses.asdict(limits)}, ensure_ascii=True
    ).encode()
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(_BACKEND),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    try:
        proc = subprocess.Popen(
            [sys.executable, "-B", "-m", "app.services.readers.worker", kind],
            cwd=_BACKEND,
            env=env,
            pass_fds=(fd,),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except OSError as exc:
        raise ReadFailed("no se pudo lanzar el proceso de analisis") from exc
    deadline = time.monotonic() + limits.worker_timeout_seconds
    cap = limits.worker_max_output_bytes
    chunks: list[bytes] = []
    total = 0
    try:
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write(request)
            proc.stdin.close()
        except OSError:
            pass
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                _kill(proc)
                raise ReadFailed("tiempo de analisis agotado")
            if not sel.select(left):
                continue
            data = os.read(proc.stdout.fileno(), 65536)
            if not data:
                break
            total += len(data)
            if total > cap:
                _kill(proc)
                raise ReadFailed("salida del analisis demasiado grande")
            chunks.append(data)
        try:
            code = proc.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            _kill(proc)
            raise ReadFailed("tiempo de analisis agotado") from None
    finally:
        if proc.poll() is None:
            _kill(proc)
        if proc.stdout:
            proc.stdout.close()
    if code != 0:
        why = f"senal {-code}" if code < 0 else f"codigo {code}"
        raise ReadFailed(f"el analisis termino anormalmente ({why}); posible limite de recursos")
    try:
        reply = json.loads(b"".join(chunks))
    except ValueError as exc:
        raise ReadFailed("respuesta del analisis ilegible") from exc
    if not isinstance(reply, dict):
        raise ReadFailed("respuesta del analisis ilegible")
    if reply.get("ok"):
        return reply["result"]
    raise _ERRORS.get(reply.get("error", ""), ReadFailed)(str(reply.get("message", "fallo")))
