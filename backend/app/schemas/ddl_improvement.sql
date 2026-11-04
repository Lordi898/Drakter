-- Proposed DDL for the controlled improvement cycle. Unnumbered: the migrations
-- owner absorbs and numbers it. Every id is a UUID, every timestamp UTC ISO 8601.

CREATE TABLE improvement_feedback (
    id            TEXT PRIMARY KEY CHECK (length(id) = 36),
    origin        TEXT NOT NULL CHECK (origin IN ('user', 'agent', 'system')),
    author_id     TEXT NOT NULL CHECK (length(author_id) BETWEEN 1 AND 128),
    body          TEXT NOT NULL CHECK (length(body) BETWEEN 1 AND 8192),
    category      TEXT NOT NULL CHECK (category IN (
                      'communication_preference', 'context_adjustment', 'skill_fix',
                      'procedure_improvement', 'memory_retrieval', 'performance',
                      'interface', 'bug_fix')),
    severity      TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    classified_by TEXT NOT NULL CHECK (classified_by IN ('rules', 'default', 'user')),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX idx_improvement_feedback_created ON improvement_feedback (created_at);
CREATE INDEX idx_improvement_feedback_category ON improvement_feedback (category);
CREATE INDEX idx_improvement_feedback_severity ON improvement_feedback (severity);

CREATE TABLE improvement_proposals (
    id                    TEXT PRIMARY KEY CHECK (length(id) = 36),
    title                 TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    rationale             TEXT NOT NULL CHECK (length(rationale) <= 8192),
    category              TEXT CHECK (category IS NULL OR category IN (
                              'communication_preference', 'context_adjustment', 'skill_fix',
                              'procedure_improvement', 'memory_retrieval', 'performance',
                              'interface', 'bug_fix')),
    feedback_id           TEXT REFERENCES improvement_feedback (id) ON DELETE RESTRICT,
    author_kind           TEXT NOT NULL CHECK (author_kind IN ('user', 'agent', 'system')),
    author_id             TEXT NOT NULL CHECK (length(author_id) BETWEEN 1 AND 128),
    patch                 BLOB CHECK (
                              patch IS NULL
                              OR (typeof(patch) = 'blob' AND length(patch) BETWEEN 1 AND 1048576)),
    patch_sha256          TEXT CHECK (patch_sha256 IS NULL OR length(patch_sha256) = 64),
    status                TEXT NOT NULL CHECK (status IN (
                              'draft', 'evaluating', 'evaluated_passed', 'evaluated_failed',
                              'evaluation_blocked', 'approved', 'applied', 'reverted',
                              'rejected')),
    current_evaluation_id TEXT REFERENCES improvement_evaluations (id) ON DELETE RESTRICT,
    pending_evaluation_id TEXT,
    approved_digest       TEXT CHECK (approved_digest IS NULL OR length(approved_digest) = 64),
    approved_at           TEXT,
    applied_branch        TEXT,
    applied_commit        TEXT,
    applied_at            TEXT,
    reverted_at           TEXT,
    rejected_at           TEXT,
    rejection_reason      TEXT CHECK (rejection_reason IS NULL OR length(rejection_reason) <= 2000),
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    CHECK ((patch IS NULL) = (patch_sha256 IS NULL)),
    CHECK (status NOT IN ('approved', 'applied', 'reverted') OR approved_digest IS NOT NULL),
    CHECK (status NOT IN ('applied', 'reverted')
           OR (applied_branch IS NOT NULL AND applied_commit IS NOT NULL))
);

CREATE INDEX idx_improvement_proposals_status ON improvement_proposals (status);
CREATE INDEX idx_improvement_proposals_created ON improvement_proposals (created_at);
CREATE INDEX idx_improvement_proposals_feedback ON improvement_proposals (feedback_id);

-- The BEFORE INSERT guards also stop `INSERT OR REPLACE`, whose implicit delete
-- would otherwise skip the delete triggers.
CREATE TRIGGER improvement_proposals_insert_guard
BEFORE INSERT ON improvement_proposals
WHEN NEW.status <> 'draft'
  OR EXISTS (SELECT 1 FROM improvement_proposals WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'improvement proposal must start as a new draft');
END;

CREATE TRIGGER improvement_proposals_immutable
BEFORE UPDATE ON improvement_proposals
WHEN OLD.id IS NOT NEW.id
  OR OLD.title IS NOT NEW.title
  OR OLD.patch IS NOT NEW.patch
  OR OLD.patch_sha256 IS NOT NEW.patch_sha256
  OR OLD.author_kind IS NOT NEW.author_kind
BEGIN
    SELECT RAISE(ABORT, 'improvement proposal content is immutable');
END;

CREATE TRIGGER improvement_proposals_no_delete
BEFORE DELETE ON improvement_proposals
BEGIN
    SELECT RAISE(ABORT, 'improvement proposals cannot be deleted');
END;

CREATE TABLE improvement_evaluations (
    id              TEXT PRIMARY KEY CHECK (length(id) = 36),
    proposal_id     TEXT NOT NULL REFERENCES improvement_proposals (id) ON DELETE RESTRICT,
    status          TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'blocked')),
    base_commit     TEXT,
    patch_sha256    TEXT NOT NULL CHECK (length(patch_sha256) = 64),
    changed_paths   TEXT NOT NULL CHECK (json_valid(changed_paths)),
    protected_paths TEXT NOT NULL CHECK (json_valid(protected_paths)),
    checks          TEXT NOT NULL CHECK (json_valid(checks)),
    reason          TEXT,
    requested_by    TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_improvement_evaluations_proposal
    ON improvement_evaluations (proposal_id, created_at);

