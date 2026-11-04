-- Registro de memoria (metadatos y procedencia; el contenido vive en OpenViking o Hermes) y automejora.
-- review_text solo existe mientras un candidato espera revision y se vacia al decidir o borrar.
CREATE TABLE memory_items (
  id TEXT NOT NULL,
  provider TEXT NOT NULL,
  external_uri TEXT,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'candidate',
  provenance_type TEXT NOT NULL,
  provenance_ref TEXT,
  confidence REAL,
  review_text TEXT,
  supersedes_id TEXT,
  conversation_id TEXT,
  expires_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT,
  CONSTRAINT pk_memory_items PRIMARY KEY (id),
  CONSTRAINT uq_memory_items_uri UNIQUE (provider, external_uri),
  CONSTRAINT ck_memory_provider CHECK (provider IN ('openviking','hermes_native')),
  CONSTRAINT ck_memory_kind CHECK (kind IN ('episodic','semantic','procedural')),
  CONSTRAINT ck_memory_status CHECK (status IN ('candidate','active','superseded','rejected','deleted')),
  CONSTRAINT ck_memory_provenance CHECK (provenance_type IN ('conversation','document','tool_result','user_correction','system')),
  CONSTRAINT ck_memory_confidence CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
  CONSTRAINT ck_memory_review CHECK (status = 'candidate' OR review_text IS NULL),
  CONSTRAINT ck_memory_deleted CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
  CONSTRAINT fk_memory_supersedes FOREIGN KEY (supersedes_id) REFERENCES memory_items (id) ON DELETE SET NULL,
  CONSTRAINT fk_memory_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE SET NULL
);
CREATE INDEX ix_memory_items_status ON memory_items (status, kind);

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
    status NOT IN ('approved','rejected','applied') OR (decided_at IS NOT NULL AND decided_via = 'desktop')
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
