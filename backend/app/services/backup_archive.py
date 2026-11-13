"""The bundle format: writing it, and reading it back as untrusted input.

Reading is one pass over the archive, so what is verified is exactly what gets
extracted. The manifest goes last because the writer learns sizes and hashes
while streaming, from a data directory other processes may be changing.
"""

from __future__ import annotations

import errno
import gzip
import hashlib
import io
import os
import re
import stat
import tarfile
import zlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Final

from pydantic import ValidationError

from app.core.errors import AppError
from app.services.backup_models import BundleManifest, ExcludedItem, ManifestFile, Role

FORMAT_VERSION: Final = 1
MANIFEST_NAME: Final = "manifest.json"
DATABASE_MEMBER: Final = "db/drakter.db"
CONFIG_ALLOWLIST: Final = frozenset({"settings.json", "preferences.json"})
ROLE_PREFIXES: Final[dict[Role, str]] = {
    "database": "db",
    "config": "config",
    "indexes": "indexes",
    "openviking": "openviking",
    "storage": "storage",
}

MAX_MEMBERS: Final = 200_000
MAX_DEPTH: Final = 24
MAX_DECOMPRESSED_BYTES: Final = 64 * 1024**3
MAX_MANIFEST_BYTES: Final = 16 * 1024**2

_CHUNK_BYTES: Final = 1024**2
# Tar metadata and file chunks stay below this. Without it, a forged pax or
# GNU long-name header makes `tarfile` load its claimed size in one read.
_MAX_SINGLE_READ: Final = 2 * 1024**2
# Headers and padding are real decompressed bytes on top of the file contents.
_MAX_STREAM_BYTES: Final = MAX_DECOMPRESSED_BYTES + 1024**3
_READ_ERRORS: Final = (
    tarfile.TarError,
    OSError,
    EOFError,
    zlib.error,
    RecursionError,  # A chain of pax headers recurses inside `tarfile`.
    ValueError,
    OverflowError,
)
_SECRET_NAME: Final = re.compile(
    r"\.env(?:\.|$)|\.key$|\.pem$|^auth\.json$|token|secret|credential", re.IGNORECASE
)


class ArchiveRejected(AppError):
    """The archive broke a rule. Messages are fixed: nothing from it reaches the client."""

    def __init__(self, message: str, code: str = "backup_invalid", status_code: int = 422) -> None:
        super().__init__(code, message, status_code)


