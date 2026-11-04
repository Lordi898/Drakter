-- Habitos. Editar la frecuencia crea una version nueva: las rachas pasadas no se recalculan.
CREATE TABLE habits (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'habit',
  name TEXT NOT NULL,
  description TEXT,
  timezone TEXT NOT NULL,
  target_note TEXT,
  preferred_local_time TEXT,
  goal_project_id TEXT,
  reminder_enabled INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'active',
  start_date TEXT NOT NULL,
  end_date TEXT,
  CONSTRAINT pk_habits PRIMARY KEY (id),
  CONSTRAINT ck_habits_type CHECK (entity_type = 'habit'),
  CONSTRAINT ck_habits_name CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_habits_status CHECK (status IN ('active','paused','ended')),
  CONSTRAINT ck_habits_time CHECK (preferred_local_time IS NULL OR preferred_local_time GLOB '[0-2][0-9]:[0-5][0-9]'),
  CONSTRAINT ck_habits_reminder CHECK (reminder_enabled IN (0, 1)),
  CONSTRAINT ck_habits_dates CHECK (end_date IS NULL OR end_date >= start_date),
  CONSTRAINT fk_habits_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_habits_goal_project FOREIGN KEY (goal_project_id) REFERENCES projects (id) ON DELETE RESTRICT
);
CREATE INDEX ix_habits_goal_project ON habits (goal_project_id);
CREATE TRIGGER trg_habits_delete_entity AFTER DELETE ON habits BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

CREATE TABLE habit_schedule_versions (
  id TEXT NOT NULL,
  habit_id TEXT NOT NULL,
  rrule TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_until TEXT,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_habit_schedule_versions PRIMARY KEY (id),
  CONSTRAINT uq_habit_schedule_from UNIQUE (habit_id, valid_from),
  CONSTRAINT ck_habit_schedule_dates CHECK (valid_until IS NULL OR valid_until > valid_from),
  CONSTRAINT fk_habit_schedule_habit FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE RESTRICT
);

CREATE TABLE habit_records (
  id TEXT NOT NULL,
  habit_id TEXT NOT NULL,
  occurrence_date TEXT NOT NULL,
  status TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CONSTRAINT pk_habit_records PRIMARY KEY (id),
  CONSTRAINT uq_habit_records_occurrence UNIQUE (habit_id, occurrence_date),
  CONSTRAINT ck_habit_records_date CHECK (occurrence_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  CONSTRAINT ck_habit_records_status CHECK (status IN ('done','skipped','missed')),
  CONSTRAINT fk_habit_records_habit FOREIGN KEY (habit_id) REFERENCES habits (id) ON DELETE RESTRICT
);
