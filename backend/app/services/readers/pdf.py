"""PDF con pypdf. La extraccion corre siempre en el proceso hijo (sandbox)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from . import Extracted, ReadFailed, ReadOptions

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

_SEL = re.compile(r"^(?:page:(\d+)|pages:(\d+)-(\d+))$")


def parse_selector(selector: str | None) -> tuple[int, int] | None:
    if not selector:
        return None
    m = _SEL.match(selector.strip())
    if not m:
        raise ReadFailed("selector invalido, se espera page:N o pages:A-B")
    if m.group(1):
        a = b = int(m.group(1))
    else:
        a, b = int(m.group(2)), int(m.group(3))
    if a < 1 or b < a:
        raise ReadFailed("rango de paginas invalido")
    return a, b


def read_pdf(fd: int, options: ReadOptions, limits: StorageLimits) -> Extracted:
    from .sandbox import run_in_sandbox

    pages = parse_selector(options.selector)
    out = run_in_sandbox(
        "pdf",
        fd,
        {
            "pages": list(pages) if pages else None,
            "offset": max(0, options.offset),
            "max_chars": max(1, min(options.max_chars, limits.max_read_chars)),
        },
        limits,
    )
    return Extracted(out["text"], out["truncated"], out["next_offset"], out["metadata"])


def extract_pdf_text(fd: int, max_chars: int, limits: StorageLimits) -> str:
    from .sandbox import run_in_sandbox

    out = run_in_sandbox("pdf", fd, {"pages": None, "offset": 0, "max_chars": max_chars}, limits)
    return str(out["text"])


def worker_extract(fd: int, params: dict[str, Any], limits: Any) -> dict[str, Any]:
    """Se ejecuta dentro del hijo."""
    import io

    from pypdf import PdfReader

    from .text import PreadFile

    try:
        reader = PdfReader(io.BufferedReader(PreadFile(fd)), strict=False)
        if reader.is_encrypted:
            raise ReadFailed("PDF protegido con contrasena")
        total = len(reader.pages)
    except ReadFailed:
        raise
    except Exception as exc:
        raise ReadFailed(f"PDF invalido: {type(exc).__name__}") from exc
    first, last = 1, min(total, limits.pdf_max_pages)
    sel = params.get("pages")
    if sel:
        first, last = sel[0], min(sel[1], total, limits.pdf_max_pages)
        if first > last:
            raise ReadFailed("paginas fuera de rango")
    offset, max_chars = params["offset"], params["max_chars"]
    need = offset + max_chars + 1
    parts: list[str] = []
    got = 0
    done = first - 1
    try:
        for n in range(first, last + 1):
            t = reader.pages[n - 1].extract_text() or ""
            parts.append(t)
            got += len(t) + 2
            done = n
            if got >= need:
                break
    except Exception as exc:
        raise ReadFailed(f"error extrayendo PDF: {type(exc).__name__}") from exc
    text = "\n\n".join(parts)
    chunk = text[offset : offset + max_chars]
    more = len(text) > offset + max_chars or done < last
    return {
        "text": chunk,
        "truncated": more,
        "next_offset": offset + max_chars if more else None,
        "metadata": {"pages": total, "pages_read_to": done, "pages_limit": limits.pdf_max_pages},
    }