class BundleLimitExceeded(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("backup_too_large", message, 409)


@dataclass(frozen=True)
class SourceFile:
    member: str
    role: Role
    path: Path


def is_secret_name(name: str) -> bool:
    return _SECRET_NAME.search(name) is not None


def member_problem(name: str) -> str | None:
    """Why this path cannot live in a bundle. Shared so the writer never emits what the reader rejects."""
    if not name or "\x00" in name or "\\" in name:
        return "ruta con caracteres no admitidos"
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return "ruta que no es UTF-8"
    if PurePosixPath(name).is_absolute() or PureWindowsPath(name).anchor:
        return "ruta absoluta"
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return "ruta no normalizada"
    if len(parts) > MAX_DEPTH:
        return "ruta demasiado profunda"
    if any(is_secret_name(part) for part in parts):
        return "posible secreto: no se abre ni se copia"
    return None


def role_of(path: str) -> Role | None:
    """The only role a file path may have; `None` when no role admits it."""
    parts = path.split("/")
    if len(parts) < 2:
        return None
    if parts[0] == ROLE_PREFIXES["database"]:
        return "database" if path == DATABASE_MEMBER else None
    if parts[0] == ROLE_PREFIXES["config"]:
        return "config" if len(parts) == 2 and parts[1] in CONFIG_ALLOWLIST else None
    for role in ("indexes", "openviking", "storage"):
        if parts[0] == ROLE_PREFIXES[role]:
            return role
    return None


def _tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.size = size
    info.mode = 0o600
    return info  # Owner and mtime stay at zero: a bundle does not describe this machine.


class _HashingReader:
    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        data = self._stream.read(size)
        self.digest.update(data)
        return data


def _add_file(
    tar: tarfile.TarFile, source: SourceFile, budget: int, skipped: list[ExcludedItem]
) -> ManifestFile | None:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    try:
        descriptor = os.open(source.path, flags)
    except FileNotFoundError:
        skipped.append(ExcludedItem(what=source.member, reason="desapareció durante la copia"))
        return None
    except OSError as exc:
        if exc.errno != errno.ELOOP:
            raise
        skipped.append(ExcludedItem(what=source.member, reason="enlace simbólico: no se sigue"))
        return None
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            skipped.append(ExcludedItem(what=source.member, reason="no es un archivo regular"))
            return None
        if info.st_size > budget:
            raise BundleLimitExceeded("La copia supera el tamaño máximo admitido")
        reader = _HashingReader(stream)
        # `size` bytes exactly: a file that shrank fails here, one that grew is cut.
        tar.addfile(_tar_info(source.member, info.st_size), reader)  # type: ignore[arg-type]
    return ManifestFile(
        path=source.member, role=source.role, size=info.st_size, sha256=reader.digest.hexdigest()
    )


def write_bundle(
    target: Path,
    sources: Iterable[SourceFile],
    skipped: list[ExcludedItem],
    make_manifest: Callable[[list[ManifestFile]], BundleManifest],
) -> BundleManifest:
    files: list[ManifestFile] = []
    total = 0
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    with os.fdopen(os.open(target, flags, 0o600), "wb") as raw:
        with tarfile.open(
            fileobj=raw, mode="w:gz", compresslevel=6, format=tarfile.PAX_FORMAT
        ) as tar:
            tar.copybufsize = _CHUNK_BYTES
            for source in sources:
                if len(files) + 1 >= MAX_MEMBERS:
                    raise BundleLimitExceeded("La copia supera el número máximo de archivos")
                entry = _add_file(tar, source, MAX_DECOMPRESSED_BYTES - total, skipped)
                if entry is not None:
                    files.append(entry)
                    total += entry.size
            manifest = make_manifest(files)
            payload = manifest.model_dump_json(indent=2).encode("utf-8")
            if len(payload) > MAX_MANIFEST_BYTES:
                raise BundleLimitExceeded("El manifiesto supera el tamaño máximo admitido")
            tar.addfile(_tar_info(MANIFEST_NAME, len(payload)), io.BytesIO(payload))
        raw.flush()
        os.fsync(raw.fileno())
    return manifest


class _BoundedStream:
    """Decompressed view of the archive that counts what really comes out."""

    def __init__(self, inner: gzip.GzipFile) -> None:
        self._inner = inner

    def _check_position(self) -> None:
        if self._inner.tell() > _MAX_STREAM_BYTES:
            raise ArchiveRejected("El archivo descomprimido supera el límite")

    def read(self, size: int = -1) -> bytes:
        if size < 0 or size > _MAX_SINGLE_READ:
            raise ArchiveRejected("El archivo declara una cabecera demasiado grande")
        data = self._inner.read(size)
        self._check_position()
        return data

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence != os.SEEK_SET or offset > _MAX_STREAM_BYTES:
            raise ArchiveRejected("El archivo descomprimido supera el límite")
        return self._inner.seek(offset)

    def tell(self) -> int:
        return self._inner.tell()


def _open_private(path: Path) -> BinaryIO:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    return os.fdopen(os.open(path, flags, 0o600), "wb")


def _extraction_target(root: Path, name: str) -> Path:
    """`name` has passed `member_problem`, and this tree only gets real directories."""
    directory = root
    parts = name.split("/")
    for part in parts[:-1]:
        directory = directory / part
        if not directory.is_dir():
            directory.mkdir(mode=0o700)
    return directory / parts[-1]


def _check_member_header(member: tarfile.TarInfo) -> None:
    problem = member_problem(member.name)
    if problem is not None:
        raise ArchiveRejected("El archivo contiene una ruta prohibida")
    if member.isdir():
        if member.name.split("/")[0] not in ROLE_PREFIXES.values():
            raise ArchiveRejected("El archivo contiene un directorio inesperado")
        return
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.issparse():
        raise ArchiveRejected("El archivo contiene un miembro que no es regular")
    if member.size < 0 or member.size > MAX_DECOMPRESSED_BYTES:
        raise ArchiveRejected("El archivo declara un tamaño no admitido")


def _read_member(
    tar: tarfile.TarFile, member: tarfile.TarInfo, sink: BinaryIO | None
) -> tuple[int, str]:
    stream = tar.extractfile(member)
    if stream is None:
        raise ArchiveRejected("El archivo contiene un miembro ilegible")
    digest = hashlib.sha256()
    size = 0
    with stream:
        while chunk := stream.read(_CHUNK_BYTES):
            size += len(chunk)
            digest.update(chunk)
            if sink is not None:
                sink.write(chunk)
    if size != member.size:
        raise ArchiveRejected("Un miembro del archivo está truncado")
    return size, digest.hexdigest()


def _read_manifest_member(tar: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    if member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE) or member.issparse():
        raise ArchiveRejected("El manifiesto no es un archivo regular")
    if member.size > MAX_MANIFEST_BYTES:
        raise ArchiveRejected("El manifiesto supera el tamaño máximo admitido")
    buffer = io.BytesIO()
    _read_member(tar, member, buffer)  # type: ignore[arg-type]
    return buffer.getvalue()


def _parse_manifest(raw: bytes | None) -> BundleManifest:
    if raw is None:
        raise ArchiveRejected("El archivo no contiene manifiesto")
    try:
        manifest = BundleManifest.model_validate_json(raw)
    except ValidationError as exc:
        raise ArchiveRejected("El manifiesto no es válido") from exc
    if manifest.format_version != FORMAT_VERSION:
        raise ArchiveRejected(
            "El formato de la copia no está soportado", "backup_format_unsupported", 409
        )
    return manifest


def _check_against_manifest(manifest: BundleManifest, seen: dict[str, tuple[int, str]]) -> None:
    listed = {entry.path: entry for entry in manifest.files}
    if len(listed) != len(manifest.files):
        raise ArchiveRejected("El manifiesto repite una ruta")
    if listed.keys() != seen.keys():
        raise ArchiveRejected("El contenido del archivo no coincide con el manifiesto")
    for path, entry in listed.items():
        if seen[path] != (entry.size, entry.sha256):
            raise ArchiveRejected("Un archivo no coincide con su tamaño o su hash")
        if role_of(path) != entry.role:
            raise ArchiveRejected("El rol de un archivo no coincide con su ruta")
    if DATABASE_MEMBER not in listed:
        raise ArchiveRejected("El archivo no contiene la base de datos")


def _scan(
    tar: tarfile.TarFile, extract_to: Path | None, select: Callable[[str], bool] | None
) -> BundleManifest:
    seen: dict[str, tuple[int, str]] = {}
    names: set[str] = set()
    manifest_raw: bytes | None = None
    total = 0
    for count, member in enumerate(tar, start=1):
        if count > MAX_MEMBERS:
            raise ArchiveRejected("El archivo supera el número máximo de miembros")
        if member.name in names:
            raise ArchiveRejected("El archivo repite un miembro")
        names.add(member.name)
        if member.name == MANIFEST_NAME:
            manifest_raw = _read_manifest_member(tar, member)
            continue
        _check_member_header(member)
        if member.isdir():
            continue
        # Checked before a single byte of the member reaches the disk.
        if role_of(member.name) is None:
            raise ArchiveRejected("El archivo contiene una ruta no admitida para su rol")
        total += member.size
        if total > MAX_DECOMPRESSED_BYTES:
            raise ArchiveRejected("El archivo descomprimido supera el límite")
        if extract_to is not None and (select is None or select(member.name)):
            with _open_private(_extraction_target(extract_to, member.name)) as sink:
                seen[member.name] = _read_member(tar, member, sink)
        else:
            seen[member.name] = _read_member(tar, member, None)
    manifest = _parse_manifest(manifest_raw)
    _check_against_manifest(manifest, seen)
    return manifest


def read_bundle(
    path: Path,
    *,
    extract_to: Path | None = None,
    select: Callable[[str], bool] | None = None,
) -> BundleManifest:
    """Validate a whole bundle, optionally extracting into a private directory.

    Whatever lands in `extract_to` is only trustworthy once this returns: on
    failure the caller discards the directory.
    """
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(descriptor, "rb") as raw:
            if not stat.S_ISREG(os.fstat(raw.fileno()).st_mode):
                raise ArchiveRejected("La copia no es un archivo regular")
            with gzip.GzipFile(fileobj=raw, mode="rb") as decompressed:
                bounded = _BoundedStream(decompressed)
                with tarfile.open(fileobj=bounded, mode="r:") as tar:  # type: ignore[call-overload]
                    return _scan(tar, extract_to, select)
    except AppError:
        raise
    except _READ_ERRORS as exc:
        raise ArchiveRejected("El archivo está dañado o no es una copia válida") from exc
