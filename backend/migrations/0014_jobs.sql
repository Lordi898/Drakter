-- Drakter Jobs (voz v2, V-24 a V-27): trabajos largos en un carril Hermes aparte.
-- Sin estado `waiting_confirmation`: lo pendiente de confirmar se cuenta en `pending_actions`.
-- No hay migración inversa: «revertir» es restaurar la copia previa del migrador.

CREATE TABLE jobs (
    id                TEXT PRIMARY KEY CONSTRAINT ck_jobs_id CHECK (length(id) = 36),
    parent_session_id TEXT CONSTRAINT ck_jobs_parent_session_id CHECK (parent_session_id IS NULL OR length(parent_session_id) = 36),
    session_id        TEXT NOT NULL CONSTRAINT ck_jobs_session_id CHECK (length(session_id) = 36),
    lane              TEXT NOT NULL CONSTRAINT ck_jobs_lane CHECK (length(lane) BETWEEN 1 AND 32),
    title             TEXT NOT NULL CONSTRAINT ck_jobs_title CHECK (length(title) BETWEEN 1 AND 80),
    brief             TEXT NOT NULL CONSTRAINT ck_jobs_brief CHECK (length(brief) BETWEEN 1 AND 4000),
    state             TEXT NOT NULL CONSTRAINT ck_jobs_state CHECK (state IN ('running', 'completed', 'failed', 'cancelled')),
    reason            TEXT CONSTRAINT ck_jobs_reason CHECK (reason IS NULL OR length(reason) <= 200),
    summary           TEXT CONSTRAINT ck_jobs_summary CHECK (summary IS NULL OR length(summary) <= 8000),
    tainted           INTEGER NOT NULL DEFAULT 0 CONSTRAINT ck_jobs_tainted CHECK (tainted IN (0, 1)),
    tool_calls        INTEGER NOT NULL DEFAULT 0 CONSTRAINT ck_jobs_tool_calls CHECK (tool_calls >= 0),
    last_tool         TEXT CONSTRAINT ck_jobs_last_tool CHECK (last_tool IS NULL OR length(last_tool) <= 64),
    pending_actions   INTEGER NOT NULL DEFAULT 0 CONSTRAINT ck_jobs_pending_actions CHECK (pending_actions >= 0),
    created_at        TEXT NOT NULL,
    started_at        TEXT,
    finished_at       TEXT,
    CONSTRAINT ck_jobs_finished CHECK ((state = 'running') = (finished_at IS NULL))
);

CREATE INDEX idx_jobs_created ON jobs (created_at);
CREATE INDEX idx_jobs_state ON jobs (state);
