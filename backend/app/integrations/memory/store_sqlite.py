"""SQLite + FTS5 memory store. Never creates schema; see schemas/ddl_memory.sql."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.core.text import strip_invisible
from app.database.connection import connect
from app.integrations.memory.models import (
    L0_MAX_CHARS,
    L1_MAX_CHARS,
    BackendStatus,
    ConflictStatus,
    DetailLevel,
    EntityRef,
    ForgetReport,
    MemoryCategory,
    MemoryConflict,
    MemoryDraft,
    MemoryFilter,
    MemoryHit,
    MemoryKind,
    MemoryPatch,
    MemoryQuery,
    MemoryRecord,
    MemoryStatus,
    Provenance,
    SourceType,
    TrustLevel,
)

_SPACES = re.compile(r"\s+")
_TERM = re.compile(r"\w+")
_MAX_QUERY_TERMS = 16
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # fixed width: text order is time order


def _collapse(text: str) -> str:
    return _SPACES.sub(" ", text).strip()


def content_hash(text: str) -> str:
    """sha256 of the content normalized: NFKC, lowercase, collapsed spaces."""
    normalized = _collapse(unicodedata.normalize("NFKC", strip_invisible(text)).lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_subject(text: str) -> str:
    """Conflict key: NFKC, lowercase, no diacritics, collapsed spaces."""
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", strip_invisible(text)).lower())
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _collapse(unicodedata.normalize("NFKC", stripped))


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _to_text(value: datetime) -> str:
    return _utc(value).strftime(_DATE_FORMAT)


def _from_text(value: str) -> datetime:
    return _utc(datetime.fromisoformat(value))


def _opt_from_text(value: str | None) -> datetime | None:
    return None if value is None else _from_text(value)


def _now() -> datetime:
    return datetime.now(UTC)


def _fts_query(text: str, limit: int = _MAX_QUERY_TERMS) -> str | None:
    """Quote every term and join with OR; user text never reaches FTS syntax raw."""
    seen: dict[str, None] = {}
    for term in _TERM.findall(unicodedata.normalize("NFKC", text)):
        seen.setdefault(term.lower(), None)
    terms = list(seen)[:limit]
    return " OR ".join(f'"{term}"' for term in terms) if terms else None


def _marks(count: int) -> str:
    return ", ".join("?" for _ in range(count))


@contextmanager
def _transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


class SqliteMemoryAdapter:
    """MemoryAdapter over SQLite. One connection per operation."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)

    def _open(self) -> closing[sqlite3.Connection]:
        conn = connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return closing(conn)

    # -- row mapping -------------------------------------------------------

    @staticmethod
    def _record(conn: sqlite3.Connection, row: sqlite3.Row) -> MemoryRecord:
        refs = conn.execute(
            "SELECT entity_type, entity_id FROM memory_entity_refs WHERE memory_id = ? ORDER BY position",
            (row["id"],),
        ).fetchall()
        return MemoryRecord(
            id=UUID(row["id"]),
            kind=MemoryKind(row["kind"]),
            category=MemoryCategory(row["category"]),
            subject=row["subject"],
            content=row["content"],
            abstract=row["abstract"],
            overview=row["overview"],
            provenance=Provenance(
                source_type=SourceType(row["source_type"]),
                source_ref=row["source_ref"],
                session_id=row["session_id"],
                captured_at=_from_text(row["captured_at"]),
            ),
            trust=TrustLevel(row["trust"]),
            confidence=row["confidence"],
            valid_until=_opt_from_text(row["valid_until"]),
            entity_refs=tuple(EntityRef(entity_type=r[0], entity_id=UUID(r[1])) for r in refs),
            status=MemoryStatus(row["status"]),
            content_hash=row["content_hash"],
            supersedes=UUID(row["supersedes"]) if row["supersedes"] else None,
            created_at=_from_text(row["created_at"]),
            updated_at=_from_text(row["updated_at"]),
        )

    @staticmethod
    def _conflict(row: sqlite3.Row) -> MemoryConflict:
        return MemoryConflict(
            id=UUID(row["id"]),
            memory_a=UUID(row["memory_a"]),
            memory_b=UUID(row["memory_b"]),
            reason=row["reason"],
            status=ConflictStatus(row["status"]),
            created_at=_from_text(row["created_at"]),
            resolved_at=_opt_from_text(row["resolved_at"]),
            kept=UUID(row["kept"]) if row["kept"] else None,
        )

    def _fetch(self, conn: sqlite3.Connection, memory_id: UUID) -> MemoryRecord | None:
        row = conn.execute("SELECT * FROM memory_records WHERE id = ?", (str(memory_id),)).fetchone()
        return None if row is None else self._record(conn, row)

    # -- port --------------------------------------------------------------

    def status(self) -> BackendStatus:
        try:
            with self._open() as conn:
                conn.execute("SELECT 1 FROM memory_records LIMIT 1").fetchone()
                conn.execute("SELECT 1 FROM memory_fts LIMIT 1").fetchone()
        except (sqlite3.Error, OSError, ValueError) as exc:
            return BackendStatus(backend="sqlite", available=False, detail=f"{type(exc).__name__}: {exc}")
        return BackendStatus(backend="sqlite", available=True, detail="")

    def create(self, draft: MemoryDraft, status: MemoryStatus, supersedes: UUID | None = None) -> MemoryRecord:
        memory_id = uuid4()
        now = _to_text(_now())
        content = draft.content
        abstract = draft.abstract.strip() or content.strip()[:L0_MAX_CHARS]
        overview = draft.overview.strip() or content.strip()[:L1_MAX_CHARS]
        with self._open() as conn, _transaction(conn):
            conn.execute(
                "INSERT INTO memory_records (id, kind, category, subject, subject_norm, content, abstract,"
                " overview, source_type, source_ref, session_id, captured_at, trust, confidence, valid_until,"
                " status, content_hash, supersedes, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(memory_id), draft.kind.value, draft.category.value, draft.subject,
                    normalize_subject(draft.subject), content, abstract, overview,
                    draft.provenance.source_type.value, draft.provenance.source_ref,
                    draft.provenance.session_id, _to_text(draft.provenance.captured_at),
                    draft.trust.value, draft.confidence,
                    None if draft.valid_until is None else _to_text(draft.valid_until),
                    status.value, content_hash(content),
                    None if supersedes is None else str(supersedes), now, now,
                ),
            )
            conn.executemany(
                "INSERT INTO memory_entity_refs (memory_id, position, entity_type, entity_id) VALUES (?, ?, ?, ?)",
                [(str(memory_id), i, ref.entity_type, str(ref.entity_id)) for i, ref in enumerate(draft.entity_refs)],
            )
            record = self._fetch(conn, memory_id)
        assert record is not None
        return record

    def get(self, memory_id: UUID) -> MemoryRecord | None:
        with self._open() as conn:
            return self._fetch(conn, memory_id)

    def list(self, flt: MemoryFilter) -> tuple[list[MemoryRecord], int]:
        clauses: list[str] = []
        params: list[Any] = []
        for column, values in (
            ("status", flt.statuses), ("kind", flt.kinds), ("category", flt.categories),
        ):
            if values:
                clauses.append(f"{column} IN ({_marks(len(values))})")
                params.extend(v.value for v in values)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._open() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM memory_records{where}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM memory_records{where} ORDER BY created_at DESC, seq DESC LIMIT ? OFFSET ?",
                [*params, flt.limit, flt.offset],
            ).fetchall()
            return [self._record(conn, row) for row in rows], int(total)

    def search(self, query: MemoryQuery) -> list[MemoryHit]:
        match = _fts_query(query.text)
        if match is None:
            return []
        clauses = ["memory_fts MATCH ?", "r.status = 'approved'", "(r.valid_until IS NULL OR r.valid_until > ?)"]
        params: list[Any] = [match, _to_text(_now())]
        for column, values in (("kind", query.kinds), ("category", query.categories)):
            if values:
                clauses.append(f"r.{column} IN ({_marks(len(values))})")
                params.extend(v.value for v in values)
        sql = (
            "SELECT r.*, bm25(memory_fts) AS rank FROM memory_fts JOIN memory_records r ON r.seq = memory_fts.rowid"
            f" WHERE {' AND '.join(clauses)} ORDER BY rank LIMIT ?"
        )
        with self._open() as conn:
            rows = conn.execute(sql, [*params, query.limit]).fetchall()
        return [
            MemoryHit(
                id=UUID(r["id"]),
                kind=MemoryKind(r["kind"]),
                category=MemoryCategory(r["category"]),
                abstract=r["abstract"],
                score=-float(r["rank"]),  # bm25 is lower-is-better
                trust=TrustLevel(r["trust"]),
                provenance=Provenance(
                    source_type=SourceType(r["source_type"]),
                    source_ref=r["source_ref"],
                    session_id=r["session_id"],
                    captured_at=_from_text(r["captured_at"]),
                ),
                updated_at=_from_text(r["updated_at"]),
            )
            for r in rows
        ]

    def read(self, memory_id: UUID, level: DetailLevel) -> str | None:
        column = {DetailLevel.L0: "abstract", DetailLevel.L1: "overview", DetailLevel.L2: "content"}[level]
        with self._open() as conn:
            row = conn.execute(
                f"SELECT {column} FROM memory_records WHERE id = ? AND status = 'approved'"
                " AND (valid_until IS NULL OR valid_until > ?)",
                (str(memory_id), _to_text(_now())),
            ).fetchone()
        return None if row is None else str(row[0])

    def find_by_hash(self, content_hash: str) -> MemoryRecord | None:
        with self._open() as conn:
            row = conn.execute(
                "SELECT * FROM memory_records WHERE content_hash = ? ORDER BY"
                " CASE status WHEN 'approved' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END, created_at DESC LIMIT 1",
                (content_hash,),
            ).fetchone()
            return None if row is None else self._record(conn, row)

    def related(self, draft: MemoryDraft, limit: int = 20) -> list[MemoryRecord]:
        subject = normalize_subject(draft.subject)
        text = f"{draft.subject} {draft.abstract} {draft.content[:2000]}"
        terms = sorted({t.lower() for t in _TERM.findall(unicodedata.normalize("NFKC", text))}, key=len, reverse=True)
        match = _fts_query(" ".join(terms[:_MAX_QUERY_TERMS]))
        alternatives: list[str] = []
        params: list[Any] = []
        if subject:
            alternatives.append("subject_norm = ?")
            params.append(subject)
        if match is not None:
            alternatives.append("seq IN (SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?)")
            params.append(match)
        if not alternatives:
            return []
        sql = (
            "SELECT * FROM memory_records WHERE status IN ('pending', 'approved')"
            f" AND ({' OR '.join(alternatives)}) ORDER BY updated_at DESC, seq DESC LIMIT ?"
        )
        with self._open() as conn:
            rows = conn.execute(sql, [*params, limit]).fetchall()
            return [self._record(conn, row) for row in rows]

    def update(self, memory_id: UUID, patch: MemoryPatch, trust: TrustLevel | None = None) -> MemoryRecord | None:
        fields = patch.model_fields_set
        with self._open() as conn, _transaction(conn):
            current = self._fetch(conn, memory_id)
            if current is None:
                return None
            sets: dict[str, Any] = {}
            if patch.subject is not None:
                sets["subject"] = patch.subject
                sets["subject_norm"] = normalize_subject(patch.subject)
            if patch.kind is not None:
                sets["kind"] = patch.kind.value
            if patch.category is not None:
                sets["category"] = patch.category.value
            if "valid_until" in fields:
                sets["valid_until"] = None if patch.valid_until is None else _to_text(patch.valid_until)
            if patch.content is not None:
                sets["content"] = patch.content
                sets["content_hash"] = content_hash(patch.content)
                # A stale L0/L1 would describe the old text, so they follow the new content unless given.
                sets["abstract"] = patch.content.strip()[:L0_MAX_CHARS]
                sets["overview"] = patch.content.strip()[:L1_MAX_CHARS]
            if patch.abstract is not None:
                sets["abstract"] = patch.abstract.strip() or (patch.content or current.content).strip()[:L0_MAX_CHARS]
            if patch.overview is not None:
                sets["overview"] = patch.overview.strip() or (patch.content or current.content).strip()[:L1_MAX_CHARS]
            if trust is not None:
                sets["trust"] = trust.value
            if sets:
                sets["updated_at"] = _to_text(_now())
                assignments = ", ".join(f"{column} = ?" for column in sets)  # column names are literals above
                conn.execute(
                    f"UPDATE memory_records SET {assignments} WHERE id = ?", [*sets.values(), str(memory_id)]
                )
            return self._fetch(conn, memory_id)

    def set_status(self, memory_id: UUID, status: MemoryStatus) -> MemoryRecord | None:
        with self._open() as conn, _transaction(conn):
            cursor = conn.execute(
                "UPDATE memory_records SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, _to_text(_now()), str(memory_id)),
            )
            return self._fetch(conn, memory_id) if cursor.rowcount else None

    def delete(self, memory_id: UUID) -> ForgetReport | None:
        key = str(memory_id)
        with self._open() as conn, _transaction(conn):
            if conn.execute("SELECT 1 FROM memory_records WHERE id = ?", (key,)).fetchone() is None:
                return None
            conn.execute("DELETE FROM memory_conflicts WHERE memory_a = ? OR memory_b = ? OR kept = ?", (key, key, key))
            conn.execute("DELETE FROM memory_entity_refs WHERE memory_id = ?", (key,))
            conn.execute("UPDATE memory_records SET supersedes = NULL WHERE supersedes = ?", (key,))
            conn.execute("DELETE FROM memory_records WHERE id = ?", (key,))  # trigger clears memory_fts
        # Hermes keeps in its own sessions whatever it was sent (dossier N3).
        return ForgetReport(memory_id=memory_id, erased_from=("sqlite",), not_reached=("hermes_sessions",))

    def add_conflict(self, memory_a: UUID, memory_b: UUID, reason: str) -> MemoryConflict:
        conflict_id = uuid4()
        with self._open() as conn, _transaction(conn):
            conn.execute(
                "INSERT INTO memory_conflicts (id, memory_a, memory_b, reason, status, created_at)"
                " VALUES (?, ?, ?, ?, 'open', ?)",
                (str(conflict_id), str(memory_a), str(memory_b), reason[:256], _to_text(_now())),
            )
            row = conn.execute("SELECT * FROM memory_conflicts WHERE id = ?", (str(conflict_id),)).fetchone()
        return self._conflict(row)

    def list_conflicts(self, open_only: bool = True) -> list[MemoryConflict]:
        where = " WHERE status = 'open'" if open_only else ""
        with self._open() as conn:
            rows = conn.execute(f"SELECT * FROM memory_conflicts{where} ORDER BY created_at, id").fetchall()
        return [self._conflict(row) for row in rows]

    def resolve_conflict(self, conflict_id: UUID, kept: UUID | None) -> MemoryConflict | None:
        with self._open() as conn, _transaction(conn):
            row = conn.execute("SELECT * FROM memory_conflicts WHERE id = ?", (str(conflict_id),)).fetchone()
            if row is None:
                return None
            if kept is not None and str(kept) not in (row["memory_a"], row["memory_b"]):
                raise ValueError("kept must be one of the two conflicting memories")
            conn.execute(
                "UPDATE memory_conflicts SET status = 'resolved', resolved_at = ?, kept = ? WHERE id = ?",
                (_to_text(_now()), None if kept is None else str(kept), str(conflict_id)),
            )
            row = conn.execute("SELECT * FROM memory_conflicts WHERE id = ?", (str(conflict_id),)).fetchone()
        return self._conflict(row)


