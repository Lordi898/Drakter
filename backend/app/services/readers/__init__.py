"""Lectores de archivos bajo demanda del almacen (contrato: storage_relations_contract.md).

Este paquete se importa tambien dentro del proceso hijo (`readers.worker`), asi que no
importa `Settings`, FastAPI ni nada pesado a nivel de modulo.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from app.services.storage_ports import StorageLimits

ResourceTypeLiteral = Literal["image", "document", "pdf", "text", "code", "archive", "other"]
MetaValue = str | int | float | bool | None


@dataclass(frozen=True)
class ReadOptions:
    selector: str | None = None
    offset: int = 0
    max_chars: int = 8000


@dataclass(frozen=True)
class Extracted:
    text: str
    truncated: bool
    next_offset: int | None
    metadata: dict[str, MetaValue]


class UnsupportedFormat(Exception):
    """Formato sin lector en v1."""


class ReadFailed(Exception):
    """Archivo invalido, protegido o lector fallido."""


class TooLarge(Exception):
    """Archivo por encima del limite de lectura."""


class ArchiveLimit(Exception):
    """Un comprimido supera un limite (entradas, bytes, proporcion, profundidad)."""


_LAZY_LINK = {"read_link", "UrlNotAllowed", "LinkFetchFailed"}


def __getattr__(name: str) -> Any:
    if name in _LAZY_LINK:
        import importlib

        return getattr(importlib.import_module(".link", __name__), name)
    raise AttributeError(name)


# --- deteccion de tipo ------------------------------------------------------

_DOCUMENT_EXT = {".doc", ".docx", ".odt", ".rtf"}
_OTHER_EXT = {
    ".exe", ".dll", ".so", ".appimage", ".bin", ".dmg", ".msi", ".deb", ".rpm", ".o", ".a",
    ".dylib", ".class", ".pyc", ".iso", ".img", ".sys", ".com", ".bat_exe",
}  # fmt: skip
_ARCHIVE_EXT = {".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".tbz2", ".txz", ".jar", ".apk"}
_CODE_EXT = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".rs", ".go", ".java", ".kt", ".cs", ".rb", ".php", ".sh", ".bash", ".zsh", ".ps1", ".bat",
    ".sql", ".css", ".scss", ".html", ".htm", ".vue", ".svelte", ".lua", ".swift", ".r", ".pl",
}  # fmt: skip
_TEXT_EXT = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".xml", ".env", ".tex", ".org", ".srt", ".gitignore",
}  # fmt: skip
_IMAGE_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".gif": "image/gif", ".webp": "image/webp", ".bmp": "image/bmp"}  # fmt: skip
_MIME_BY_EXT = {
    ".md": "text/markdown", ".csv": "text/csv", ".json": "application/json",
    ".yaml": "application/yaml", ".yml": "application/yaml", ".xml": "application/xml",
    ".zip": "application/zip", ".gz": "application/gzip", ".tgz": "application/gzip",
    ".bz2": "application/x-bzip2", ".xz": "application/x-xz", ".tar": "application/x-tar",
    ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text", ".doc": "application/msword",
    ".rtf": "application/rtf",
}  # fmt: skip


def _ext(name: str) -> str:
    base = os.path.basename(name).lower()
    if base.startswith(".") and base.count(".") == 1:
        return base  # ".gitignore"
    return os.path.splitext(base)[1]


def _looks_text(head: bytes) -> bool:
    if not head or b"\x00" in head[:8192]:
        return False
    try:
        head[:8192].decode("utf-8")
    except UnicodeDecodeError as exc:
        if exc.start < len(head[:8192]) - 4:
            return False
    return True


def detect_type(name: str, head: bytes) -> tuple[ResourceTypeLiteral, str | None]:
    """Magic bytes primero, extension despues. Nunca ejecuta ni abre nada."""
    ext = _ext(name)
    if head.startswith(b"%PDF-"):
        return "pdf", "application/pdf"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image", "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "image", "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image", "image/webp"
    if head[:2] == b"BM" and ext == ".bmp":
        return "image", "image/bmp"
    if head.startswith(b"\x7fELF") or head[:2] == b"MZ" or head[:4] in (
        b"\xca\xfe\xba\xbe", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"
    ):  # fmt: skip
        return "other", "application/octet-stream"
    if ext in _OTHER_EXT:
        return "other", "application/octet-stream"
    if head.startswith(b"{\\rtf") or ext in _DOCUMENT_EXT:
        return "document", _MIME_BY_EXT.get(ext, "application/rtf")
    if head[:4] in (b"PK\x03\x04", b"PK\x05\x06") or head[:3] == b"BZh" \
            or head[:2] == b"\x1f\x8b" or head[:6] == b"\xfd7zXZ\x00" or head[257:262] == b"ustar":  # fmt: skip
        return "archive", _MIME_BY_EXT.get(ext) if ext in _ARCHIVE_EXT else _magic_archive_mime(head)
    if ext in _IMAGE_EXT:
        return "image", _IMAGE_EXT[ext]
    if ext == ".pdf":
        return "pdf", "application/pdf"
    if ext in _ARCHIVE_EXT:
        return "archive", _MIME_BY_EXT.get(ext)
    if ext in _CODE_EXT:
        return "code", "text/x-" + ext[1:]
    if ext in _TEXT_EXT:
        return "text", _MIME_BY_EXT.get(ext, "text/plain")
    if _looks_text(head):
        return "text", "text/plain"
    return "other", None


def _magic_archive_mime(head: bytes) -> str:
    if head[:2] == b"PK":
        return "application/zip"
    if head[:2] == b"\x1f\x8b":
        return "application/gzip"
    if head[:3] == b"BZh":
        return "application/x-bzip2"
    if head[:2] == b"\xfd7":
        return "application/x-xz"
    return "application/x-tar"


# --- lectura -----------------------------------------------------------------


def _check_regular(fd: int) -> int:
    try:
        st = os.fstat(fd)
    except OSError as exc:
        raise ReadFailed("no se puede consultar el archivo") from exc
    if not stat.S_ISREG(st.st_mode):
        raise ReadFailed("no es un archivo regular")
    return st.st_size


def read_file(
    fd: int, resource_type: str, mime: str | None, options: ReadOptions, limits: StorageLimits
) -> Extracted:
    size = _check_regular(fd)
    if resource_type in ("text", "code"):
        from . import text

        return text.read_text(fd, options, limits)
    if resource_type == "image":
        from . import image

        return image.read_image(fd, limits)
    if resource_type == "pdf":
        if size > limits.max_read_file_bytes:
            raise TooLarge("PDF demasiado grande")
        from . import pdf

        return pdf.read_pdf(fd, options, limits)
    if resource_type == "archive":
        if size > limits.archive_max_bytes:
            raise ArchiveLimit("comprimido demasiado grande")
        from app.services import storage_archives

        return storage_archives.read_archive(fd, options, limits)
    if resource_type == "document":
        raise UnsupportedFormat("los documentos Office/ODT no se leen en v1")
    raise UnsupportedFormat("tipo sin lector")


def extract_for_index(fd: int, resource_type: str, mime: str | None, limits: StorageLimits) -> str:
    """Solo texto, codigo y PDF. Comprimidos, imagenes y el resto: cadena vacia."""
    if resource_type not in ("text", "code", "pdf"):
        return ""
    size = _check_regular(fd)
    if resource_type == "pdf":
        if size > limits.max_read_file_bytes:
            raise TooLarge("PDF demasiado grande")
        from . import pdf

        return pdf.extract_pdf_text(fd, limits.max_index_chars, limits)
    from . import text

    return text.read_text_raw(fd, limits)[: limits.max_index_chars]
