-- Memory store (proposal, unnumbered). Absorbed and numbered by the contracts front.
-- Dates are ISO 8601 UTC text in a fixed format, so they compare as text.
-- Ids are UUID text. No foreign keys to tables outside memory_.

CREATE TABLE memory_records (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('working', 'episodic', 'semantic', 'procedural')),
    category TEXT NOT NULL CHECK (category IN ('profile', 'preferences', 'entities', 'events', 'cases', 'patterns')),
    subject TEXT NOT NULL DEFAULT '',
    subject_norm TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL CHECK (length(content) > 0),
    abstract TEXT NOT NULL DEFAULT '',
    overview TEXT NOT NULL DEFAULT '',
    source_type TEXT NOT NULL CHECK (source_type IN ('user_gui', 'user_conversation', 'agent', 'tool_result', 'document', 'import')),
    source_ref TEXT,
    session_id TEXT,
    captured_at TEXT NOT NULL,
    trust TEXT NOT NULL CHECK (trust IN ('user_confirmed', 'user_stated', 'derived', 'third_party')),
    confidence REAL NOT NULL DEFAULT 0.5 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    valid_until TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'superseded')),
    content_hash TEXT NOT NULL,
    supersedes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX idx_memory_records_status ON memory_records (status);
CREATE INDEX idx_memory_records_subject ON memory_records (subject_norm);
CREATE INDEX idx_memory_records_content_hash ON memory_records (content_hash);

CREATE TABLE memory_entity_refs (
    memory_id TEXT NOT NULL REFERENCES memory_records (id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY (memory_id, position)
);

CREATE INDEX idx_memory_entity_refs_entity ON memory_entity_refs (entity_type, entity_id);

CREATE TABLE memory_conflicts (
    id TEXT PRIMARY KEY,
    memory_a TEXT NOT NULL REFERENCES memory_records (id) ON DELETE CASCADE,
    memory_b TEXT NOT NULL REFERENCES memory_records (id) ON DELETE CASCADE,
    reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('open', 'resolved')),
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    kept TEXT,
    CHECK (memory_a <> memory_b)
);

CREATE INDEX idx_memory_conflicts_status ON memory_conflicts (status);
CREATE INDEX idx_memory_conflicts_a ON memory_conflicts (memory_a);
CREATE INDEX idx_memory_conflicts_b ON memory_conflicts (memory_b);

-- Standalone index (own copy of the text, keyed by memory_records.seq).
-- Deleting a record deletes its tokens and text from the index.
CREATE VIRTUAL TABLE memory_fts USING fts5 (
    subject,
    abstract,
    overview,
    content,
    tokenize = 'unicode61 remove_diacritics 2'
);

CREATE TRIGGER memory_records_ai AFTER INSERT ON memory_records BEGIN
    INSERT INTO memory_fts (rowid, subject, abstract, overview, content)
    VALUES (new.seq, new.subject, new.abstract, new.overview, new.content);
END;

CREATE TRIGGER memory_records_au AFTER UPDATE OF subject, abstract, overview, content ON memory_records BEGIN
    DELETE FROM memory_fts WHERE rowid = old.seq;
    INSERT INTO memory_fts (rowid, subject, abstract, overview, content)
    VALUES (new.seq, new.subject, new.abstract, new.overview, new.content);
END;

CREATE TRIGGER memory_records_ad AFTER DELETE ON memory_records BEGIN
    DELETE FROM memory_fts WHERE rowid = old.seq;
END;
