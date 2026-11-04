"""Single-instance lock: the backend is the only writer of its database."""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

try:
    import fcntl
except ImportError:  # Windows: there is no flock to rely on.
    fcntl = None  # type: ignore[assignment]

_PRIVATE_MODE: Final = 0o600


class DatabaseInUse(Exception):
    """Another instance holds the database, or holding it cannot be guaranteed."""


def _open_lock_file(lock_path: Path) -> int:
    flags = os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
    try:
        descriptor = os.open(lock_path, flags, _PRIVATE_MODE)
    except OSError as exc:
        raise DatabaseInUse(f"No se puede abrir el bloqueo de la base: {exc}") from exc
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
        os.close(descriptor)
        raise DatabaseInUse(f"El bloqueo de la base no es un archivo propio: {lock_path}")
    os.fchmod(descriptor, _PRIVATE_MODE)
    return descriptor


@contextmanager
def exclusive_instance(db_path: Path) -> Iterator[None]:
    """Hold `<db>.lock` with a non-blocking flock; the kernel frees it if the process dies.

    The lock file is never removed: unlinking it would let two holders coexist.
    """
    if fcntl is None:
        raise DatabaseInUse("Esta plataforma no tiene flock: no se puede garantizar exclusividad")
    descriptor = _open_lock_file(Path(f"{db_path}.lock"))
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise DatabaseInUse("La base está en uso por otra instancia de Drakter") from exc
        yield
    finally:
        os.close(descriptor)  # Closing the only descriptor releases the flock.
