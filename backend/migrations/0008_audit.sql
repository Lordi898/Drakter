-- Auditoria inmutable. entity_id sin FK para sobrevivir al borrado. params_redacted_json sale de la lista blanca de ToolSpec.audit.
-- Los triggers protegen frente a errores del codigo, no frente a un proceso con escritura directa en la BD.
CREATE TABLE audit_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  origin TEXT NOT NULL,
  action TEXT NOT NULL,
  tool_name TEXT,
  entity_type TEXT,
  entity_id TEXT,
  affected_count INTEGER,
  params_redacted_json TEXT,
  params_hash TEXT,
  changes_json TEXT,
  result TEXT NOT NULL,
  error_code TEXT,
  confirmation_id TEXT,
  duration_ms INTEGER,
  turn_id TEXT,
  tainted INTEGER NOT NULL DEFAULT 0,
  agent_provider TEXT,
  CONSTRAINT uq_audit_events_id UNIQUE (id),
  CONSTRAINT ck_audit_actor CHECK (actor_type IN ('user','agent','automation','system')),
  CONSTRAINT ck_audit_origin CHECK (origin IN ('rest','mcp','scheduler','internal')),
  CONSTRAINT ck_audit_result CHECK (result IN ('success','denied','failed','confirmation_required')),
  CONSTRAINT ck_audit_params CHECK (params_redacted_json IS NULL OR json_valid(params_redacted_json)),
  CONSTRAINT ck_audit_changes CHECK (changes_json IS NULL OR json_valid(changes_json)),
  CONSTRAINT ck_audit_tainted CHECK (tainted IN (0, 1)),
  CONSTRAINT ck_audit_occurred CHECK (length(occurred_at) = 24 AND occurred_at GLOB '*Z')
);
CREATE INDEX ix_audit_entity ON audit_events (entity_id, seq);
CREATE INDEX ix_audit_correlation ON audit_events (correlation_id);
CREATE INDEX ix_audit_occurred ON audit_events (occurred_at);
CREATE TRIGGER trg_audit_no_update BEFORE UPDATE ON audit_events BEGIN
  SELECT raise(ABORT, 'audit_immutable');
END;
CREATE TRIGGER trg_audit_no_delete BEFORE DELETE ON audit_events BEGIN
  SELECT raise(ABORT, 'audit_immutable');
END;
-- INSERT OR REPLACE sustituye filas sin disparar el trigger de borrado: se corta aqui.
CREATE TRIGGER trg_audit_no_replace BEFORE INSERT ON audit_events
WHEN EXISTS (SELECT 1 FROM audit_events WHERE id = new.id OR seq = new.seq) BEGIN
  SELECT raise(ABORT, 'audit_immutable');
END;
