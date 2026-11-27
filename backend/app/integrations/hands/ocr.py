"""OCR of a window crop: `hands/ocr` in its own venv, one process per request (CONTRACT §5)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Final

from drakter_contracts.hands_ipc import OcrRequest, OcrResult
from pydantic import ValidationError

logger = logging.getLogger("drakter.hands.ocr")

_DATA: Final = Path.home() / ".local" / "share" / "drakter"  # fixed (CONTRACT §2), not XDG_DATA_HOME
OCR_PYTHON: Final = _DATA / "venvs" / "ocr" / "bin" / "python"
TIMEOUT_S: Final = 10.0
_ENV_KEYS: Final = ("HOME", "LANG")


def available() -> bool:
    return OCR_PYTHON.is_file()


async def run_ocr(image: Path, region: list[int] | None = None, threads: int = 4) -> OcrResult | None:
    """None when the OCR is not installed, fails or takes over 10 s. Never logs the text."""
    if not available():
        return None
    req = OcrRequest(image=str(image), region=region, threads=threads)
    env = {k: os.environ[k] for k in _ENV_KEYS if k in os.environ}
    env["PATH"] = "/usr/bin:/bin"
    env["OMP_NUM_THREADS"] = str(threads)
    try:
        proc = await asyncio.create_subprocess_exec(
            str(OCR_PYTHON), "-I", "-m", "drakter_ocr",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            env=env, start_new_session=True,
        )
    except OSError:
        return None
    try:
        out, _ = await asyncio.wait_for(proc.communicate(req.model_dump_json().encode()), TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("OCR timed out", extra={"event": "ocr_timeout"})
        return None
    try:
        result = OcrResult.model_validate(json.loads(out or b"{}"))
    except (ValueError, ValidationError):
        return None
    if result.error:
        logger.warning("OCR failed", extra={"event": "ocr_failed", "error": result.error[:40]})
        return None
    return result
