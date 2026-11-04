-- Propuesta de tablas de habitos, calendario y asignaturas (sin numerar).
-- La absorbe y numera drakter-11. Parte de schema_v1 (auditoria C-09/C-12) y
-- depende de `entities`, `projects` y `tasks`, que no define este archivo.
-- Diferencias con schema_v1: habits.goal_project_id, habits.reminder_enabled y
-- time_blocks.task_id (relacion 1:N estructural = columna, regla C-11).

CREATE TABLE subjects(
  id TEXT PRIMARY KEY, entity_type TEXT NOT NULL DEFAULT 'subject' CHECK(entity_type='subject'),
  name TEXT NOT NULL CHECK(length(trim(name))>0), description TEXT, teacher TEXT,
  color TEXT CHECK(color IS NULL OR color GLOB '#[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]'),
  FOREIGN KEY(id,entity_type) REFERENCES entities(id,entity_type) ON DELETE RESTRICT);

CREATE TABLE habits(
  id TEXT PRIMARY KEY, entity_type TEXT NOT NULL DEFAULT 'habit' CHECK(entity_type='habit'),
  name TEXT NOT NULL CHECK(length(trim(name))>0), description TEXT, timezone TEXT NOT NULL,
  target_note TEXT, preferred_local_time TEXT,
  goal_project_id TEXT REFERENCES projects(id) ON DELETE RESTRICT,
  reminder_enabled INTEGER NOT NULL DEFAULT 0 CHECK(reminder_enabled IN(0,1)),
  status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','paused','ended')),
  start_date TEXT NOT NULL, end_date TEXT,
  CHECK(end_date IS NULL OR end_date>=start_date),
  FOREIGN KEY(id,entity_type) REFERENCES entities(id,entity_type) ON DELETE RESTRICT);
CREATE INDEX ix_habits_goal_project ON habits(goal_project_id);

-- Editar la frecuencia crea una version nueva: las rachas pasadas no se recalculan.
CREATE TABLE habit_schedule_versions(
  id TEXT PRIMARY KEY, habit_id TEXT NOT NULL REFERENCES habits(id) ON DELETE RESTRICT,
  rrule TEXT NOT NULL, valid_from TEXT NOT NULL, valid_until TEXT, created_at TEXT NOT NULL,
  CHECK(valid_until IS NULL OR valid_until>valid_from),
  UNIQUE(habit_id,valid_from));

CREATE TABLE habit_records(
  id TEXT PRIMARY KEY, habit_id TEXT NOT NULL REFERENCES habits(id) ON DELETE RESTRICT,
  occurrence_date TEXT NOT NULL CHECK(occurrence_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status TEXT NOT NULL CHECK(status IN('done','skipped','missed')), note TEXT, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(habit_id,occurrence_date));

CREATE TABLE calendar_events(
  id TEXT PRIMARY KEY, entity_type TEXT NOT NULL DEFAULT 'calendar_event' CHECK(entity_type='calendar_event'),
  title TEXT NOT NULL CHECK(length(trim(title))>0), description TEXT,
  kind TEXT NOT NULL DEFAULT 'event' CHECK(kind IN('event','reminder','work_session')),
  status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN('tentative','confirmed','cancelled')),
  timezone TEXT NOT NULL, all_day INTEGER NOT NULL DEFAULT 0 CHECK(all_day IN(0,1)),
  local_start TEXT, local_end TEXT, start_date TEXT, end_date_exclusive TEXT,
  starts_at_utc TEXT, ends_at_utc TEXT, rrule TEXT, recurrence_until_utc TEXT,
  CHECK((all_day=1 AND start_date IS NOT NULL AND end_date_exclusive IS NOT NULL AND end_date_exclusive>start_date AND local_start IS NULL AND local_end IS NULL AND starts_at_utc IS NULL)
     OR (all_day=0 AND local_start IS NOT NULL AND local_end IS NOT NULL AND start_date IS NULL AND end_date_exclusive IS NULL AND starts_at_utc IS NOT NULL AND ends_at_utc IS NOT NULL AND ends_at_utc>starts_at_utc)),
  FOREIGN KEY(id,entity_type) REFERENCES entities(id,entity_type) ON DELETE RESTRICT);
CREATE INDEX ix_events_range ON calendar_events(starts_at_utc,ends_at_utc);
CREATE INDEX ix_events_dates ON calendar_events(start_date,end_date_exclusive);

CREATE TABLE time_blocks(
  id TEXT PRIMARY KEY, entity_type TEXT NOT NULL DEFAULT 'time_block' CHECK(entity_type='time_block'),
  title TEXT NOT NULL CHECK(length(trim(title))>0), description TEXT, timezone TEXT NOT NULL,
  local_start TEXT NOT NULL, local_end TEXT NOT NULL, starts_at_utc TEXT NOT NULL, ends_at_utc TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN('planned','in_progress','done','skipped','cancelled')),
  task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  CHECK(ends_at_utc>starts_at_utc),
  FOREIGN KEY(id,entity_type) REFERENCES entities(id,entity_type) ON DELETE RESTRICT);
CREATE INDEX ix_blocks_range ON time_blocks(starts_at_utc,ends_at_utc);
CREATE INDEX ix_blocks_task ON time_blocks(task_id);

-- weekday: 1=lunes .. 7=domingo (ISO). Las clases se proyectan en la agenda, nunca se copian.
CREATE TABLE class_sessions(
  id TEXT PRIMARY KEY, entity_type TEXT NOT NULL DEFAULT 'class_session' CHECK(entity_type='class_session'),
  subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
  weekday INTEGER NOT NULL CHECK(weekday BETWEEN 1 AND 7), starts_local_time TEXT NOT NULL, ends_local_time TEXT NOT NULL,
  timezone TEXT NOT NULL, valid_from TEXT NOT NULL, valid_until TEXT, room TEXT,
  CHECK(ends_local_time>starts_local_time),
  CHECK(valid_until IS NULL OR valid_until>=valid_from),
  FOREIGN KEY(id,entity_type) REFERENCES entities(id,entity_type) ON DELETE RESTRICT);
CREATE INDEX ix_class_sessions_subject ON class_sessions(subject_id,weekday);

-- occurrence_local_start: 'AAAA-MM-DDTHH:MM:SS' o 'AAAA-MM-DD' en eventos de dia completo.
CREATE TABLE recurrence_exceptions(
  id TEXT PRIMARY KEY,
  event_id TEXT REFERENCES calendar_events(id) ON DELETE CASCADE,
  class_session_id TEXT REFERENCES class_sessions(id) ON DELETE CASCADE,
  occurrence_local_start TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN('cancelled','modified')),
  override_json TEXT CHECK(override_json IS NULL OR json_valid(override_json)), created_at TEXT NOT NULL,
  CHECK((event_id IS NULL)<>(class_session_id IS NULL)));
CREATE UNIQUE INDEX ux_recurrence_exceptions ON recurrence_exceptions(coalesce(event_id,class_session_id),occurrence_local_start);
