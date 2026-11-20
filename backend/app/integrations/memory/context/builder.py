"""Builds the context of a turn in the order of CLAUDE.md §8.

Levels 1-4 form `system_prompt`. Conversation, memory and instruction form `turn_prompt`:
a memory never reaches the system prompt, because Hermes treats that as authoritative and
keeps it for the whole session.
"""

from __future__ import annotations

import logging
import os
import secrets
import threading
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final
from uuid import UUID

from app.integrations.memory.context.rules import LEVEL_FILES, SECURITY_RULES
from app.integrations.memory.context.sanitize import (
    UntrustedItem,
    render_item,
    sanitize_untrusted,
    seal_block,
)
from app.integrations.memory.models import (
    ContextBundle,
    ContextSection,
    ConversationTurn,
    PriorityLevel,
    Provenance,
    TrustLevel,
)

logger = logging.getLogger(__name__)

_LARGE_LEVEL_CHARS: Final = 32_000
_JOINER: Final = "\n\n"
_TRUNCATED_MARK: Final = "\n[... truncado por presupuesto ...]"
_INSTRUCTION_LABEL: Final = "Instrucción actual (petición, dentro de las reglas anteriores):\n"
_TURN_TRUST: Final = {"user": TrustLevel.USER_STATED, "assistant": TrustLevel.DERIVED}


class MissingRulesError(RuntimeError):
    """A level 2 file is missing: a turn must not run without the system rules."""


@dataclass(frozen=True)
class MemoryForContext:
    """A retrieved memory. `text` is already at the chosen detail level. L0/L1 are untrusted too."""

    id: UUID
    text: str
    provenance: Provenance
    trust: TrustLevel
    updated_at: datetime


@dataclass(frozen=True)
class ContextBudget:
    """Limits in characters. Levels 1-3 have none: they are never cut."""

    user_context: int = 6_000  # agent/context/ holds 5.3k today; 4k would cut CURRENT_CONTEXT
    conversation: int = 12_000
    memory: int = 6_000
    instruction: int = 8_000
    total: int = 60_000


def _read_level(agent_dir: Path, level: PriorityLevel) -> tuple[str, list[str]]:
    """Text of the level's fixed files and the ones that are missing. Symlinks count as missing."""
    texts: list[str] = []
    missing: list[str] = []
    for relative in LEVEL_FILES[level]:
        path = agent_dir / relative
        if path.is_symlink() or not path.is_file():
            missing.append(relative)
            continue
        texts.append(path.read_text(encoding="utf-8", errors="replace").strip())
    return _JOINER.join(texts), missing


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - len(_TRUNCATED_MARK), 0)] + _TRUNCATED_MARK


def _memory_item(memory: MemoryForContext) -> UntrustedItem:
    source = memory.provenance
    provenance = str(source.source_type)
    if source.source_ref:
        provenance += ":" + source.source_ref
    return UntrustedItem(
        id=str(memory.id),
        text=memory.text,
        provenance=provenance,
        trust=str(memory.trust),
        updated=memory.updated_at.isoformat(),
    )


def _turn_item(index: int, turn: ConversationTurn) -> UntrustedItem:
    return UntrustedItem(
        id="turn-" + str(index),
        text=turn.text,
        provenance="conversation:" + turn.role,
        trust=str(_TURN_TRUST[turn.role]),
    )


def _block_size(rendered: Sequence[str], overhead: int) -> int:
    return overhead + sum(len(item) + 1 for item in rendered) if rendered else 0


def _fit_memories(rendered: list[str], limit: int, overhead: int) -> list[int]:
    """Indexes kept, walking from most to least relevant. An oversized memory is skipped alone."""
    kept: list[int] = []
    used = overhead
    for index, item in enumerate(rendered):
        if used + len(item) + 1 <= limit:
            kept.append(index)
            used += len(item) + 1
    return kept


def _fit_turns(rendered: list[str], limit: int, overhead: int) -> int:
    """First index to keep: the newest turns that fit, with no gaps."""
    used = overhead
    start = len(rendered)
    while start > 0 and used + len(rendered[start - 1]) + 1 <= limit:
        start -= 1
        used += len(rendered[start]) + 1
    return start


_TrustedLevels = tuple[str, str, str]
_Warning = tuple[str, tuple[object, ...]]
_FilesKey = tuple[tuple[int, int, int, int, int] | None, ...]
_CACHE_MAX: Final = 8
_trusted_cache: dict[Path, tuple[_FilesKey, _TrustedLevels, tuple[_Warning, ...]]] = {}
_trusted_lock = threading.Lock()


