-- Propuesta de tablas del frente de seguridad, sin numerar: la absorbe y numera
-- quien gobierna backend/migrations/. No añadir PRAGMA ni control de transacción.
-- Formatos: id = UUID en minúsculas con guiones; instantes = YYYY-MM-DDTHH:MM:SS.sssZ.
-- Los triggers protegen frente a errores del código, no frente a un proceso con
-- escritura directa en la base. Reconstruir estas tablas elimina sus triggers:
-- cualquier migración que lo haga debe recrearlos.

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY NOT NULL
        CHECK (length(id) = 36 AND id = lower(id)),
    actor_type TEXT NOT NULL
        CHECK (actor_type IN ('user', 'agent', 'automation', 'system')),
    principal TEXT NOT NULL
        CHECK (principal IN ('gui_approver', 'gui_renderer', 'agent', 'automation', 'system')),
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    result TEXT NOT NULL
        CHECK (result IN ('success', 'denied', 'failed', 'confirmation_required',
                          'approved', 'rejected', 'expired')),
    params_json TEXT,
    params_hash TEXT,
    error_code TEXT,
    confirmation_id TEXT,
    correlation_id TEXT NOT NULL,
    turn_id TEXT,
    tainted INTEGER NOT NULL DEFAULT 0 CHECK (tainted IN (0, 1)),
    created_at TEXT NOT NULL
        CHECK (created_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9][0-9]Z')
);

CREATE INDEX idx_audit_events_created_at ON audit_events (created_at);
CREATE INDEX idx_audit_events_confirmation ON audit_events (confirmation_id);

-- INSERT OR REPLACE borra sin disparar BEFORE DELETE: este trigger lo corta.
CREATE TRIGGER audit_events_no_replace BEFORE INSERT ON audit_events
WHEN EXISTS (SELECT 1 FROM audit_events WHERE id = NEW.id)
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only');
END;

CREATE TABLE pending_actions (
    id TEXT PRIMARY KEY NOT NULL
        CHECK (length(id) = 36 AND id = lower(id)),
    action TEXT NOT NULL,
    module TEXT NOT NULL,
    operation TEXT NOT NULL
        CHECK (operation IN ('read', 'create', 'update', 'delete', 'execute', 'admin')),
    risk TEXT NOT NULL
        CHECK (risk IN ('read', 'write', 'sensitive')),
    params_json TEXT NOT NULL,
    params_hash TEXT NOT NULL CHECK (length(params_hash) = 64),
    affected_count INTEGER NOT NULL CHECK (affected_count >= 0),
    requested_by TEXT NOT NULL
        CHECK (requested_by IN ('gui_approver', 'gui_renderer', 'agent', 'automation', 'system')),
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'executing', 'executed', 'rejected', 'expired', 'failed')),
    correlation_id TEXT NOT NULL,
    turn_id TEXT,
    tainted INTEGER NOT NULL DEFAULT 0 CHECK (tainted IN (0, 1)),
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    result_json TEXT,
    error_code TEXT
);

CREATE INDEX idx_pending_actions_status ON pending_actions (status, expires_at);

CREATE TRIGGER pending_actions_valid_insert BEFORE INSERT ON pending_actions
WHEN EXISTS (SELECT 1 FROM pending_actions WHERE id = NEW.id)
    OR NEW.status <> 'pending'
    OR NEW.resolved_at IS NOT NULL
    OR NEW.resolved_by IS NOT NULL
    OR NEW.result_json IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'pending_actions rows start pending and are never replaced');
END;

CREATE TRIGGER pending_actions_immutable BEFORE UPDATE ON pending_actions
WHEN NEW.id IS NOT OLD.id
    OR NEW.action IS NOT OLD.action
    OR NEW.module IS NOT OLD.module
    OR NEW.operation IS NOT OLD.operation
    OR NEW.risk IS NOT OLD.risk
    OR NEW.params_json IS NOT OLD.params_json
    OR NEW.params_hash IS NOT OLD.params_hash
    OR NEW.affected_count IS NOT OLD.affected_count
    OR NEW.requested_by IS NOT OLD.requested_by
    OR NEW.correlation_id IS NOT OLD.correlation_id
    OR NEW.turn_id IS NOT OLD.turn_id
    OR NEW.tainted IS NOT OLD.tainted
    OR NEW.created_at IS NOT OLD.created_at
    OR NEW.expires_at IS NOT OLD.expires_at
BEGIN
    SELECT RAISE(ABORT, 'pending_actions request columns are immutable');
END;

CREATE TRIGGER pending_actions_transitions BEFORE UPDATE OF status ON pending_actions
WHEN NOT (
    (OLD.status = 'pending' AND NEW.status IN ('executing', 'rejected', 'expired', 'failed'))
    OR (OLD.status = 'executing' AND NEW.status IN ('executed', 'failed'))
)
BEGIN
    SELECT RAISE(ABORT, 'illegal pending_actions status transition');
END;

CREATE TRIGGER pending_actions_no_delete BEFORE DELETE ON pending_actions
BEGIN
    SELECT RAISE(ABORT, 'pending_actions rows are never deleted');
END;
