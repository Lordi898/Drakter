-- Relaciones polimorficas con integridad real. Regla: 1:N estructural = columna FK; N:M semantica = relationships.
-- Por eso no hay reglas parent_of tarea-tarea ni carpeta-carpeta, ni belongs_to tarea-proyecto.
CREATE TABLE relationship_types (
  relationship_type TEXT NOT NULL,
  description TEXT NOT NULL,
  symmetric INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT pk_relationship_types PRIMARY KEY (relationship_type),
  CONSTRAINT ck_relationship_types_symmetric CHECK (symmetric IN (0, 1))
) WITHOUT ROWID;

CREATE TABLE relationship_rules (
  relationship_type TEXT NOT NULL,
  source_type TEXT NOT NULL,
  target_type TEXT NOT NULL,
  acyclic INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT pk_relationship_rules PRIMARY KEY (relationship_type, source_type, target_type),
  CONSTRAINT ck_relationship_rules_acyclic CHECK (acyclic IN (0, 1)),
  CONSTRAINT fk_relationship_rules_type FOREIGN KEY (relationship_type) REFERENCES relationship_types (relationship_type) ON DELETE RESTRICT
) WITHOUT ROWID;

CREATE TABLE relationships (
  id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  CONSTRAINT pk_relationships PRIMARY KEY (id),
  CONSTRAINT uq_relationships UNIQUE (source_id, target_id, relationship_type),
  CONSTRAINT ck_relationships_self CHECK (source_id <> target_id),
  CONSTRAINT ck_relationships_metadata CHECK (json_valid(metadata_json)),
  CONSTRAINT fk_relationships_source FOREIGN KEY (source_id, source_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_relationships_target FOREIGN KEY (target_id, target_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_relationships_rule FOREIGN KEY (relationship_type, source_type, target_type)
    REFERENCES relationship_rules (relationship_type, source_type, target_type) ON DELETE RESTRICT
);
CREATE INDEX ix_relationships_target ON relationships (target_id, relationship_type);
CREATE INDEX ix_relationships_type ON relationships (relationship_type, source_type, target_type);
CREATE TRIGGER trg_relationships_no_cycle BEFORE INSERT ON relationships
WHEN EXISTS (
  SELECT 1 FROM relationship_rules r
  WHERE r.relationship_type = new.relationship_type AND r.source_type = new.source_type
    AND r.target_type = new.target_type AND r.acyclic = 1
) BEGIN
  SELECT raise(ABORT, 'relationship_cycle') WHERE EXISTS (
    WITH RECURSIVE down(id) AS (
      SELECT new.target_id
      UNION
      SELECT rel.target_id FROM relationships rel JOIN down ON rel.source_id = down.id
      WHERE rel.relationship_type = new.relationship_type
    ) SELECT 1 FROM down WHERE id = new.source_id
  );
END;

INSERT INTO relationship_types (relationship_type, description, symmetric) VALUES
  ('belongs_to', 'El origen forma parte del destino cuando no hay columna estructural.', 0),
  ('related_to', 'Vinculo generico sin direccion; se guarda con source_id < target_id.', 1),
  ('scheduled_for', 'El origen se realiza en el bloque o evento destino.', 0),
  ('uses_resource', 'El origen usa el recurso destino.', 0),
  ('depends_on', 'El origen no puede terminar hasta que termine el destino. Aciclica.', 0),
  ('supports', 'El origen ayuda a cumplir el destino.', 0),
  ('studies', 'El origen se dedica a estudiar la asignatura destino.', 0),
  ('parent_of', 'Jerarquia semantica entre proyectos. Tareas y carpetas usan su columna.', 0),
  ('references', 'El origen cita al destino.', 0),
  ('derived_from', 'El origen se creo a partir del destino. Aciclica entre recursos.', 0);

INSERT INTO relationship_rules (relationship_type, source_type, target_type, acyclic) VALUES
  ('belongs_to','resource','project',0),('belongs_to','resource','subject',0),
  ('belongs_to','habit','project',0),('belongs_to','calendar_event','project',0),
  ('belongs_to','calendar_event','subject',0),('belongs_to','time_block','project',0),
  ('belongs_to','project','subject',0),
  ('scheduled_for','task','time_block',0),('scheduled_for','task','calendar_event',0),
  ('scheduled_for','project','time_block',0),('scheduled_for','subject','time_block',0),
  ('scheduled_for','habit','time_block',0),
  ('uses_resource','task','resource',0),('uses_resource','project','resource',0),
  ('uses_resource','subject','resource',0),('uses_resource','calendar_event','resource',0),
  ('uses_resource','class_session','resource',0),('uses_resource','habit','resource',0),
  ('depends_on','task','task',1),('depends_on','project','project',1),
  ('supports','habit','project',0),('supports','habit','subject',0),
  ('supports','resource','task',0),('supports','resource','project',0),
  ('supports','time_block','project',0),('supports','task','habit',0),
  ('studies','resource','subject',0),('studies','time_block','subject',0),
  ('studies','calendar_event','subject',0),('studies','habit','subject',0),
  ('parent_of','project','project',1),
  ('references','resource','resource',0),('references','resource','task',0),
  ('references','resource','project',0),('references','resource','subject',0),
  ('references','task','task',0),
  ('derived_from','resource','resource',1),('derived_from','task','resource',0),
  ('derived_from','task','calendar_event',0),('derived_from','project','resource',0),
  ('derived_from','calendar_event','task',0);

WITH t(x) AS (VALUES ('task'),('project'),('habit'),('calendar_event'),('time_block'),('subject'),('class_session'),('resource'),('folder'))
INSERT INTO relationship_rules (relationship_type, source_type, target_type, acyclic)
SELECT 'related_to', a.x, b.x, 0 FROM t a CROSS JOIN t b;

-- Etiqueta legible de cualquier entidad y consulta de consistencia al arrancar (entidad sin fila de dominio).
CREATE VIEW v_entity_labels AS
  SELECT id, 'task' AS entity_type, title AS label FROM tasks
  UNION ALL SELECT id, 'project', name FROM projects
  UNION ALL SELECT id, 'habit', name FROM habits
  UNION ALL SELECT id, 'calendar_event', title FROM calendar_events
  UNION ALL SELECT id, 'time_block', title FROM time_blocks
  UNION ALL SELECT c.id, 'class_session', s.name FROM class_sessions c JOIN subjects s ON s.id = c.subject_id
  UNION ALL SELECT id, 'subject', name FROM subjects
  UNION ALL SELECT id, 'resource', title FROM resources
  UNION ALL SELECT id, 'folder', name FROM folders;
CREATE VIEW v_orphan_entities AS
  SELECT e.id, e.entity_type FROM entities e
  LEFT JOIN v_entity_labels l ON l.id = e.id
  WHERE l.id IS NULL;
