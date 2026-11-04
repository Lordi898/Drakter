-- Supertipo de entidades del Workspace, etiquetas, referencias externas, ajustes y notificaciones.
-- Reglas: contracts/README.md. Instantes: YYYY-MM-DDTHH:MM:SS.sssZ. UUID: TEXT(36) en minusculas.
CREATE TABLE entities (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  archived_at TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  CONSTRAINT pk_entities PRIMARY KEY (id),
  CONSTRAINT uq_entities_id_type UNIQUE (id, entity_type),
  CONSTRAINT ck_entities_id CHECK (length(id) = 36 AND id = lower(id)),
  CONSTRAINT ck_entities_type CHECK (entity_type IN ('task','project','habit','calendar_event','time_block','subject','class_session','resource','folder')),
  CONSTRAINT ck_entities_created_at CHECK (length(created_at) = 24 AND created_at GLOB '*Z'),
  CONSTRAINT ck_entities_updated_at CHECK (length(updated_at) = 24 AND updated_at GLOB '*Z'),
  CONSTRAINT ck_entities_archived_at CHECK (archived_at IS NULL OR (length(archived_at) = 24 AND archived_at GLOB '*Z')),
  CONSTRAINT ck_entities_revision CHECK (revision >= 1),
  CONSTRAINT ck_entities_metadata CHECK (json_valid(metadata_json))
);
CREATE INDEX ix_entities_type_archived ON entities (entity_type, archived_at);

CREATE TABLE tags (
  id TEXT NOT NULL,
  name TEXT NOT NULL,
  name_normalized TEXT NOT NULL,
  color TEXT,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_tags PRIMARY KEY (id),
  CONSTRAINT uq_tags_name UNIQUE (name_normalized),
  CONSTRAINT ck_tags_name CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_tags_color CHECK (color IS NULL OR color GLOB '#[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]')
);

CREATE TABLE entity_tags (
  entity_id TEXT NOT NULL,
  tag_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_entity_tags PRIMARY KEY (entity_id, tag_id),
  CONSTRAINT fk_entity_tags_entity FOREIGN KEY (entity_id) REFERENCES entities (id) ON DELETE CASCADE,
  CONSTRAINT fk_entity_tags_tag FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE RESTRICT
) WITHOUT ROWID;
CREATE INDEX ix_entity_tags_tag ON entity_tags (tag_id);

CREATE TABLE external_refs (
  id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  provider TEXT NOT NULL,
  external_type TEXT NOT NULL,
  external_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_external_refs PRIMARY KEY (id),
  CONSTRAINT uq_external_refs UNIQUE (provider, external_type, external_id),
  CONSTRAINT fk_external_refs_entity FOREIGN KEY (entity_id) REFERENCES entities (id) ON DELETE CASCADE
);
CREATE INDEX ix_external_refs_entity ON external_refs (entity_id);

-- Nunca secretos ni claves API: value_json lo escribe solo el backend tras validar por lista blanca.
CREATE TABLE settings (
  key TEXT NOT NULL,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  updated_by TEXT NOT NULL,
  CONSTRAINT pk_settings PRIMARY KEY (key),
  CONSTRAINT ck_settings_value CHECK (json_valid(value_json)),
  CONSTRAINT ck_settings_updated_by CHECK (updated_by IN ('user','agent','automation','system'))
) WITHOUT ROWID;

CREATE TABLE notifications (
  id TEXT NOT NULL,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  severity TEXT NOT NULL DEFAULT 'info',
  entity_id TEXT,
  created_at TEXT NOT NULL,
  read_at TEXT,
  CONSTRAINT pk_notifications PRIMARY KEY (id),
  CONSTRAINT ck_notifications_severity CHECK (severity IN ('info','success','warning','error')),
  CONSTRAINT fk_notifications_entity FOREIGN KEY (entity_id) REFERENCES entities (id) ON DELETE SET NULL
);
CREATE INDEX ix_notifications_unread ON notifications (read_at, created_at);
