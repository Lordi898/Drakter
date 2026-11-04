-- Calendario. Verdad: hora de pared + zona IANA. *_utc son derivados para consultar rangos.
-- local_* = YYYY-MM-DDTHH:MM:SS. *_utc = instante de 24 caracteres con milisegundos: el orden de texto depende de ello. Dia completo: start_date y end_date_exclusive, sin UTC.
CREATE TABLE calendar_events (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'calendar_event',
  title TEXT NOT NULL,
  description TEXT,
  location TEXT,
  kind TEXT NOT NULL DEFAULT 'event',
  status TEXT NOT NULL DEFAULT 'confirmed',
  timezone TEXT NOT NULL,
  all_day INTEGER NOT NULL DEFAULT 0,
  local_start TEXT,
  local_end TEXT,
  start_date TEXT,
  end_date_exclusive TEXT,
  starts_at_utc TEXT,
  ends_at_utc TEXT,
  rrule TEXT,
  recurrence_until_utc TEXT,
  reminder_minutes_before INTEGER,
  CONSTRAINT pk_calendar_events PRIMARY KEY (id),
  CONSTRAINT ck_calendar_events_type CHECK (entity_type = 'calendar_event'),
  CONSTRAINT ck_calendar_events_title CHECK (length(trim(title)) > 0),
  CONSTRAINT ck_calendar_events_kind CHECK (kind IN ('event','reminder','work_session')),
  CONSTRAINT ck_calendar_events_status CHECK (status IN ('tentative','confirmed','cancelled')),
  CONSTRAINT ck_calendar_events_all_day CHECK (all_day IN (0, 1)),
  CONSTRAINT ck_calendar_events_reminder CHECK (reminder_minutes_before IS NULL OR reminder_minutes_before >= 0),
  CONSTRAINT ck_calendar_events_utc CHECK (
    (starts_at_utc IS NULL OR (length(starts_at_utc) = 24 AND starts_at_utc GLOB '*Z'))
    AND (ends_at_utc IS NULL OR (length(ends_at_utc) = 24 AND ends_at_utc GLOB '*Z'))
  ),
  CONSTRAINT ck_calendar_events_shape CHECK (
    (all_day = 1 AND start_date IS NOT NULL AND end_date_exclusive IS NOT NULL AND end_date_exclusive > start_date
      AND local_start IS NULL AND local_end IS NULL AND starts_at_utc IS NULL AND ends_at_utc IS NULL)
    OR
    (all_day = 0 AND local_start IS NOT NULL AND local_end IS NOT NULL AND start_date IS NULL AND end_date_exclusive IS NULL
      AND starts_at_utc IS NOT NULL AND ends_at_utc IS NOT NULL AND ends_at_utc > starts_at_utc)
  ),
  CONSTRAINT fk_calendar_events_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT
);
CREATE INDEX ix_calendar_events_range ON calendar_events (starts_at_utc, ends_at_utc);
CREATE INDEX ix_calendar_events_dates ON calendar_events (start_date, end_date_exclusive);
CREATE TRIGGER trg_calendar_events_delete_entity AFTER DELETE ON calendar_events BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

CREATE TABLE time_blocks (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'time_block',
  title TEXT NOT NULL,
  description TEXT,
  timezone TEXT NOT NULL,
  local_start TEXT NOT NULL,
  local_end TEXT NOT NULL,
  starts_at_utc TEXT NOT NULL,
  ends_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',
  task_id TEXT,
  CONSTRAINT pk_time_blocks PRIMARY KEY (id),
  CONSTRAINT ck_time_blocks_type CHECK (entity_type = 'time_block'),
  CONSTRAINT ck_time_blocks_title CHECK (length(trim(title)) > 0),
  CONSTRAINT ck_time_blocks_status CHECK (status IN ('planned','in_progress','done','skipped','cancelled')),
  CONSTRAINT ck_time_blocks_range CHECK (ends_at_utc > starts_at_utc),
  CONSTRAINT ck_time_blocks_utc CHECK (length(starts_at_utc) = 24 AND starts_at_utc GLOB '*Z' AND length(ends_at_utc) = 24 AND ends_at_utc GLOB '*Z'),
  CONSTRAINT fk_time_blocks_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_time_blocks_task FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE SET NULL
);
CREATE INDEX ix_time_blocks_task ON time_blocks (task_id);
CREATE INDEX ix_time_blocks_range ON time_blocks (starts_at_utc, ends_at_utc);
CREATE TRIGGER trg_time_blocks_delete_entity AFTER DELETE ON time_blocks BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

-- Sesiones de clase: datos estructurados, se expanden en lectura y nunca se materializan.
-- weekday: 1 = lunes ... 7 = domingo (ISO 8601).
CREATE TABLE class_sessions (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'class_session',
  subject_id TEXT NOT NULL,
  weekday INTEGER NOT NULL,
  starts_local_time TEXT NOT NULL,
  ends_local_time TEXT NOT NULL,
  timezone TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_until TEXT,
  interval_weeks INTEGER NOT NULL DEFAULT 1,
  room TEXT,
  CONSTRAINT pk_class_sessions PRIMARY KEY (id),
  CONSTRAINT ck_class_sessions_type CHECK (entity_type = 'class_session'),
  CONSTRAINT ck_class_sessions_weekday CHECK (weekday BETWEEN 1 AND 7),
  CONSTRAINT ck_class_sessions_times CHECK (
    starts_local_time GLOB '[0-2][0-9]:[0-5][0-9]' AND ends_local_time GLOB '[0-2][0-9]:[0-5][0-9]'
    AND ends_local_time > starts_local_time
  ),
  CONSTRAINT ck_class_sessions_dates CHECK (valid_until IS NULL OR valid_until >= valid_from),
  CONSTRAINT ck_class_sessions_interval CHECK (interval_weeks >= 1),
  CONSTRAINT fk_class_sessions_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_class_sessions_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);
CREATE INDEX ix_class_sessions_subject ON class_sessions (subject_id, weekday);
CREATE TRIGGER trg_class_sessions_delete_entity AFTER DELETE ON class_sessions BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

CREATE TABLE recurrence_exceptions (
  id TEXT NOT NULL,
  event_id TEXT,
  class_session_id TEXT,
  occurrence_local_start TEXT NOT NULL,
  kind TEXT NOT NULL,
  override_json TEXT,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_recurrence_exceptions PRIMARY KEY (id),
  CONSTRAINT ck_recurrence_exceptions_owner CHECK ((event_id IS NULL) <> (class_session_id IS NULL)),
  CONSTRAINT ck_recurrence_exceptions_kind CHECK (kind IN ('cancelled','modified')),
  CONSTRAINT ck_recurrence_exceptions_override CHECK (
    (kind = 'cancelled' AND override_json IS NULL) OR (kind = 'modified' AND override_json IS NOT NULL AND json_valid(override_json))
  ),
  CONSTRAINT fk_recurrence_exceptions_event FOREIGN KEY (event_id) REFERENCES calendar_events (id) ON DELETE CASCADE,
  CONSTRAINT fk_recurrence_exceptions_session FOREIGN KEY (class_session_id) REFERENCES class_sessions (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ux_recurrence_exceptions_event ON recurrence_exceptions (event_id, occurrence_local_start) WHERE event_id IS NOT NULL;
CREATE UNIQUE INDEX ux_recurrence_exceptions_session ON recurrence_exceptions (class_session_id, occurrence_local_start) WHERE class_session_id IS NOT NULL;
