"""Proceso hijo de analisis. No importa Settings ni FastAPI.

Uso: python -m app.services.readers.worker <kind>; peticion JSON por stdin
({"fd", "params", "limits"}), respuesta JSON por stdout.
"""

from __future__ import annotations

import json
import os
import resource
import signal
import sys
import time
from types import SimpleNamespace
from typing import Any

from app.services.readers import (
    ArchiveLimit,
    ReadFailed,
    TooLarge,
    UnsupportedFormat,
)


def _apply_limits(limits: SimpleNamespace, fd: int) -> None:
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)  # escribir falla con EFBIG, no mata
    nofile = max(fd + 8, 32)
    for res, val in (
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_FSIZE, 0),
        (resource.RLIMIT_CPU, int(limits.worker_cpu_seconds)),
        (resource.RLIMIT_NOFILE, nofile),
        (resource.RLIMIT_AS, int(limits.worker_address_space_bytes)),
    ):
        try:
            _, hard = resource.getrlimit(res)
            if hard != resource.RLIM_INFINITY:
                val = min(val, hard)
            resource.setrlimit(res, (val, val))
        except (ValueError, OSError):
            pass


def _run(kind: str, fd: int, params: dict[str, Any], limits: SimpleNamespace) -> dict[str, Any]:
    if kind == "pdf":
        from app.services.readers.pdf import worker_extract

        return worker_extract(fd, params, limits)
    if kind == "archive":
        from app.services.storage_archives import list_archive

        return list_archive(fd, limits)
    if kind == "_selftest_sleep":
        time.sleep(float(params.get("seconds", 60)))
        return {}
    if kind == "_selftest_alloc":
        return {"n": len(bytearray(int(params["bytes"])))}
    raise UnsupportedFormat(f"tipo de analisis desconocido: {kind}")


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        req = json.loads(sys.stdin.buffer.read())
        fd = int(req["fd"])
        limits = SimpleNamespace(**req["limits"])
        _apply_limits(limits, fd)
    except Exception:
        return 2
    try:
        reply: dict[str, Any] = {"ok": True, "result": _run(kind, fd, req["params"], limits)}
    except (ReadFailed, ArchiveLimit, TooLarge, UnsupportedFormat) as exc:
        reply = {"ok": False, "error": type(exc).__name__, "message": str(exc)[:300]}
    except MemoryError:
        reply = {"ok": False, "error": "ReadFailed", "message": "limite de memoria superado"}
    except Exception as exc:
        reply = {"ok": False, "error": "ReadFailed", "message": f"fallo interno: {type(exc).__name__}"}
    out = json.dumps(reply, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
