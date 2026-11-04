"""Isolated evaluation and Git publication of improvement patches.

A patch is untrusted, whoever wrote it. The real checkout is never modified:
every operation works on a throwaway clone, truth about a patch comes from Git
after applying it (never from parsing it), checks come from the base commit and
run inside ``bwrap`` over an export without ``.git``, and the only write to the
real repository is one ``improvement/<id>`` ref. If the sandbox cannot start, the
result is ``blocked``; nothing ever runs outside it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import unicodedata
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from platformdirs import user_config_dir
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.config import Settings, ensure_private_dir
from app.core.errors import AppError
from app.services.improvement_policy import is_agent_allowed, is_protected, is_valid_path
from app.services.improvement_ports import PrincipalKind

logger = logging.getLogger("drakter.improvement")

_TOOL_PATH: Final = "/usr/bin:/bin"
_GIT_TIMEOUT_S: Final = 120
_MAX_PATCH_BYTES: Final = 2 * 1024 * 1024
_MAX_CHANGED_PATHS: Final = 200
_MAX_MESSAGE_BYTES: Final = 4096
_OUTPUT_TAIL_BYTES: Final = 8 * 1024

_EVALUATIONS_PATH: Final = "improvement/evaluations/default.json"
_MAX_EVALUATIONS_BYTES: Final = 64 * 1024
_MAX_CHECKS: Final = 20
_MAX_CHECK_TIMEOUT_S: Final = 300
_CHECK_NAME: Final = re.compile(r"^[a-z0-9_-]{1,64}$")

_SANDBOX_WORK: Final = "/work"
_SANDBOX_HOME: Final = "/home-sandbox"
_SANDBOX_DIFF: Final = "/input/changes.diff"
_SANDBOX_TMPFS_BYTES: Final = 256 * 1024 * 1024
_PREFLIGHT_TIMEOUT_S: Final = 20
_LIMIT_AS_BYTES: Final = 2 * 1024 * 1024 * 1024
_LIMIT_FSIZE_BYTES: Final = 128 * 1024 * 1024
_LIMIT_NOFILE: Final = 1024
# RLIMIT_NPROC counts every thread of the uid, not only the sandboxed ones, so a
# tight value would block evaluations on a busy desktop.
_LIMIT_NPROC: Final = 8192

_ALLOWED_MODES: Final = frozenset({"000000", "100644", "100755"})
_COMMIT_SHA: Final = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_BRANCH_PREFIX: Final = "improvement/"
# Refuses before applying: a small delta patch can inflate into a huge blob.
_BINARY_PATCH: Final = re.compile(rb"^(?:GIT binary patch|literal \d+|delta \d+)\r?$", re.M)

_COMMIT_NAME: Final = "Drakter Improvement"
_COMMIT_EMAIL: Final = "improvement@drakter.local"

# Passed on every call, so neither the real repo's config nor the user's can
# start a helper. Global and system config are off in ``_git_env``.
_GIT_OVERRIDES: Final = (
    "core.hooksPath=/dev/null",
    "core.fsmonitor=false",
    "core.attributesFile=/dev/null",
    "core.excludesFile=/dev/null",
    "core.autocrlf=false",
    "core.sshCommand=/bin/false",
    "core.protectHFS=true",
    "core.protectNTFS=true",
    "protocol.allow=never",
    "protocol.file.allow=always",
    "protocol.ext.allow=never",
    "commit.gpgsign=false",
    "tag.gpgsign=false",
    "gc.auto=0",
    "maintenance.auto=false",
    "submodule.recurse=false",
    "fetch.recurseSubmodules=false",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    exit_code: int | None
    output_tail: str


@dataclass(frozen=True)
class EvaluationOutcome:
    status: Literal["passed", "failed", "blocked"]
    base_commit: str | None
    patch_sha256: str
    changed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    checks: tuple[CheckResult, ...]
    reason: str | None


@dataclass(frozen=True)
class AppliedChange:
    branch: str
    commit: str


@dataclass(frozen=True)
class LabConfig:
    repo_path: Path | None
    experiments_dir: Path


@dataclass(frozen=True)
class _Check:
    name: str
    argv: tuple[str, ...]
    timeout_s: int


@dataclass(frozen=True)
class _Sandbox:
    prefix: tuple[str, ...]
    python: str


class _Blocked(Exception):
    """The lab cannot judge the patch. ``reason`` is a fixed, safe sentence."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Rejected(Exception):
    """The patch is not acceptable. ``reason`` is a fixed, safe sentence."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _LabSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DRAKTER_IMPROVEMENT_",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    repo: Path | None = None


def load_lab_config(settings: Settings) -> LabConfig:
    """Build the lab configuration. A packaged install has no repository."""
    experiments_dir = settings.data_dir / "improvement" / "experiments"
    ensure_private_dir(experiments_dir)
    if getattr(sys, "frozen", False):
        return LabConfig(repo_path=None, experiments_dir=experiments_dir)
    env_file = Path(user_config_dir("drakter")) / ".env"
    configured = _LabSettings(_env_file=env_file).repo  # type: ignore[call-arg]
    repo = configured.expanduser() if configured is not None else None
    if repo is not None and not repo.is_absolute():
        logger.warning("Ignoring DRAKTER_IMPROVEMENT_REPO: it must be an absolute path")
        repo = None
    return LabConfig(repo_path=repo, experiments_dir=experiments_dir)


def _find_tool(name: str) -> str | None:
    return shutil.which(name, path=_TOOL_PATH)


def _find_bwrap() -> str | None:
    return _find_tool("bwrap")


def _git_env(cwd: Path) -> dict[str, str]:
    # Built from nothing, so GIT_DIR, GIT_CONFIG_*, GIT_EXTERNAL_DIFF and any
    # secret in the backend environment never reach Git.
    return {
        "PATH": _TOOL_PATH,
        "HOME": "/nonexistent",
        "XDG_CONFIG_HOME": "/nonexistent",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CEILING_DIRECTORIES": str(cwd.parent),
    }


def _git(
    cwd: Path,
    *args: str,
    stdin: bytes | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    git = _find_tool("git")
    if git is None:
        raise _Blocked("git no está disponible")
    argv = [git]
    for override in _GIT_OVERRIDES:
        argv += ["-c", override]
    argv += args
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            env=_git_env(cwd) | (extra_env or {}),
            input=stdin,
            stdin=None if stdin is not None else subprocess.DEVNULL,
            capture_output=True,
            timeout=_GIT_TIMEOUT_S,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise _Blocked("Una operación de git superó el tiempo límite") from exc
    except OSError as exc:
        raise _Blocked("No se pudo ejecutar git sobre el repositorio") from exc


def _git_ok(cwd: Path, *args: str, stdin: bytes | None = None) -> bytes:
    result = _git(cwd, *args, stdin=stdin)
    if result.returncode != 0:
        raise _Blocked(f"Falló la operación git {args[0]}")
    return result.stdout


def _read_ref(repo: Path, ref: str) -> str | None:
    result = _git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return result.stdout.decode("ascii").strip() if result.returncode == 0 else None


def _resolve_base(repo: Path) -> str:
    base = _read_ref(repo, "HEAD")
    if base is None:
        raise _Blocked("El repositorio no tiene un commit base")
    return base


def _clone(repo: Path, root: Path) -> Path:
    clone = root / "clone"
    _git_ok(
        root,
        "clone",
        "--quiet",
        "--no-hardlinks",
        "--no-checkout",
        "--template=",
        "--",
        str(repo),
        str(clone),
    )
    return clone


def _prescreen(patch: bytes) -> None:
    """Cheap refusals before any clone. The real verdict comes after applying."""
    if not patch.strip():
        raise _Rejected("El parche está vacío")
    if len(patch) > _MAX_PATCH_BYTES:
        raise _Rejected("El parche supera el tamaño máximo")
    if b"\0" in patch or _BINARY_PATCH.search(patch):
        raise _Rejected("El parche contiene contenido binario")


def _inspect_applied(clone: Path, base: str) -> tuple[str, ...]:
    """Return the paths really changed, refusing anything but plain text files."""
    raw = _git_ok(
        clone, "diff", "--cached", "--raw", "--no-renames", "--no-abbrev", "--no-ext-diff",
        "-z", base,
    )  # fmt: skip
    fields = raw.split(b"\0")
    if fields[-1] != b"" or len(fields) % 2 != 1:
        raise _Blocked("Respuesta inesperada de git diff")
    entries = list(zip(fields[:-1:2], fields[1:-1:2], strict=True))
    if not entries:
        raise _Rejected("El parche no produce cambios")
    if len(entries) > _MAX_CHANGED_PATHS:
        raise _Rejected("El parche cambia demasiados archivos")

    paths: list[str] = []
    for meta, raw_path in entries:
        old_mode, new_mode, _, new_sha, _ = meta.decode("ascii").lstrip(":").split(" ")
        if old_mode not in _ALLOWED_MODES or new_mode not in _ALLOWED_MODES:
            raise _Rejected("El parche toca enlaces simbólicos o submódulos")
        if new_mode != "000000":
            # Own NUL scan: Git's binary test obeys .gitattributes, which a
            # patch can add.
            if b"\0" in _git_ok(clone, "cat-file", "blob", new_sha):
                raise _Rejected("El parche produce archivos binarios")
        # An undecodable name gains a backslash here, so the policy refuses it.
        paths.append(raw_path.decode("utf-8", "backslashreplace"))
    return tuple(paths)


def _apply_to_clone(clone: Path, base: str, patch: bytes) -> tuple[str, ...]:
    _git_ok(clone, "checkout", "--quiet", "--detach", base)
    applied = _git(clone, "apply", "--index", "--whitespace=nowarn", stdin=patch)
    if applied.returncode != 0:
        raise _Rejected("El parche no aplica sobre el commit base")
    return _inspect_applied(clone, base)


def _policy_violation(paths: Sequence[str], author: PrincipalKind) -> str | None:
    if not all(is_valid_path(path) for path in paths):
        return "El parche contiene rutas inválidas"
    # Only a human gets the elevated path: "system" is held to the agent's rules.
    if author == "user":
        return None
    if not all(is_agent_allowed(path) for path in paths):
        return "El parche toca rutas protegidas o fuera de las permitidas al agente"
    return None


def _parse_check(raw: object) -> _Check:
    if not isinstance(raw, dict):
        raise ValueError("check must be an object")
    name, argv, timeout_s = raw.get("name"), raw.get("argv"), raw.get("timeout_s")
    if not isinstance(name, str) or _CHECK_NAME.fullmatch(name) is None:
        raise ValueError("invalid check name")
    if not isinstance(argv, list) or not argv or not all(isinstance(a, str) for a in argv):
        raise ValueError("invalid check argv")
    if (
        not isinstance(timeout_s, int)
        or isinstance(timeout_s, bool)
        or not 1 <= timeout_s <= _MAX_CHECK_TIMEOUT_S
    ):
        raise ValueError("invalid check timeout")
    return _Check(name=name, argv=tuple(argv), timeout_s=timeout_s)


def _load_checks(clone: Path, base: str) -> tuple[_Check, ...]:
    """Read the checks from the base commit: the patched tree has no say."""
    result = _git(clone, "cat-file", "blob", f"{base}:{_EVALUATIONS_PATH}")
    if result.returncode != 0 or len(result.stdout) > _MAX_EVALUATIONS_BYTES:
        raise _Blocked("El commit base no define evaluaciones utilizables")
    try:
        document = json.loads(result.stdout)
        raw_checks = document["checks"]
        if not isinstance(raw_checks, list) or not 1 <= len(raw_checks) <= _MAX_CHECKS:
            raise ValueError("invalid check list")
        return tuple(_parse_check(raw) for raw in raw_checks)
    except (ValueError, KeyError, TypeError) as exc:
        raise _Blocked("Las evaluaciones del commit base no son válidas") from exc


def _interpreter() -> tuple[str, Path]:
    """Return the base interpreter and its prefix; a venv is not usable inside."""
    executable = Path(getattr(sys, "_base_executable", None) or sys.executable).resolve()
    return str(executable), Path(sys.base_prefix).resolve()


def _system_mounts() -> list[str]:
    """Mirror the merged-/usr layout of the host; only /usr itself is bound."""
    args = ["--ro-bind", "/usr", "/usr"]
    for name in ("bin", "sbin", "lib", "lib32", "lib64"):
        path = Path("/") / name
        if path.is_symlink():
            args += ["--symlink", os.readlink(path), str(path)]
        elif path.is_dir():
            args += ["--ro-bind", str(path), str(path)]
    return args


def _build_sandbox(bwrap: str, root: Path) -> _Sandbox:
    python, prefix = _interpreter()
    sensitive = (Path.home(), Path.home() / ".config", root)
    if any(path.is_relative_to(prefix) for path in sensitive):
        raise _Blocked("El prefijo del intérprete expondría datos del usuario al sandbox")
    if not Path(python).is_relative_to(prefix) and not Path(python).is_relative_to("/usr"):
        raise _Blocked("El intérprete no es accesible desde el sandbox")

    limits: list[str] = []
    prlimit = _find_tool("prlimit")
    if prlimit is not None:
        limits = [
            prlimit,
            f"--as={_LIMIT_AS_BYTES}",
            f"--nproc={_LIMIT_NPROC}",
            f"--nofile={_LIMIT_NOFILE}",
            f"--fsize={_LIMIT_FSIZE_BYTES}",
            "--core=0",
        ]
    tmpfs_size = str(_SANDBOX_TMPFS_BYTES)
    command = [
        *limits,
        bwrap,
        "--unshare-all",
        # --unshare-all only tries the user namespace: without it, fail, not degrade.
        "--unshare-user",
        "--disable-userns",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
        "--cap-drop", "ALL",
        *_system_mounts(),
    ]  # fmt: skip
    if not prefix.is_relative_to("/usr"):
        command += ["--ro-bind", str(prefix), str(prefix)]
    command += [
        "--proc", "/proc",
        "--dev", "/dev",
        "--size", tmpfs_size, "--tmpfs", "/tmp",
        "--size", tmpfs_size, "--tmpfs", _SANDBOX_HOME,
        "--ro-bind", str(root / "run"), _SANDBOX_WORK,
        "--ro-bind", str(root / "input"), str(Path(_SANDBOX_DIFF).parent),
        "--chdir", _SANDBOX_WORK,
        "--setenv", "HOME", _SANDBOX_HOME,
        "--setenv", "PATH", _TOOL_PATH,
        "--setenv", "LC_ALL", "C.UTF-8",
        "--setenv", "TMPDIR", "/tmp",
        "--",
    ]  # fmt: skip
    return _Sandbox(prefix=tuple(command), python=python)


def _clean_output(tail: bytes) -> str:
    text = tail.decode("utf-8", "replace")
    return "".join(
        char
        for char in text
        if char in "\n\t" or unicodedata.category(char) not in ("Cc", "Cf")
    )


def _run_in_sandbox(
    sandbox: _Sandbox, argv: Sequence[str], timeout_s: int, cwd: Path
) -> tuple[int | None, str]:
    """Run ``argv`` in the sandbox. Return (exit code or None on timeout, output)."""
    process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        [*sandbox.prefix, *argv],
        cwd=cwd,
        env={"PATH": _TOOL_PATH},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    tail = bytearray()

    def pump() -> None:
        assert process.stdout is not None
        while chunk := process.stdout.read1(64 * 1024):  # type: ignore[attr-defined]
            tail.extend(chunk)
            del tail[:-_OUTPUT_TAIL_BYTES]

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    exit_code: int | None
    try:
        exit_code = process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        exit_code = None
        # bwrap leads the group; killing it takes down its whole PID namespace.
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    reader.join(timeout=2)
    if not reader.is_alive() and process.stdout is not None:
        process.stdout.close()
    return exit_code, _clean_output(bytes(tail))


def _prepare_run(clone: Path, root: Path, base: str) -> None:
    """Export the patched index without ``.git``, plus the diff the checks read."""
    run_dir, input_dir = root / "run", root / "input"
    ensure_private_dir(run_dir)
    ensure_private_dir(input_dir)
    _git_ok(clone, "checkout-index", "--all", f"--prefix={run_dir}/")
    diff = _git_ok(
        clone, "diff", "--cached", "--no-color", "--no-ext-diff", "--no-textconv",
        "--no-renames", "--unified=0", base,
    )  # fmt: skip
    (input_dir / Path(_SANDBOX_DIFF).name).write_bytes(diff)


def _run_checks(root: Path, checks: Sequence[_Check]) -> tuple[CheckResult, ...]:
    bwrap = _find_bwrap()
    if bwrap is None:
        raise _Blocked("bwrap no está instalado: no hay entorno aislado")
    sandbox = _build_sandbox(bwrap, root)
    try:
        started, _ = _run_in_sandbox(
            sandbox, (sandbox.python, "-I", "-c", "pass"), _PREFLIGHT_TIMEOUT_S, root
        )
    except OSError as exc:
        raise _Blocked("El entorno aislado bwrap no arranca") from exc
    if started != 0:
        raise _Blocked(
            "El entorno aislado bwrap no arranca "
            "(espacios de nombres de usuario no disponibles o restringidos)"
        )

    placeholders = {"{python}": sandbox.python, "{diff}": _SANDBOX_DIFF}
    results: list[CheckResult] = []
    for check in checks:
        argv = [placeholders.get(arg, arg) for arg in check.argv]
        try:
            exit_code, output = _run_in_sandbox(sandbox, argv, check.timeout_s, root)
        except OSError as exc:
            raise _Blocked("El entorno aislado bwrap no arranca") from exc
        results.append(
            CheckResult(
                name=check.name,
                passed=exit_code == 0,
                exit_code=exit_code,
                output_tail=output,
            )
        )
    return tuple(results)


def _require_proposal_id(proposal_id: str) -> None:
    """Accept only the canonical form: this value becomes a path and a ref."""
    try:
        canonical = str(uuid.UUID(proposal_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise AppError("invalid_proposal_id", "Identificador de propuesta inválido", 422) from exc
    if canonical != proposal_id:
        raise AppError("invalid_proposal_id", "Identificador de propuesta inválido", 422)


@contextmanager
def _experiment(config: LabConfig, proposal_id: str) -> Iterator[Path]:
    parent = config.experiments_dir / proposal_id
    root = parent / str(uuid.uuid4())
    try:
        ensure_private_dir(root)
    except (OSError, ValueError) as exc:
        raise _Blocked("No se pudo preparar el directorio del experimento") from exc
    try:
        yield root
    finally:
        try:
            shutil.rmtree(root)
        except OSError:
            logger.warning("Could not remove experiment %s", root.name)
        with suppress(OSError):
            parent.rmdir()  # still in use by a concurrent experiment otherwise


def _evaluate(
    repo: Path, root: Path, patch: bytes, digest: str, author: PrincipalKind, base: str
) -> EvaluationOutcome:
    clone = _clone(repo, root)
    changed = _apply_to_clone(clone, base, patch)
    protected = tuple(path for path in changed if is_protected(path))

    def outcome(
        status: Literal["passed", "failed", "blocked"],
        checks: tuple[CheckResult, ...] = (),
        reason: str | None = None,
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            status=status,
            base_commit=base,
            patch_sha256=digest,
            changed_paths=changed,
            protected_paths=protected,
            checks=checks,
            reason=reason,
        )

    # Policy first: a forbidden patch is failed for good, whatever the sandbox does.
    violation = _policy_violation(changed, author)
    if violation is not None:
        return outcome("failed", reason=violation)
    try:
        checks = _load_checks(clone, base)
        _prepare_run(clone, root, base)
        results = _run_checks(root, checks)
    except (_Blocked, OSError, ValueError) as exc:
        reason = exc.reason if isinstance(exc, _Blocked) else "No se pudo preparar la evaluación"
        return outcome("blocked", reason=reason)
    if all(result.passed for result in results):
        return outcome("passed", results)
    return outcome("failed", results, "Alguna comprobación no ha pasado")


def evaluate_patch(
    config: LabConfig, proposal_id: str, patch: bytes, author: PrincipalKind
) -> EvaluationOutcome:
    """Judge ``patch`` on a throwaway clone. The real repository stays untouched."""
    _require_proposal_id(proposal_id)
    digest = hashlib.sha256(patch).hexdigest()

    def early(
        status: Literal["failed", "blocked"], reason: str, base: str | None
    ) -> EvaluationOutcome:
        return EvaluationOutcome(
            status=status,
            base_commit=base,
            patch_sha256=digest,
            changed_paths=(),
            protected_paths=(),
            checks=(),
            reason=reason,
        )

    if config.repo_path is None:
        return early("blocked", "No hay repositorio configurado para evaluar", None)
    base: str | None = None
    try:
        base = _resolve_base(config.repo_path)
        _prescreen(patch)
        with _experiment(config, proposal_id) as root:
            return _evaluate(config.repo_path, root, patch, digest, author, base)
    except _Blocked as exc:
        return early("blocked", exc.reason, base)
    except _Rejected as exc:
        return early("failed", exc.reason, base)
    except OSError:
        return early("blocked", "No se pudo preparar la evaluación", base)


def _require_repo(config: LabConfig) -> Path:
    if config.repo_path is None:
        raise AppError(
            "improvement_repo_unconfigured",
            "No hay repositorio configurado para la automejora",
            409,
        )
    return config.repo_path


def _commit_message(message: str) -> bytes:
    encoded = message.strip().encode("utf-8", "replace")
    if not encoded or b"\0" in encoded or len(encoded) > _MAX_MESSAGE_BYTES:
        raise AppError("invalid_commit_message", "Mensaje de commit inválido", 422)
    return encoded


def _commit(clone: Path, base: str, message: bytes) -> str:
    # The dates come from the base so that retrying the same approved change
    # rebuilds the same commit, and "another commit on the branch" means a conflict.
    timestamp = _git_ok(clone, "show", "--no-patch", "--format=%ct", base).decode("ascii").strip()
    date = f"{timestamp} +0000"
    committed = _git(
        clone,
        "commit", "--quiet", "--no-verify", "--no-gpg-sign", "--cleanup=whitespace", "-F", "-",
        stdin=message,
        extra_env={
            "GIT_AUTHOR_NAME": _COMMIT_NAME,
            "GIT_AUTHOR_EMAIL": _COMMIT_EMAIL,
            "GIT_AUTHOR_DATE": date,
            "GIT_COMMITTER_NAME": _COMMIT_NAME,
            "GIT_COMMITTER_EMAIL": _COMMIT_EMAIL,
            "GIT_COMMITTER_DATE": date,
        },
    )  # fmt: skip
    if committed.returncode != 0:
        raise _Blocked("No se pudo crear el commit de la propuesta")
    commit = _read_ref(clone, "HEAD")
    if commit is None:
        raise _Blocked("No se pudo crear el commit de la propuesta")
    return commit


def _branch_conflict() -> AppError:
    return AppError(
        "improvement_branch_conflict", "La rama de la propuesta apunta a otro commit", 409
    )


def _publish(repo: Path, clone: Path, ref: str, commit: str) -> None:
    """Bring the commit into the real repo as one new ref, and change nothing else."""
    current = _read_ref(repo, ref)
    if current == commit:
        return
    if current is not None:
        raise _branch_conflict()
    _git(
        repo,
        "fetch", "--quiet", "--no-tags", "--no-write-fetch-head", "--no-auto-gc",
        "--no-recurse-submodules", "--no-prune", "--", str(clone), f"HEAD:{ref}",
    )  # fmt: skip
    published = _read_ref(repo, ref)
    if published is None:
        raise _Blocked("No se pudo publicar la rama de la propuesta")
    if published != commit:
        raise _branch_conflict()


def apply_patch(
    config: LabConfig, proposal_id: str, patch: bytes, base_commit: str, message: str
) -> AppliedChange:
    """Publish an approved patch as branch ``improvement/<id>``.

    Everything is validated again on a fresh clone. No author is passed in: the
    agent rule is final in ``evaluate_patch``, and here only what no author may
    do is enforced. The caller must hold a ``passed`` outcome for this digest.
    Never merges, never pushes, never touches HEAD, the index or other branches.
    """
    repo = _require_repo(config)
    _require_proposal_id(proposal_id)
    if _COMMIT_SHA.fullmatch(base_commit) is None:
        raise AppError("invalid_base_commit", "Commit base inválido", 422)
    encoded_message = _commit_message(message)
    branch = f"{_BRANCH_PREFIX}{proposal_id}"
    try:
        _prescreen(patch)
        with _experiment(config, proposal_id) as root:
            clone = _clone(repo, root)
            if _git(clone, "cat-file", "-e", f"{base_commit}^{{commit}}").returncode != 0:
                raise AppError("base_commit_missing", "El commit base ya no existe", 409)
            changed = _apply_to_clone(clone, base_commit, patch)
            violation = _policy_violation(changed, "user")
            if violation is not None:
                raise _Rejected(violation)
            commit = _commit(clone, base_commit, encoded_message)
            _publish(repo, clone, f"refs/heads/{branch}", commit)
    except _Rejected as exc:
        raise AppError("improvement_patch_rejected", exc.reason, 409) from exc
    except _Blocked as exc:
        raise AppError("improvement_lab_unavailable", exc.reason, 503) from exc
    except OSError as exc:
        raise AppError(
            "improvement_lab_unavailable", "No se pudo preparar el experimento", 503
        ) from exc
    return AppliedChange(branch=branch, commit=commit)


def _is_merged(repo: Path, commit: str, ref: str) -> bool:
    if _git(repo, "merge-base", "--is-ancestor", commit, "HEAD").returncode == 0:
        return True
    # HEAD may be a work branch while the merge landed in main.
    containing = _git(repo, "for-each-ref", "--contains", commit, "--format=%(refname)",
                      "refs/heads/")  # fmt: skip
    if containing.returncode != 0:
        return False  # the commit is gone, so nothing can contain it
    return any(line != ref for line in containing.stdout.decode("utf-8", "replace").splitlines())


def revert_change(config: LabConfig, change: AppliedChange) -> None:
    """Drop an unmerged proposal branch. A merged change must be reverted by hand."""
    repo = _require_repo(config)
    proposal_id = change.branch.removeprefix(_BRANCH_PREFIX)
    _require_proposal_id(proposal_id)
    # Rebuilt from a validated id, so no caller can aim this at any other ref.
    ref = f"refs/heads/{_BRANCH_PREFIX}{proposal_id}"
    if not change.branch.startswith(_BRANCH_PREFIX) or _COMMIT_SHA.fullmatch(change.commit) is None:
        raise AppError("invalid_change", "Cambio aplicado inválido", 422)
    try:
        if _is_merged(repo, change.commit, ref):
            raise AppError(
                "change_already_merged",
                "El cambio ya está integrado: hay que revertirlo a mano",
                409,
            )
        current = _read_ref(repo, ref)
        if current is None:
            return
        if current != change.commit:
            raise _branch_conflict()
        if _git(repo, "update-ref", "-d", ref, change.commit).returncode != 0:
            raise _branch_conflict()
    except _Blocked as exc:
        raise AppError("improvement_lab_unavailable", exc.reason, 503) from exc
