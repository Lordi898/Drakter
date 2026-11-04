-- Memoria gestionada por Drakter (propuesta de drakter-18). Fechas en formato de instante; ids UUID.
-- memory_fts guarda copia propia del texto: borrar un registro borra sus tokens. Cuenta para copias y borrado.
CREATE TABLE memory_records (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT NOT NULL,
  kind TEXT NOT NULL,
  category TEXT NOT NULL,
  subject TEXT NOT NULL DEFAULT '',
  subject_norm TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL,
  abstract TEXT NOT NULL DEFAULT '',
  overview TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL,
  source_ref TEXT,
  session_id TEXT,
  captured_at TEXT NOT NULL,
  trust TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  valid_until TEXT,
  status TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  supersedes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CONSTRAINT uq_memory_records_id UNIQUE (id),
  CONSTRAINT ck_memory_records_kind CHECK (kind IN ('working','episodic','semantic','procedural')),
  CONSTRAINT ck_memory_records_category CHECK (category IN ('profile','preferences','entities','events','cases','patterns')),
  CONSTRAINT ck_memory_records_content CHECK (length(content) > 0),
  CONSTRAINT ck_memory_records_source CHECK (source_type IN ('user_gui','user_conversation','agent','tool_result','document','import')),
  CONSTRAINT ck_memory_records_trust CHECK (trust IN ('user_confirmed','user_stated','derived','third_party')),
  CONSTRAINT ck_memory_records_confidence CHECK (confidence >= 0.0 AND confidence <= 1.0),
  CONSTRAINT ck_memory_records_status CHECK (status IN ('pending','approved','rejected','superseded'))
);
CREATE INDEX ix_memory_records_status ON memory_records (status);
CREATE INDEX ix_memory_records_subject ON memory_records (subject_norm);
CREATE INDEX ix_memory_records_content_hash ON memory_records (content_hash);

CREATE TABLE memory_entity_refs (
  memory_id TEXT NOT NULL,
  position INTEGER NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  CONSTRAINT pk_memory_entity_refs PRIMARY KEY (memory_id, position),
  CONSTRAINT fk_memory_entity_refs_memory FOREIGN KEY (memory_id) REFERENCES memory_records (id) ON DELETE CASCADE
);
CREATE INDEX ix_memory_entity_refs_entity ON memory_entity_refs (entity_type, entity_id);

CREATE TABLE memory_conflicts (
  id TEXT NOT NULL,
  memory_a TEXT NOT NULL,
  memory_b TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  kept TEXT,
  CONSTRAINT pk_memory_conflicts PRIMARY KEY (id),
  CONSTRAINT ck_memory_conflicts_status CHECK (status IN ('open','resolved')),
  CONSTRAINT ck_memory_conflicts_pair CHECK (memory_a <> memory_b),
  CONSTRAINT fk_memory_conflicts_a FOREIGN KEY (memory_a) REFERENCES memory_records (id) ON DELETE CASCADE,
  CONSTRAINT fk_memory_conflicts_b FOREIGN KEY (memory_b) REFERENCES memory_records (id) ON DELETE CASCADE
);
CREATE INDEX ix_memory_conflicts_status ON memory_conflicts (status);
CREATE INDEX ix_memory_conflicts_a ON memory_conflicts (memory_a);
CREATE INDEX ix_memory_conflicts_b ON memory_conflicts (memory_b);

CREATE VIRTUAL TABLE memory_fts USING fts5 (
  subject, abstract, overview, content,
  tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TRIGGER trg_memory_records_ai AFTER INSERT ON memory_records BEGIN
  INSERT INTO memory_fts (rowid, subject, abstract, overview, content)
  VALUES (new.seq, new.subject, new.abstract, new.overview, new.content);
END;
CREATE TRIGGER trg_memory_records_au AFTER UPDATE OF subject, abstract, overview, content ON memory_records BEGIN
  DELETE FROM memory_fts WHERE rowid = old.seq;
  INSERT INTO memory_fts (rowid, subject, abstract, overview, content)
  VALUES (new.seq, new.subject, new.abstract, new.overview, new.content);
END;
CREATE TRIGGER trg_memory_records_ad AFTER DELETE ON memory_records BEGIN
  DELETE FROM memory_fts WHERE rowid = old.seq;
END;

CREATE TABLE improvement_feedback (
  id TEXT NOT NULL,
  source TEXT NOT NULL,
  category TEXT NOT NULL,
  summary TEXT NOT NULL,
  correlation_id TEXT,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_improvement_feedback PRIMARY KEY (id),
  CONSTRAINT ck_improvement_feedback_source CHECK (source IN ('user','agent','system')),
  CONSTRAINT ck_improvement_feedback_category CHECK (category IN ('communication','context','skill','procedure','memory','performance','interface','bug'))
);

CREATE TABLE improvement_proposals (
  id TEXT NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  summary TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft',
  feedback_id TEXT,
  document_path TEXT,
  git_ref TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  decided_at TEXT,
  decided_via TEXT,
  applied_at TEXT,
  CONSTRAINT pk_improvement_proposals PRIMARY KEY (id),
  CONSTRAINT ck_improvement_proposals_category CHECK (category IN ('communication','context','skill','procedure','memory','performance','interface','bug')),
  CONSTRAINT ck_improvement_proposals_status CHECK (status IN ('draft','evaluating','ready','approved','rejected','applied','failed')),
  CONSTRAINT ck_improvement_proposals_creator CHECK (created_by IN ('user','agent','system')),
  CONSTRAINT ck_improvement_proposals_decided CHECK (
    status NOT IN ('approved','rejected','applied') OR (decided_at IS NOT NULL AND decided_via IS 'desktop')
  ),
  CONSTRAINT fk_improvement_proposals_feedback FOREIGN KEY (feedback_id) REFERENCES improvement_feedback (id) ON DELETE SET NULL
);
CREATE INDEX ix_improvement_proposals_status ON improvement_proposals (status);

CREATE TABLE improvement_evaluations (
  id TEXT NOT NULL,
  proposal_id TEXT NOT NULL,
  environment TEXT NOT NULL,
  outcome TEXT NOT NULL,
  report_path TEXT,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_improvement_evaluations PRIMARY KEY (id),
  CONSTRAINT ck_improvement_evaluations_outcome CHECK (outcome IN ('passed','failed','inconclusive')),
  CONSTRAINT fk_improvement_evaluations_proposal FOREIGN KEY (proposal_id) REFERENCES improvement_proposals (id) ON DELETE RESTRICT
);