def _files_key(agent_dir: Path) -> _FilesKey:
    """Identity of every fixed file (lstat: a symlink changes the mode). Any edit changes it."""
    key: list[tuple[int, int, int, int, int] | None] = []
    for level in (PriorityLevel.SYSTEM_RULES, PriorityLevel.IDENTITY, PriorityLevel.USER_CONTEXT):
        for relative in LEVEL_FILES[level]:
            try:
                info = os.lstat(agent_dir / relative)
            except OSError:
                key.append(None)
                continue
            key.append((info.st_mode, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return tuple(key)


def _read_trusted_levels(agent_dir: Path) -> tuple[_TrustedLevels, tuple[_Warning, ...]]:
    system_rules, missing = _read_level(agent_dir, PriorityLevel.SYSTEM_RULES)
    if missing:
        raise MissingRulesError("missing system rules: " + ", ".join(missing))
    warnings: list[_Warning] = []
    identity, missing = _read_level(agent_dir, PriorityLevel.IDENTITY)
    warnings.extend(("identity file not available, skipped: %s", (relative,)) for relative in missing)
    user_context, missing = _read_level(agent_dir, PriorityLevel.USER_CONTEXT)
    warnings.extend(("user context file not available, skipped: %s", (relative,)) for relative in missing)
    for level, text in ((PriorityLevel.SYSTEM_RULES, system_rules), (PriorityLevel.IDENTITY, identity)):
        if len(text) > _LARGE_LEVEL_CHARS:
            warnings.append(("level %s is large and is never cut: %d chars", (level.name, len(text))))
    return (system_rules, identity, sanitize_untrusted(user_context)), tuple(warnings)


def _load_trusted_levels(agent_dir: Path) -> _TrustedLevels:
    """Levels 2-4, cached by the identity of their files (sanitizing level 4 costs ~5 ms a turn).

    The key is taken before reading, so a file edited mid-read is read again next turn.
    A missing level 2 file raises every time: errors are never cached. Warnings repeat each turn.
    """
    key = _files_key(agent_dir)
    with _trusted_lock:
        cached = _trusted_cache.get(agent_dir)
    if cached is not None and cached[0] == key:
        levels, warnings = cached[1], cached[2]
    else:
        levels, warnings = _read_trusted_levels(agent_dir)
        with _trusted_lock:
            if len(_trusted_cache) >= _CACHE_MAX:
                _trusted_cache.clear()
            _trusted_cache[agent_dir] = (key, levels, warnings)
    for message, args in warnings:
        logger.warning(message, *args)
    return levels


def build_context(
    *,
    instruction: str,
    conversation: Sequence[ConversationTurn] = (),
    memories: Sequence[MemoryForContext] = (),
    agent_dir: Path,
    budget: ContextBudget = ContextBudget(),
) -> ContextBundle:
    """Assemble a turn. `memories` go most relevant first; `conversation` oldest first."""
    system_rules, identity, full_user_context = _load_trusted_levels(Path(agent_dir))

    full_request = sanitize_untrusted(instruction)
    request = _truncate(full_request, budget.instruction)
    instruction_text = _INSTRUCTION_LABEL + request

    # One boundary per block, so that each marker closes exactly once.
    conversation_nonce = secrets.token_hex(16)
    memory_nonce = secrets.token_hex(16)
    overhead = len(seal_block((), memory_nonce))

    turns = [render_item(_turn_item(i, turn)) for i, turn in enumerate(conversation)]
    memory_items = [render_item(_memory_item(memory)) for memory in memories]

    turn_start = _fit_turns(turns, budget.conversation, overhead)
    kept_memories = _fit_memories(memory_items, budget.memory, overhead)

    fixed = sum(
        len(text) + len(_JOINER)
        for text in (SECURITY_RULES, system_rules, identity, instruction_text)
        if text
    )
    user_context = _truncate(full_user_context, budget.user_context)

    def excess() -> int:
        selected = [memory_items[i] for i in kept_memories]
        sizes = (
            _block_size(selected, overhead),
            _block_size(turns[turn_start:], overhead),
            len(user_context),
        )
        return fixed + sum(size + len(_JOINER) for size in sizes if size) - budget.total

    # Cut order: memory, then oldest turns, then level 4.
    while excess() > 0 and kept_memories:
        kept_memories.pop()
    while excess() > 0 and turn_start < len(turns):
        turn_start += 1
    overflow = excess()
    if overflow > 0 and user_context:
        user_context = _truncate(full_user_context, len(user_context) - overflow)

    sections = [
        _section(PriorityLevel.SECURITY, "security", SECURITY_RULES, trusted=True),
        _section(PriorityLevel.SYSTEM_RULES, "system_rules", system_rules, trusted=True),
    ]
    if identity:
        sections.append(_section(PriorityLevel.IDENTITY, "identity", identity, trusted=True))
    if user_context:
        sections.append(
            _section(
                PriorityLevel.USER_CONTEXT,
                "user_context",
                user_context,
                trusted=True,
                truncated=user_context != full_user_context,
            )
        )
    if turns[turn_start:]:
        sections.append(
            _section(
                PriorityLevel.CONVERSATION,
                "conversation",
                seal_block(turns[turn_start:], conversation_nonce),
                trusted=False,
                truncated=turn_start > 0,
            )
        )
    if kept_memories:
        sections.append(
            _section(
                PriorityLevel.MEMORY,
                "memory",
                seal_block([memory_items[i] for i in kept_memories], memory_nonce),
                trusted=False,
                truncated=len(kept_memories) < len(memories),
            )
        )
    sections.append(
        _section(
            PriorityLevel.CURRENT_INSTRUCTION,
            "instruction",
            instruction_text,
            trusted=True,
            truncated=request != full_request,
        )
    )

    kept = set(kept_memories)
    return ContextBundle(
        sections=tuple(sections),
        system_prompt=_join(s for s in sections if s.level <= PriorityLevel.USER_CONTEXT),
        turn_prompt=_join(s for s in sections if s.level > PriorityLevel.USER_CONTEXT),
        memory_ids=tuple(memories[i].id for i in kept_memories),
        dropped_memory_ids=tuple(m.id for i, m in enumerate(memories) if i not in kept),
        tainted=bool(kept_memories) or turn_start < len(turns),
    )


def _section(
    level: PriorityLevel, name: str, text: str, *, trusted: bool, truncated: bool = False
) -> ContextSection:
    return ContextSection(
        level=level, name=name, text=text, trusted=trusted, truncated=truncated, chars=len(text)
    )


def _join(sections: Iterable[ContextSection]) -> str:
    return _JOINER.join(section.text for section in sections)
