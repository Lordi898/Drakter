-- Propuesta de tablas de relaciones, sin numerar. La absorbe y numera drakter-11.
-- Requiere de contracts: entities(id, entity_type, ..., UNIQUE(id, entity_type)).
--
-- Regla: lo 1:N estructural es columna (tasks.project_id, tasks.subject_id,
-- tasks.parent_task_id, folders.parent_folder_id, resources.folder_id,
-- class_sessions.subject_id) y se muestra como arista virtual. Aquí solo va lo
-- N:M semántico, por eso `parent_of` no tiene ninguna regla.

CREATE TABLE relationship_types (
    relationship_type TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    inverse_label TEXT NOT NULL,
    description TEXT NOT NULL,
    symmetric INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT ck_relationship_types_symmetric CHECK (symmetric IN (0, 1))
) WITHOUT ROWID;

CREATE TABLE relationship_rules (
    relationship_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    acyclic INTEGER NOT NULL DEFAULT 0,
    max_outgoing INTEGER,
    CONSTRAINT pk_relationship_rules PRIMARY KEY (relationship_type, source_type, target_type),
    CONSTRAINT ck_relationship_rules_acyclic CHECK (acyclic IN (0, 1)),
    CONSTRAINT ck_relationship_rules_max CHECK (max_outgoing IS NULL OR max_outgoing > 0),
    CONSTRAINT fk_relationship_rules_type FOREIGN KEY (relationship_type)
        REFERENCES relationship_types (relationship_type) ON DELETE RESTRICT
) WITHOUT ROWID;

CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT ck_relationships_not_self CHECK (source_id <> target_id),
    CONSTRAINT ck_relationships_metadata CHECK (json_valid(metadata_json)),
    CONSTRAINT uq_relationships_edge UNIQUE (source_id, target_id, relationship_type),
    CONSTRAINT fk_relationships_source FOREIGN KEY (source_id, source_type)
        REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
    CONSTRAINT fk_relationships_target FOREIGN KEY (target_id, target_type)
        REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
    CONSTRAINT fk_relationships_rule FOREIGN KEY (relationship_type, source_type, target_type)
        REFERENCES relationship_rules (relationship_type, source_type, target_type)
        ON DELETE RESTRICT
);

CREATE INDEX ix_relationships_source ON relationships (source_id, relationship_type);
CREATE INDEX ix_relationships_target ON relationships (target_id, relationship_type);

INSERT INTO relationship_types (relationship_type, label, inverse_label, description, symmetric) VALUES
    ('belongs_to', 'pertenece a', 'contiene', 'El origen forma parte del destino, sin ser una columna estructural.', 0),
    ('related_to', 'relacionado con', 'relacionado con', 'Vínculo general sin dirección. Se guarda una sola fila.', 1),
    ('scheduled_for', 'programado en', 'tiene programado', 'La tarea se trabaja en ese evento o bloque de tiempo.', 0),
    ('uses_resource', 'usa', 'usado por', 'El elemento necesita o consulta el recurso.', 0),
    ('depends_on', 'depende de', 'bloquea a', 'El origen no puede terminar antes que el destino. Sin ciclos.', 0),
    ('supports', 'apoya a', 'apoyado por', 'El origen ayuda a cumplir el destino, sin ser necesario.', 0),
    ('studies', 'estudia', 'estudiado en', 'El origen dedica tiempo de estudio a la asignatura.', 0),
    ('parent_of', 'es padre de', 'es hijo de', 'Jerarquía. Solo aparece como arista virtual de columnas.', 0),
    ('references', 'hace referencia a', 'referenciado por', 'El recurso cita o enlaza a otro.', 0),
    ('derived_from', 'derivado de', 'origen de', 'El recurso se obtuvo a partir de otro. Sin ciclos.', 0);

INSERT INTO relationship_rules (relationship_type, source_type, target_type, acyclic) VALUES
    ('belongs_to', 'resource', 'project', 0),
    ('belongs_to', 'resource', 'subject', 0),
    ('belongs_to', 'habit', 'project', 0),
    ('belongs_to', 'calendar_event', 'project', 0),
    ('belongs_to', 'calendar_event', 'subject', 0),
    ('belongs_to', 'time_block', 'project', 0),
    ('belongs_to', 'time_block', 'subject', 0),
    ('scheduled_for', 'task', 'calendar_event', 0),
    ('scheduled_for', 'task', 'time_block', 0),
    ('scheduled_for', 'task', 'class_session', 0),
    ('uses_resource', 'task', 'resource', 0),
    ('uses_resource', 'project', 'resource', 0),
    ('uses_resource', 'subject', 'resource', 0),
    ('uses_resource', 'calendar_event', 'resource', 0),
    ('uses_resource', 'class_session', 'resource', 0),
    ('depends_on', 'task', 'task', 1),
    ('depends_on', 'project', 'project', 1),
    ('supports', 'habit', 'project', 0),
    ('supports', 'habit', 'subject', 0),
    ('supports', 'resource', 'task', 0),
    ('supports', 'resource', 'project', 0),
    ('supports', 'task', 'project', 0),
    ('studies', 'task', 'subject', 0),
    ('studies', 'time_block', 'subject', 0),
    ('studies', 'calendar_event', 'subject', 0),
    ('studies', 'habit', 'subject', 0),
    ('references', 'resource', 'resource', 0),
    ('references', 'task', 'resource', 0),
    ('references', 'project', 'resource', 0),
    ('derived_from', 'resource', 'resource', 1);

-- `related_to` admite cualquier par. El servicio guarda source_id < target_id.
INSERT INTO relationship_rules (relationship_type, source_type, target_type, acyclic)
WITH kinds(name) AS (
    VALUES ('task'), ('project'), ('habit'), ('calendar_event'), ('time_block'),
           ('subject'), ('class_session'), ('resource'), ('folder')
)
SELECT 'related_to', a.name, b.name, 0 FROM kinds AS a CROSS JOIN kinds AS b;
