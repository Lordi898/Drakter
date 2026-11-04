-- Proyectos, asignaturas y tareas. Subtarea = tarea con parent_task_id. "Bloqueada" se deriva de depends_on.
CREATE TABLE projects (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'project',
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'planned',
  priority TEXT NOT NULL DEFAULT 'medium',
  start_date TEXT,
  target_date TEXT,
  completed_at TEXT,
  manual_progress INTEGER,
  CONSTRAINT pk_projects PRIMARY KEY (id),
  CONSTRAINT ck_projects_type CHECK (entity_type = 'project'),
  CONSTRAINT ck_projects_name CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_projects_status CHECK (status IN ('planned','active','paused','completed','cancelled')),
  CONSTRAINT ck_projects_priority CHECK (priority IN ('low','medium','high','urgent')),
  CONSTRAINT ck_projects_completed CHECK ((status = 'completed') = (completed_at IS NOT NULL)),
  CONSTRAINT ck_projects_progress CHECK (manual_progress IS NULL OR manual_progress BETWEEN 0 AND 100),
  CONSTRAINT fk_projects_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT
);
CREATE INDEX ix_projects_status ON projects (status);
CREATE TRIGGER trg_projects_delete_entity AFTER DELETE ON projects BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

CREATE TABLE subjects (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'subject',
  name TEXT NOT NULL,
  description TEXT,
  teacher TEXT,
  color TEXT,
  CONSTRAINT pk_subjects PRIMARY KEY (id),
  CONSTRAINT ck_subjects_type CHECK (entity_type = 'subject'),
  CONSTRAINT ck_subjects_name CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_subjects_color CHECK (color IS NULL OR color GLOB '#[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]'),
  CONSTRAINT fk_subjects_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT
);
CREATE TRIGGER trg_subjects_delete_entity AFTER DELETE ON subjects BEGIN
  DELETE FROM entities WHERE id = old.id;
END;

CREATE TABLE tasks (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'task',
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  priority TEXT NOT NULL DEFAULT 'medium',
  start_at TEXT,
  due_at TEXT,
  due_date TEXT,
  completed_at TEXT,
  estimated_minutes INTEGER,
  parent_task_id TEXT,
  project_id TEXT,
  subject_id TEXT,
  position REAL NOT NULL DEFAULT 0,
  CONSTRAINT pk_tasks PRIMARY KEY (id),
  CONSTRAINT ck_tasks_type CHECK (entity_type = 'task'),
  CONSTRAINT ck_tasks_title CHECK (length(trim(title)) > 0),
  CONSTRAINT ck_tasks_status CHECK (status IN ('pending','in_progress','on_hold','completed','cancelled')),
  CONSTRAINT ck_tasks_priority CHECK (priority IN ('low','medium','high','urgent')),
  CONSTRAINT ck_tasks_completed CHECK ((status = 'completed') = (completed_at IS NOT NULL)),
  CONSTRAINT ck_tasks_due CHECK (NOT (due_at IS NOT NULL AND due_date IS NOT NULL)),
  CONSTRAINT ck_tasks_estimate CHECK (estimated_minutes IS NULL OR estimated_minutes >= 0),
  CONSTRAINT ck_tasks_parent CHECK (parent_task_id IS NULL OR parent_task_id <> id),
  CONSTRAINT fk_tasks_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_tasks_parent FOREIGN KEY (parent_task_id) REFERENCES tasks (id) ON DELETE RESTRICT,
  CONSTRAINT fk_tasks_project FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE RESTRICT,
  CONSTRAINT fk_tasks_subject FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);
CREATE INDEX ix_tasks_parent ON tasks (parent_task_id);
CREATE INDEX ix_tasks_project ON tasks (project_id);
CREATE INDEX ix_tasks_subject ON tasks (subject_id);
CREATE INDEX ix_tasks_status_due ON tasks (status, due_at);
CREATE TRIGGER trg_tasks_delete_entity AFTER DELETE ON tasks BEGIN
  DELETE FROM entities WHERE id = old.id;
END;
CREATE TRIGGER trg_tasks_no_cycle BEFORE UPDATE OF parent_task_id ON tasks
WHEN new.parent_task_id IS NOT NULL BEGIN
  SELECT raise(ABORT, 'task_hierarchy_cycle') WHERE EXISTS (
    WITH RECURSIVE up(id) AS (
      SELECT new.parent_task_id
      UNION
      SELECT t.parent_task_id FROM tasks t JOIN up ON t.id = up.id WHERE t.parent_task_id IS NOT NULL
    ) SELECT 1 FROM up WHERE id = new.id
  );
END;
