"""Full backups: create, verify, restore, prune and schedule bundles.

The manifest and the file system are the truth; there is no backup table, which
would itself be rolled back by a restore. One lock serialises every operation:
the scheduler and the API must never interleave on the same directories.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import shutil
import sqlite3
import stat
import tarfile
import tempfile
import threading
import tomllib
from collections.abc import Callable, Iterator, Sequence
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Final

from fastapi import FastAPI
from platformdirs import user_config_dir

from app.core.config import Settings, ensure_private_dir
from app.core.errors import AppError
from app.database.backup import BackupError, create_backup, restore_backup, verify_backup
from app.database.connection import connect, sqlite_uri
from app.database.migrator import (
    MIGRATIONS_DIR,
    MigrationError,
    current_version,
    load_migrations,
    migrate,
)
from app.services.backup_archive import (
    CONFIG_ALLOWLIST,
    DATABASE_MEMBER,
    FORMAT_VERSION,
    ArchiveRejected,
    SourceFile,
    member_problem,
    read_bundle,
    write_bundle,
)
from app.services.backup_models import (
    BundleInfo,
    BundleManifest,
    ExcludedItem,
    ManifestFile,
    RestoreReport,
    Role,
)

logger = logging.getLogger("drakter.backup")

RestoreHook = Callable[[sqlite3.Connection], None]
Quiesce = Callable[[], None]

AUTO_LABEL: Final = "auto"
INITIAL_LABEL: Final = "initial"
PRE_RESTORE_LABEL: Final = "pre-restore"

_APP_NAME: Final = "drakter"
_BUNDLES_SUBDIR: Final = "bundles"
_WORK_PREFIX: Final = ".bundle-work-"
_STAMP_FORMAT: Final = "%Y%m%dT%H%M%S%fZ"
_LABEL_PATTERN: Final = re.compile(r"[a-z0-9-]{1,32}")
_BUNDLE_NAME: Final = re.compile(r"drakter-bundle-([0-9]{8}T[0-9]{12}Z)-([a-z0-9-]{1,32})\.tar\.gz")
_MODEL_SUFFIXES: Final = (".gguf", ".safetensors", ".onnx")
_MAX_EXCLUDED_ROWS: Final = 1000
_AUTO_KEEP: Final = 7
_INTERVAL_SECONDS: Final = 24 * 3600
_RETRY_SECONDS: Final = 3600
_HASH_CHUNK_BYTES: Final = 1024**2
_FAILURES: Final = (
    BackupError,
    MigrationError,
    OSError,
    ValueError,
    sqlite3.Error,
    tarfile.TarError,
)
_ALWAYS_EXCLUDED: Final = (
    ("documentos originales externos", "permanecen en su ubicación; solo se copian sus metadatos"),
    ("secretos", "claves y credenciales nunca entran en una copia"),
    ("modelos locales", "se pueden volver a descargar"),
    ("datos de Hermes", "viven en ~/.hermes, fuera de Drakter"),
)

_operations = threading.RLock()


@contextmanager
def _exclusive() -> Iterator[None]:
    if not _operations.acquire(blocking=False):
        raise AppError("backup_busy", "Ya hay una operación de copias en curso", 409)
    try:
        yield
    finally:
        _operations.release()


class _Exclusions:
    """Rows for the manifest. Capped: a huge skipped tree must not outgrow the manifest."""

    def __init__(self) -> None:
        self.items = [ExcludedItem(what=what, reason=why) for what, why in _ALWAYS_EXCLUDED]
        self._dropped = 0

    def add(self, what: str, reason: str) -> None:
        if len(self.items) >= _MAX_EXCLUDED_ROWS:
            self._dropped += 1
            return
        printable = what.encode("utf-8", "backslashreplace").decode("utf-8")
        self.items.append(ExcludedItem(what=printable, reason=reason))

    def finish(self) -> None:
        if self._dropped:
            what = f"{self._dropped} elementos más"
            self.items.append(ExcludedItem(what=what, reason="lista de exclusiones truncada"))
            self._dropped = 0


def _config_dir() -> Path:
    return Path(user_config_dir(_APP_NAME))


def _bundles_dir(settings: Settings) -> Path:
    directory = settings.backups_dir / _BUNDLES_SUBDIR
    try:
        ensure_private_dir(directory)
    except (OSError, ValueError) as exc:
        logger.error("unsafe bundles directory", exc_info=exc)
        raise AppError("backup_failed", "El directorio de copias no es seguro", 500) from exc
    return directory


def _stamp() -> str:
    return datetime.now(UTC).strftime(_STAMP_FORMAT)


def _app_version() -> str:
    try:
        return metadata.version("drakter-backend")
    except metadata.PackageNotFoundError:
        pass
    try:
        project = Path(__file__).resolve().parents[2] / "pyproject.toml"
        with open(project, "rb") as stream:
            return str(tomllib.load(stream)["project"]["version"])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "unknown"


def _schema_version_of(database: Path) -> int:
    uri = sqlite_uri(database, read_only=True)
    with closing(sqlite3.connect(uri, uri=True, isolation_level=None)) as conn:
        return current_version(conn)


def _code_schema_version() -> int:
    return len(load_migrations(MIGRATIONS_DIR))


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _new_work_dir(parent: Path) -> Path:
    return Path(tempfile.mkdtemp(dir=parent, prefix=_WORK_PREFIX))


def _sweep_stale_work(settings: Settings) -> None:
    """Remove what a crash left behind. Only call while holding the lock, outermost."""
    for parent in (settings.backups_dir, settings.backups_dir / _BUNDLES_SUBDIR):
        try:
            leftovers = [path for path in parent.iterdir() if path.name.startswith(_WORK_PREFIX)]
        except FileNotFoundError:
            continue
        for path in leftovers:
            shutil.rmtree(path, ignore_errors=True)


def _collect_config(exclusions: _Exclusions) -> Iterator[SourceFile]:
    """Look up exact names only: the directory is never listed, so nothing else is touched."""
    directory = _config_dir()
    for name in sorted(CONFIG_ALLOWLIST):
        path = directory / name
        member = f"config/{name}"
        try:
            info = os.lstat(path)
        except (FileNotFoundError, NotADirectoryError):
            continue
        if stat.S_ISLNK(info.st_mode):
            exclusions.add(member, "enlace simbólico: no se sigue")
        elif not stat.S_ISREG(info.st_mode):
            exclusions.add(member, "no es un archivo regular")
        else:
            yield SourceFile(member, "config", path)


def _collect_tree(
    root: Path, prefix: str, role: Role, exclusions: _Exclusions
) -> Iterator[SourceFile]:
    try:
        info = os.lstat(root)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(info.st_mode):
        exclusions.add(prefix, "enlace simbólico: no se sigue")
        return
    if not stat.S_ISDIR(info.st_mode):
        exclusions.add(prefix, "no es un directorio")
        return
    pending = [(root, prefix)]
    while pending:
        directory, relative = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except FileNotFoundError:
            continue
        for entry in entries:
            member = f"{relative}/{entry.name}"
            problem = member_problem(member)
            if problem is not None:
                exclusions.add(member, problem)
            elif entry.is_symlink():
                exclusions.add(member, "enlace simbólico: no se sigue")
            elif entry.is_dir(follow_symlinks=False):
                pending.append((Path(entry.path), member))
            elif not entry.is_file(follow_symlinks=False):
                exclusions.add(member, "no es un archivo regular")
            elif entry.name.lower().endswith(_MODEL_SUFFIXES):
                exclusions.add(member, "modelo local")
            else:
                yield SourceFile(member, role, Path(entry.path))


def _sources(
    settings: Settings, database: Path, include_storage: bool, exclusions: _Exclusions
) -> Iterator[SourceFile]:
    yield SourceFile(DATABASE_MEMBER, "database", database)
    yield from _collect_config(exclusions)
    yield from _collect_tree(settings.data_dir / "indexes", "indexes", "indexes", exclusions)
    yield from _collect_tree(
        settings.data_dir / "openviking", "openviking", "openviking", exclusions
    )
    if include_storage:
        yield from _collect_tree(settings.data_dir / "storage", "storage", "storage", exclusions)
    else:
        exclusions.add("storage", "no solicitado: requiere include_storage")


def _check_bundled_database(database: Path, manifest: BundleManifest) -> None:
    """The manifest is a claim: only the extracted database proves its schema version.

    Its bytes were already checked against the manifest's SHA-256 by `read_bundle`, and a
    bundle carries no `.sha256` sidecar: the digest check is not repeated here.
    """
    try:
        verify_backup(database, check_digest=False)
        actual = _schema_version_of(database)
    except (BackupError, sqlite3.Error, ValueError, TypeError) as exc:
        raise ArchiveRejected("La base de datos de la copia no es válida") from exc
    if actual != manifest.schema_version:
        raise ArchiveRejected("El manifiesto declara otra versión de esquema")


def verify_bundle(path: Path) -> BundleManifest:
    """Check everything a restore relies on. Raises `AppError`, never touches live data."""
    with _exclusive():
        scratch = Path(tempfile.mkdtemp(dir=path.parent, prefix=_WORK_PREFIX))
        try:
            manifest = read_bundle(
                path, extract_to=scratch, select=lambda member: member == DATABASE_MEMBER
            )
            _check_bundled_database(scratch / DATABASE_MEMBER, manifest)
            return manifest
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


def _create_locked(settings: Settings, label: str, include_storage: bool) -> BundleInfo:
    if _LABEL_PATTERN.fullmatch(label) is None:
        raise AppError("backup_invalid_label", "La etiqueta solo admite [a-z0-9-]", 400)
    bundles = _bundles_dir(settings)
    work = _new_work_dir(settings.backups_dir)
    try:
        database = create_backup(settings.db_path, work, "bundle")
        verify_backup(database)
        schema_version = _schema_version_of(database)
        moment = datetime.now(UTC)
        exclusions = _Exclusions()

        def make_manifest(files: list[ManifestFile]) -> BundleManifest:
            exclusions.finish()
            return BundleManifest(
                format_version=FORMAT_VERSION,
                created_at=moment.isoformat(),
                app_version=_app_version(),
                schema_version=schema_version,
                label=label,
                files=files,
                excluded=exclusions.items,
            )

        archive = work / "bundle.tar.gz"
        manifest = write_bundle(
            archive,
            _sources(settings, database, include_storage, exclusions),
            exclusions.items,
            make_manifest,
        )
        verify_bundle(archive)
        name = f"drakter-bundle-{moment.strftime(_STAMP_FORMAT)}-{label}.tar.gz"
        size = archive.stat().st_size
        os.replace(archive, bundles / name)
        _fsync_dir(bundles)
    except _FAILURES as exc:
        logger.error("bundle creation failed", exc_info=exc, extra={"event": "backup_failed"})
        raise AppError("backup_failed", "No se pudo crear la copia", 500) from exc
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return BundleInfo(
        name=name,
        label=label,
        created_at=manifest.created_at,
        size_bytes=size,
        schema_version=manifest.schema_version,
        app_version=manifest.app_version,
        file_count=len(manifest.files),
        includes_storage=include_storage,
        excluded=manifest.excluded,
    )


def create_bundle(settings: Settings, label: str, include_storage: bool = False) -> BundleInfo:
    with _exclusive():
        _bundles_dir(settings)
        _sweep_stale_work(settings)
        return _create_locked(settings, label, include_storage)


def _info_from_name(path: Path) -> BundleInfo | None:
    match = _BUNDLE_NAME.fullmatch(path.name)
    if match is None:
        return None
    try:
        created = datetime.strptime(match.group(1), _STAMP_FORMAT).replace(tzinfo=UTC)
        info = os.lstat(path)
    except (ValueError, OSError):
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return BundleInfo(
        name=path.name,
        label=match.group(2),
        created_at=created.isoformat(),
        size_bytes=info.st_size,
    )


def list_bundles(settings: Settings) -> list[BundleInfo]:
    """Newest first. Temporary files never match the name, so they never show up."""
    found = (_info_from_name(path) for path in _bundles_dir(settings).iterdir())
    bundles = [info for info in found if info is not None]
    return sorted(bundles, key=lambda info: info.name.split("-")[2], reverse=True)


def is_bundle_name(name: str) -> bool:
    return _BUNDLE_NAME.fullmatch(name) is not None


def resolve_bundle(settings: Settings, name: str) -> Path:
    """Map an API identifier to its file. Never accepts a path from the client."""
    if not is_bundle_name(name):
        raise AppError("backup_invalid_name", "El identificador de la copia no es válido", 400)
    bundles = _bundles_dir(settings)
    path = bundles / name
    try:
        info = os.lstat(path)
    except FileNotFoundError as exc:
        raise AppError("backup_not_found", "La copia no existe", 404) from exc
    if not stat.S_ISREG(info.st_mode):
        raise AppError("backup_not_found", "La copia no existe", 404)
    if Path(os.path.realpath(path)).parent != Path(os.path.realpath(bundles)):
        raise AppError("backup_not_found", "La copia no existe", 404)
    return path


def bundle_digest(settings: Settings, name: str) -> str:
    digest = hashlib.sha256()
    with open(resolve_bundle(settings, name), "rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def delete_bundle(settings: Settings, name: str) -> None:
    with _exclusive():
        path = resolve_bundle(settings, name)
        path.unlink()
        _fsync_dir(path.parent)


def ensure_initial_backup(settings: Settings) -> BundleInfo:
    with _exclusive():
        for bundle in list_bundles(settings):
            if bundle.label == INITIAL_LABEL:
                return bundle
        return create_bundle(settings, INITIAL_LABEL)


def prune_auto(settings: Settings, keep: int) -> list[str]:
    """Delete old `auto` bundles only. Every other label is out of reach by construction."""
    if keep < 0:
        raise ValueError("keep must not be negative")
    with _exclusive():
        automatic = [bundle for bundle in list_bundles(settings) if bundle.label == AUTO_LABEL]
        removed = [bundle.name for bundle in automatic[keep:]]
        for name in removed:
            delete_bundle(settings, name)
    return removed


def _copy_private(source: Path, target: Path) -> None:
    """Copy into a new 0600 file, without following a link at either end."""
    with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC), "rb") as reader:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        with os.fdopen(os.open(target, flags, 0o600), "wb") as writer:
            shutil.copyfileobj(reader, writer, _HASH_CHUNK_BYTES)
            writer.flush()
            os.fsync(writer.fileno())


def _swap_tree(staged: Path, live: Path, retired: Path) -> None:
    """Replace a whole directory. The old tree moves out of the live tree, intact."""
    ensure_private_dir(live.parent)
    existed = os.path.lexists(live)
    if existed and (live.is_symlink() or not live.is_dir()):
        raise ValueError(f"No es un directorio real: {live}")
    if existed:
        os.rename(live, retired)
    try:
        os.rename(staged, live)
    except OSError:
        if existed:
            os.rename(retired, live)
        raise


def _restore_config(staged: Path, retired: Path) -> bool:
    """Swap allowlisted files one by one.

    Never the directory: it holds `.env`, which no bundle carries, and it may
    live on another file system than the backups.
    """
    target = _config_dir()
    ensure_private_dir(target)
    any_retired = False
    for name in sorted(CONFIG_ALLOWLIST):
        replacement = staged / name
        if not replacement.is_file():
            continue
        live = target / name
        if os.path.lexists(live) and not live.is_symlink() and live.is_file():
            retired.mkdir(mode=0o700, exist_ok=True)
            _copy_private(live, retired / name)
            any_retired = True
        descriptor, temporary = tempfile.mkstemp(dir=target, prefix=".restore-")
        os.close(descriptor)
        os.unlink(temporary)
        try:
            _copy_private(replacement, Path(temporary))
            os.replace(temporary, live)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    return any_retired


def _run_hooks(settings: Settings, hooks: Sequence[RestoreHook]) -> list[str]:
    """Run them all: one failing must not spare the approvals the next would invalidate."""
    names = [getattr(hook, "__name__", "hook") for hook in hooks]
    if not hooks:
        logger.warning(
            "restore without invalidation hooks", extra={"event": "backup_restore_no_hooks"}
        )
        return []
    try:
        conn = connect(settings.db_path)
    except (OSError, ValueError, sqlite3.Error) as exc:
        logger.error("restore hooks could not run", exc_info=exc)
        return names
    failed: list[str] = []
    with closing(conn):
        for hook, name in zip(hooks, names, strict=True):
            try:
                hook(conn)
                if conn.in_transaction:
                    conn.execute("COMMIT")
            except Exception as exc:
                logger.error("restore hook failed: %s", name, exc_info=exc)
                failed.append(name)
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
    return failed


def _preflight_migration(database: Path, work: Path) -> None:
    """Prove on a throwaway copy that the code can run this database, before replacing the live one."""
    scratch = work / "preflight"
    scratch.mkdir(mode=0o700)
    trial = scratch / "drakter.db"
    _copy_private(database, trial)
    try:
        migrate(trial, scratch / "backups")
    except MigrationError as exc:
        logger.error("restore preflight failed", exc_info=exc)
        raise AppError(
            "backup_incompatible", "La copia no es compatible con esta versión", 409
        ) from exc


class _Progress:
    def __init__(self) -> None:
        self.restored: list[Role] = []
        self.skipped: list[ExcludedItem] = []
        self.retired: list[str] = []


def _skip(role: str, reason: str) -> ExcludedItem:
    return ExcludedItem(what=role, reason=reason)


def _apply_files(
    settings: Settings,
    staging: Path,
    roles: set[Role],
    stamp: str,
    quiesced: bool,
    report: _Progress,
) -> None:
    backups = settings.backups_dir

    def retired_name(role: str) -> Path:
        path = backups / f"{role}.pre-restore-{stamp}"
        report.retired.append(path.name)
        return path

    if "indexes" in roles:
        _swap_tree(staging / "indexes", settings.data_dir / "indexes", retired_name("indexes"))
        report.restored.append("indexes")
    else:
        report.skipped.append(_skip("indexes", "la copia no los contiene: siguen los actuales"))

    if "config" in roles:
        retired = backups / f"config.pre-restore-{stamp}"
        if _restore_config(staging / "config", retired):
            report.retired.append(retired.name)
        report.restored.append("config")
    else:
        report.skipped.append(_skip("config", "la copia no la contiene: sigue la actual"))

    if "openviking" not in roles:
        report.skipped.append(_skip("openviking", "la copia no lo contiene: sigue el actual"))
    elif quiesced:
        target = settings.data_dir / "openviking"
        _swap_tree(staging / "openviking", target, retired_name("openviking"))
        report.restored.append("openviking")
    else:
        report.skipped.append(_skip("openviking", "no hay forma de garantizar el servicio parado"))

    if "storage" in roles:
        _swap_tree(staging / "storage", settings.data_dir / "storage", retired_name("storage"))
        report.restored.append("storage")
    else:
        # A default bundle carries no storage: that is not a request to empty it.
        report.skipped.append(_skip("storage", "la copia no lo contiene: sigue el actual"))


def _restore(
    settings: Settings,
    path: Path,
    work: Path,
    hooks: Sequence[RestoreHook],
    quiesce: Quiesce | None,
) -> RestoreReport:
    # Verify and extract in one pass, so what was checked is what gets applied.
    # Nothing here touches live data; a bad bundle leaves no `pre-restore` behind.
    staging = work / "staging"
    staging.mkdir(mode=0o700)
    manifest = read_bundle(path, extract_to=staging)
    staged_database = staging / DATABASE_MEMBER
    _check_bundled_database(staged_database, manifest)
    if manifest.schema_version > _code_schema_version():
        raise AppError(
            "backup_newer_than_app", "La copia es de una versión más nueva de Drakter", 409
        )
    _preflight_migration(staged_database, work)

    roles = {entry.role for entry in manifest.files}
    quiesced = "openviking" in roles and quiesce is not None
    if quiesced and quiesce is not None:
        try:
            quiesce()
        except Exception as exc:
            logger.error("restore quiesce failed", exc_info=exc)
            raise AppError(
                "backup_quiesce_failed", "No se pudo detener el servicio de memoria", 503
            ) from exc

    try:
        # The rollback point must hold whatever this restore is about to replace.
        previous = _create_locked(settings, PRE_RESTORE_LABEL, "storage" in roles)
    except AppError as exc:
        raise AppError(
            "backup_pre_restore_failed", "No se pudo crear la copia previa: no se tocó nada", 500
        ) from exc

    progress = _Progress()
    hook_failures: list[str] = []
    stamp = _stamp()
    try:
        try:
            previous_database = restore_backup(
                settings.db_path, settings.backups_dir, staged_database
            )
            schema_version = migrate(settings.db_path, settings.backups_dir).to_version
            progress.restored.append("database")
            _apply_files(settings, staging, roles, stamp, quiesced, progress)
        finally:
            # Also on failure: the old database may already be live, and with
            # it the confirmations that this run has to invalidate.
            hook_failures = _run_hooks(settings, hooks)
    except _FAILURES as exc:
        logger.error("restore failed", exc_info=exc, extra={"event": "backup_restore_failed"})
        note = " No se pudieron invalidar las confirmaciones." if hook_failures else ""
        raise AppError(
            "backup_restore_failed",
            f"La restauración falló. Copia previa: {previous.name}.{note}",
            500,
        ) from exc
    return RestoreReport(
        status="partial" if hook_failures else "ok",
        bundle=path.name,
        pre_restore=previous.name,
        pre_restore_database=previous_database.name,
        schema_version=schema_version,
        restored=progress.restored,
        skipped=progress.skipped,
        retired=progress.retired,
        hooks_run=len(hooks),
        hook_failures=hook_failures,
    )


def restore_bundle(
    settings: Settings,
    name: str,
    hooks: Sequence[RestoreHook] = (),
    quiesce: Quiesce | None = None,
) -> RestoreReport:
    with _exclusive():
        path = resolve_bundle(settings, name)
        _sweep_stale_work(settings)
        work = _new_work_dir(settings.backups_dir)
        try:
            return _restore(settings, path, work, hooks, quiesce)
        except _FAILURES as exc:
            logger.error("restore aborted", exc_info=exc, extra={"event": "backup_restore_failed"})
            raise AppError("backup_restore_failed", "No se pudo restaurar la copia", 500) from exc
        finally:
            shutil.rmtree(work, ignore_errors=True)


def _seconds_until_next_auto(settings: Settings) -> float:
    """A desktop app rarely stays up 24 h: count from the last copy, not from this start."""
    for bundle in list_bundles(settings):
        if bundle.label == AUTO_LABEL:
            age = datetime.now(UTC) - datetime.fromisoformat(bundle.created_at)
            return max(0.0, _INTERVAL_SECONDS - age.total_seconds())
    return 0.0


def _run_auto_backup(settings: Settings) -> None:
    create_bundle(settings, AUTO_LABEL)
    prune_auto(settings, _AUTO_KEEP)


async def _scheduler_loop(settings: Settings) -> None:
    delay = _RETRY_SECONDS
    try:
        delay = await asyncio.to_thread(_seconds_until_next_auto, settings)
    except Exception as exc:
        logger.error("backup scheduler could not read bundles", exc_info=exc)
    while True:
        await asyncio.sleep(delay)
        try:
            await asyncio.to_thread(_run_auto_backup, settings)
            delay = _INTERVAL_SECONDS
        except Exception as exc:
            logger.error("automatic backup failed", exc_info=exc)
            delay = _RETRY_SECONDS


def start_backup_scheduler(app: FastAPI) -> asyncio.Task[None]:
    return asyncio.create_task(_scheduler_loop(app.state.settings), name="drakter-backups")