CREATE TRIGGER improvement_evaluations_insert_guard
BEFORE INSERT ON improvement_evaluations
WHEN EXISTS (SELECT 1 FROM improvement_evaluations WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'improvement evaluations are immutable');
END;

CREATE TRIGGER improvement_evaluations_no_update
BEFORE UPDATE ON improvement_evaluations
BEGIN
    SELECT RAISE(ABORT, 'improvement evaluations are immutable');
END;

CREATE TRIGGER improvement_evaluations_no_delete
BEFORE DELETE ON improvement_evaluations
BEGIN
    SELECT RAISE(ABORT, 'improvement evaluations are immutable');
END;

CREATE TABLE improvement_events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    id          TEXT NOT NULL UNIQUE CHECK (length(id) = 36),
    proposal_id TEXT REFERENCES improvement_proposals (id) ON DELETE RESTRICT,
    feedback_id TEXT REFERENCES improvement_feedback (id) ON DELETE RESTRICT,
    event_type  TEXT NOT NULL CHECK (event_type IN (
                    'feedback_recorded', 'feedback_reclassified', 'proposal_created',
                    'evaluation_started', 'evaluation_finished', 'approval_requested',
                    'approved', 'apply_failed', 'applied', 'revert_requested',
                    'revert_failed', 'reverted', 'rejected', 'invalidated_by_restore')),
    from_status TEXT,
    to_status   TEXT,
    actor_kind  TEXT NOT NULL CHECK (actor_kind IN ('user', 'agent', 'system')),
    actor_id    TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(detail)),
    created_at  TEXT NOT NULL,
    CHECK (proposal_id IS NOT NULL OR feedback_id IS NOT NULL)
);

CREATE INDEX idx_improvement_events_proposal ON improvement_events (proposal_id, seq);
CREATE INDEX idx_improvement_events_feedback ON improvement_events (feedback_id, seq);
CREATE INDEX idx_improvement_events_created ON improvement_events (created_at);

CREATE TRIGGER improvement_events_insert_guard
BEFORE INSERT ON improvement_events
WHEN EXISTS (SELECT 1 FROM improvement_events WHERE id = NEW.id OR seq = NEW.seq)
BEGIN
    SELECT RAISE(ABORT, 'improvement events are append-only');
END;

CREATE TRIGGER improvement_events_no_update
BEFORE UPDATE ON improvement_events
BEGIN
    SELECT RAISE(ABORT, 'improvement events are append-only');
END;

CREATE TRIGGER improvement_events_no_delete
BEFORE DELETE ON improvement_events
BEGIN
    SELECT RAISE(ABORT, 'improvement events are append-only');
END;
