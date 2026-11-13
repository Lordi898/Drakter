-- Automejora: sustituye las tablas improvement_* de 0010, que ningún código usa
-- y están vacías, por el esquema de app/services/improvement_*.py
-- (app/schemas/ddl_improvement.sql, absorbido aquí). DROP TABLE va con foreign_keys
-- desactivadas por el migrador; no es una reconstrucción: no se copia nada.

DROP TABLE IF EXISTS improvement_evaluations;
DROP TABLE IF EXISTS improvement_proposals;
DROP TABLE IF EXISTS improvement_feedback;

CREATE TABLE improvement_feedback (
    id            TEXT PRIMARY KEY CONSTRAINT ck_improvement_feedback_id CHECK (length(id) = 36),
    origin        TEXT NOT NULL CONSTRAINT ck_improvement_feedback_origin CHECK (origin IN ('user', 'agent', 'system')),
    author_id     TEXT NOT NULL CONSTRAINT ck_improvement_feedback_author_id CHECK (length(author_id) BETWEEN 1 AND 128),
    body          TEXT NOT NULL CONSTRAINT ck_improvement_feedback_body CHECK (length(body) BETWEEN 1 AND 8192),
    category      TEXT NOT NULL CONSTRAINT ck_improvement_feedback_category CHECK (category IN (
                      'communication_preference', 'context_adjustment', 'skill_fix',
                      'procedure_improvement', 'memory_retrieval', 'performance',
                      'interface', 'bug_fix')),
    severity      TEXT NOT NULL CONSTRAINT ck_improvement_feedback_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    classified_by TEXT NOT NULL CONSTRAINT ck_improvement_feedback_classified_by CHECK (classified_by IN ('rules', 'default', 'user')),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX idx_improvement_feedback_created ON improvement_feedback (created_at);
CREATE INDEX idx_improvement_feedback_category ON improvement_feedback (category);
CREATE INDEX idx_improvement_feedback_severity ON improvement_feedback (severity);

CREATE TABLE improvement_proposals (
    id                    TEXT PRIMARY KEY CONSTRAINT ck_improvement_proposals_id CHECK (length(id) = 36),
    title                 TEXT NOT NULL CONSTRAINT ck_improvement_proposals_title CHECK (length(title) BETWEEN 1 AND 200),
    rationale             TEXT NOT NULL CONSTRAINT ck_improvement_proposals_rationale CHECK (length(rationale) <= 8192),
    category              TEXT CONSTRAINT ck_improvement_proposals_category CHECK (category IS NULL OR category IN (
                              'communication_preference', 'context_adjustment', 'skill_fix',
                              'procedure_improvement', 'memory_retrieval', 'performance',
                              'interface', 'bug_fix')),
    feedback_id           TEXT CONSTRAINT fk_improvement_proposals_feedback_id REFERENCES improvement_feedback (id) ON DELETE RESTRICT,
    author_kind           TEXT NOT NULL CONSTRAINT ck_improvement_proposals_author_kind CHECK (author_kind IN ('user', 'agent', 'system')),
    author_id             TEXT NOT NULL CONSTRAINT ck_improvement_proposals_author_id CHECK (length(author_id) BETWEEN 1 AND 128),
    patch                 BLOB CONSTRAINT ck_improvement_proposals_patch CHECK (
                              patch IS NULL
                              OR (typeof(patch) = 'blob' AND length(patch) BETWEEN 1 AND 1048576)),
    patch_sha256          TEXT CONSTRAINT ck_improvement_proposals_patch_sha256 CHECK (patch_sha256 IS NULL OR length(patch_sha256) = 64),
    status                TEXT NOT NULL CONSTRAINT ck_improvement_proposals_status CHECK (status IN (
                              'draft', 'evaluating', 'evaluated_passed', 'evaluated_failed',
                              'evaluation_blocked', 'approved', 'applied', 'reverted',
                              'rejected')),
    current_evaluation_id TEXT CONSTRAINT fk_improvement_proposals_current_evaluation_id REFERENCES improvement_evaluations (id) ON DELETE RESTRICT,
    pending_evaluation_id TEXT,
    approved_digest       TEXT CONSTRAINT ck_improvement_proposals_approved_digest CHECK (approved_digest IS NULL OR length(approved_digest) = 64),
    approved_at           TEXT,
    applied_branch        TEXT,
    applied_commit        TEXT,
    applied_at            TEXT,
    reverted_at           TEXT,
    rejected_at           TEXT,
    rejection_reason      TEXT CONSTRAINT ck_improvement_proposals_rejection_reason CHECK (rejection_reason IS NULL OR length(rejection_reason) <= 2000),
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL,
    CONSTRAINT ck_improvement_proposals_patch_pair CHECK ((patch IS NULL) = (patch_sha256 IS NULL)),
    CONSTRAINT ck_improvement_proposals_approved_digest CHECK (status NOT IN ('approved', 'applied', 'reverted') OR approved_digest IS NOT NULL),
    CONSTRAINT ck_improvement_proposals_applied_fields CHECK (status NOT IN ('applied', 'reverted')
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
  OR OLD.author_id IS NOT NEW.author_id
  OR OLD.rationale IS NOT NEW.rationale
  OR OLD.feedback_id IS NOT NEW.feedback_id
  OR OLD.category IS NOT NEW.category
BEGIN
    SELECT RAISE(ABORT, 'improvement proposal content is immutable');
END;

-- The digest changes only when entering `approved` or when a restore drops it;
-- the applied_* columns only on approved -> applied.
CREATE TRIGGER improvement_proposals_approval_fields
BEFORE UPDATE ON improvement_proposals
WHEN (
        (OLD.approved_digest IS NOT NEW.approved_digest
         OR OLD.approved_at IS NOT NEW.approved_at)
        AND NOT (NEW.status = 'approved' AND OLD.status IN ('draft', 'evaluated_passed'))
        AND NOT (OLD.status = 'approved' AND NEW.status = 'evaluated_passed')
     )
  OR (
        (OLD.applied_branch IS NOT NEW.applied_branch
         OR OLD.applied_commit IS NOT NEW.applied_commit
         OR OLD.applied_at IS NOT NEW.applied_at)
        AND NOT (OLD.status = 'approved' AND NEW.status = 'applied')
     )
BEGIN
    SELECT RAISE(ABORT, 'improvement approval fields change only on their transition');
END;

-- evaluating -> draft and approved -> evaluated_passed exist only for restore and
-- recovery; the latter must drop the digest.
CREATE TRIGGER improvement_proposals_transitions
BEFORE UPDATE ON improvement_proposals
WHEN OLD.status <> NEW.status AND NOT (
       (OLD.status IN ('draft', 'evaluated_passed', 'evaluated_failed', 'evaluation_blocked')
        AND NEW.status = 'evaluating')
    OR (OLD.status = 'evaluating'
        AND NEW.status IN ('evaluated_passed', 'evaluated_failed', 'evaluation_blocked', 'draft'))
    OR (OLD.status = 'draft' AND NEW.status = 'approved' AND NEW.patch IS NULL)
    OR (OLD.status = 'evaluated_passed' AND NEW.status = 'approved'
        AND (NEW.patch IS NULL OR NEW.current_evaluation_id IS NOT NULL))
    OR (OLD.status = 'approved' AND NEW.status = 'applied' AND NEW.patch IS NOT NULL)
    OR (OLD.status = 'approved' AND NEW.status = 'evaluated_passed'
        AND NEW.approved_digest IS NULL)
    OR (OLD.status = 'applied' AND NEW.status = 'reverted')
    OR (OLD.status IN ('draft', 'evaluating', 'evaluated_passed', 'evaluated_failed',
                       'evaluation_blocked', 'approved')
        AND NEW.status = 'rejected')
)
BEGIN
    SELECT RAISE(ABORT, 'invalid improvement proposal transition');
END;

CREATE TRIGGER improvement_proposals_no_delete
BEFORE DELETE ON improvement_proposals
BEGIN
    SELECT RAISE(ABORT, 'improvement proposals cannot be deleted');
END;

CREATE TABLE improvement_evaluations (
    id              TEXT PRIMARY KEY CONSTRAINT ck_improvement_evaluations_id CHECK (length(id) = 36),
    proposal_id     TEXT NOT NULL CONSTRAINT fk_improvement_evaluations_proposal_id REFERENCES improvement_proposals (id) ON DELETE RESTRICT,
    status          TEXT NOT NULL CONSTRAINT ck_improvement_evaluations_status CHECK (status IN ('passed', 'failed', 'blocked')),
    base_commit     TEXT,
    patch_sha256    TEXT NOT NULL CONSTRAINT ck_improvement_evaluations_patch_sha256 CHECK (length(patch_sha256) = 64),
    changed_paths   TEXT NOT NULL CONSTRAINT ck_improvement_evaluations_changed_paths CHECK (json_valid(changed_paths)),
    protected_paths TEXT NOT NULL CONSTRAINT ck_improvement_evaluations_protected_paths CHECK (json_valid(protected_paths)),
    checks          TEXT NOT NULL CONSTRAINT ck_improvement_evaluations_checks CHECK (json_valid(checks)),
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
    id          TEXT NOT NULL CONSTRAINT uq_improvement_events_id UNIQUE CONSTRAINT ck_improvement_events_id CHECK (length(id) = 36),
    proposal_id TEXT CONSTRAINT fk_improvement_events_proposal_id REFERENCES improvement_proposals (id) ON DELETE RESTRICT,
    feedback_id TEXT CONSTRAINT fk_improvement_events_feedback_id REFERENCES improvement_feedback (id) ON DELETE RESTRICT,
    event_type  TEXT NOT NULL CONSTRAINT ck_improvement_events_event_type CHECK (event_type IN (
                    'feedback_recorded', 'feedback_reclassified', 'proposal_created',
                    'evaluation_started', 'evaluation_finished', 'approval_requested',
                    'approved', 'apply_failed', 'applied', 'revert_requested',
                    'revert_failed', 'reverted', 'rejected', 'invalidated_by_restore',
                    'recovered_after_interrupt')),
    from_status TEXT,
    to_status   TEXT,
    actor_kind  TEXT NOT NULL CONSTRAINT ck_improvement_events_actor_kind CHECK (actor_kind IN ('user', 'agent', 'system')),
    actor_id    TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '{}' CONSTRAINT ck_improvement_events_detail CHECK (json_valid(detail)),
    created_at  TEXT NOT NULL,
    CONSTRAINT ck_improvement_events_target CHECK (proposal_id IS NOT NULL OR feedback_id IS NOT NULL)
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
