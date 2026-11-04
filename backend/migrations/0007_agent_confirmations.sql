-- Conversacion, turnos, mensajes, confirmaciones impuestas por el backend e idempotencia.
CREATE TABLE conversations (
  id TEXT NOT NULL,
  title TEXT,
  hermes_session_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  ended_at TEXT,
  CONSTRAINT pk_conversations PRIMARY KEY (id)
);

CREATE TABLE agent_turns (
  id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  status TEXT NOT NULL,
  input_source TEXT NOT NULL DEFAULT 'text',
  error_code TEXT,
  created_at TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  CONSTRAINT pk_agent_turns PRIMARY KEY (id),
  CONSTRAINT ck_agent_turns_status CHECK (status IN ('queued','running','completed','failed','cancelled','interrupted')),
  CONSTRAINT ck_agent_turns_source CHECK (input_source IN ('text','voice')),
  CONSTRAINT fk_agent_turns_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE RESTRICT
);
CREATE INDEX ix_agent_turns_conversation ON agent_turns (conversation_id, created_at);
-- Un solo turno activo por proceso: el dispatcher MCP atribuye cada llamada a ese turno.
CREATE UNIQUE INDEX ux_agent_turns_active ON agent_turns (status) WHERE status = 'running';

CREATE TABLE messages (
  id TEXT NOT NULL,
  conversation_id TEXT NOT NULL,
  turn_id TEXT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'complete',
  created_at TEXT NOT NULL,
  CONSTRAINT pk_messages PRIMARY KEY (id),
  CONSTRAINT ck_messages_role CHECK (role IN ('user','assistant','system')),
  CONSTRAINT ck_messages_status CHECK (status IN ('streaming','complete','cancelled','failed')),
  CONSTRAINT fk_messages_conversation FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE RESTRICT,
  CONSTRAINT fk_messages_turn FOREIGN KEY (turn_id) REFERENCES agent_turns (id) ON DELETE RESTRICT
);
CREATE INDEX ix_messages_conversation ON messages (conversation_id, created_at);

-- summary y affected_count los calcula el backend desde los argumentos, nunca el modelo.
-- targets_json guarda ids y revision resueltos: si difieren al aprobar, se responde conflict.
CREATE TABLE pending_confirmations (
  id TEXT NOT NULL,
  tool_name TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  origin TEXT NOT NULL,
  turn_id TEXT,
  correlation_id TEXT NOT NULL,
  args_json TEXT NOT NULL,
  args_hash TEXT NOT NULL,
  targets_json TEXT NOT NULL DEFAULT '[]',
  summary TEXT NOT NULL,
  affected_count INTEGER,
  risk TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  decided_at TEXT,
  decided_via TEXT,
  executed_at TEXT,
  result_json TEXT,
  error_code TEXT,
  CONSTRAINT pk_pending_confirmations PRIMARY KEY (id),
  CONSTRAINT ck_pc_actor CHECK (actor_type IN ('user','agent','automation','system')),
  CONSTRAINT ck_pc_origin CHECK (origin IN ('rest','mcp','scheduler','internal')),
  CONSTRAINT ck_pc_args CHECK (json_valid(args_json)),
  CONSTRAINT ck_pc_targets CHECK (json_valid(targets_json)),
  CONSTRAINT ck_pc_result CHECK (result_json IS NULL OR json_valid(result_json)),
  CONSTRAINT ck_pc_risk CHECK (risk IN ('write','sensitive')),
  CONSTRAINT ck_pc_status CHECK (status IN ('pending','approved','rejected','expired','executed','failed')),
  CONSTRAINT ck_pc_decided CHECK (
    (status IN ('pending','expired') AND decided_at IS NULL AND decided_via IS NULL)
    OR (status IN ('approved','rejected','executed','failed') AND decided_at IS NOT NULL AND decided_via = 'desktop')
  ),
  CONSTRAINT fk_pc_turn FOREIGN KEY (turn_id) REFERENCES agent_turns (id) ON DELETE SET NULL
);
CREATE INDEX ix_pc_status ON pending_confirmations (status, expires_at);
CREATE TRIGGER trg_pc_transition BEFORE UPDATE OF status ON pending_confirmations
WHEN NOT (
  new.status = old.status
  OR (old.status = 'pending' AND new.status IN ('approved','rejected','expired'))
  OR (old.status = 'approved' AND new.status IN ('executed','failed'))
) BEGIN
  SELECT raise(ABORT, 'confirmation_invalid_transition');
END;
CREATE TRIGGER trg_pc_immutable BEFORE UPDATE OF tool_name, actor_type, origin, correlation_id, args_json, args_hash, targets_json, summary, affected_count, risk, created_at, expires_at ON pending_confirmations
BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;
CREATE TRIGGER trg_pc_no_delete BEFORE DELETE ON pending_confirmations BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;

CREATE TABLE idempotency_records (
  scope TEXT NOT NULL,
  key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  status_code INTEGER NOT NULL,
  response_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  CONSTRAINT pk_idempotency_records PRIMARY KEY (scope, key),
  CONSTRAINT ck_idempotency_response CHECK (json_valid(response_json))
) WITHOUT ROWID;
CREATE INDEX ix_idempotency_expires ON idempotency_records (expires_at);
