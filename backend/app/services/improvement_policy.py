"""Which repository paths an improvement patch may touch.

This policy is deterministic and lives in code on purpose: nothing a patch can
change feeds it, and this file is itself protected. It denies by default. A path
is open to the agent only when it sits under an allowed root and is not
protected. Every unclear case (a malformed path, an odd character) counts as
protected.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Final

from app.services.improvement_ports import PrincipalKind

# Compared as written: "Docs/x.md" is not under "docs/" on a case-sensitive disk.
# No backend root: any Python there runs inside the backend process, where it
# could replace this very policy in memory.
AGENT_ALLOWED_ROOTS: Final = (
    "desktop/src/",
    "agent/skills/",
    "docs/",
)

# Everything below is compared against the folded path (see ``_fold``).
_PROTECTED_PREFIXES: Final = (
    "backend/app/core/",
    "backend/app/database/",
    "backend/migrations/",
    "backend/app/tools/",
    "contracts/",
    "agent/identity/",
    "agent/configuration/",
    "agent/policies/",
    "desktop/electron/",
    "desktop/electron-builder.",
    "improvement/",
    "backend/app/services/improvement",
    "backend/app/services/backup",
)
_PROTECTED_FILES: Final = frozenset(
    {
        "docs/implementation_status.md",
        "docs/decisions.md",
        "docs/master_plan.md",
        "docs/roadmap.md",
        "docs/run_state.md",
    }
)
# Prefixes of any single path component, at any depth.
_PROTECTED_COMPONENT_PREFIXES: Final = (".git", ".env", ".claude")
_PROTECTED_BASENAMES: Final = frozenset(
    {
        "claude.md",
        "__init__.py",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "setup.py",
        "setup.cfg",
        ".npmrc",
        ".python-version",
    }
)
_PROTECTED_BASENAME_PREFIXES: Final = ("electron-builder.", "requirements")
# Substrings of the whole path. Beyond the English minimum, this covers the
# stems that miss it ("policies" does not contain "policy") and the Spanish
# names this project also uses.
_PROTECTED_WORDS: Final = (
    "audit",
    "confirm",
    "permission",
    "permis",
    "policy",
    "polic",
    "politic",
    "security",
    "segur",
    "auth",
    "secret",
    "credential",
    "approv",
    "aprob",
)

_DRIVE_PREFIX: Final = re.compile(r"^[A-Za-z]:")


def is_valid_path(path: str) -> bool:
    """Tell whether ``path`` is a clean repository-relative path.

    Rejects absolute paths, ``.``/``..``/empty components, NUL and any control
    character, the ``\\`` separator, drive prefixes and components ending in a
    dot or a space, which Windows would silently rewrite into another name.
    """
    if not isinstance(path, str) or not path:
        return False
    if path.startswith("/") or "\\" in path or _DRIVE_PREFIX.match(path):
        return False
    if any(ord(char) < 0x20 or ord(char) == 0x7f for char in path):
        return False
    return all(
        part not in ("", ".", "..") and part == part.rstrip(" .")
        for part in path.split("/")
    )


def _fold(path: str) -> str:
    """Collapse look-alikes so case, ligatures or invisible marks evade no rule."""
    composed = unicodedata.normalize("NFKC", path)
    visible = "".join(char for char in composed if unicodedata.category(char) != "Cf")
    return visible.casefold()


def is_protected(path: str) -> bool:
    """Return True for a path no agent may touch, and for any malformed path."""
    if not is_valid_path(path):
        return True
    folded = _fold(path)
    if folded in _PROTECTED_FILES or folded.startswith(_PROTECTED_PREFIXES):
        return True
    if folded.startswith("backend/") and folded.endswith(".py"):
        return True
    components = folded.split("/")
    if any(part.startswith(_PROTECTED_COMPONENT_PREFIXES) for part in components):
        return True
    basename = components[-1]
    if basename in _PROTECTED_BASENAMES or basename.startswith(_PROTECTED_BASENAME_PREFIXES):
        return True
    return any(word in folded for word in _PROTECTED_WORDS)


def is_agent_allowed(path: str) -> bool:
    """Return True only for an unprotected path under an allowed root."""
    return not is_protected(path) and path.startswith(AGENT_ALLOWED_ROOTS)


def check_paths(paths: Sequence[str], author: PrincipalKind) -> tuple[str, ...]:
    """Return the ``paths`` denied to ``author``, in order.

    Malformed paths are denied to everyone. A protected path stays open to a
    human, under elevated approval. ``system`` is held to the agent's rules, so
    only the exact ``user`` kind gets the wider path.
    """
    if author == "user":
        return tuple(path for path in paths if not is_valid_path(path))
    return tuple(path for path in paths if not is_agent_allowed(path))
