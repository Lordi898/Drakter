-- Almacen. Nunca hay ruta absoluta libre: location_id + relative_path. Folder es organizacion, no tipo de recurso.
-- Nota y apunte son recursos note/study_note con note_body en BD.
-- agent_read: el agente solo lee una ubicacion con permiso explicito. root_dev/root_ino: identidad de la raiz, comprobada al abrir.
CREATE TABLE storage_locations (
  id TEXT NOT NULL,
  path TEXT NOT NULL,
  label TEXT NOT NULL,
  read_only INTEGER NOT NULL DEFAULT 1,
  enabled INTEGER NOT NULL DEFAULT 1,
  agent_read INTEGER NOT NULL DEFAULT 0,
  root_dev INTEGER,
  root_ino INTEGER,
  created_at TEXT NOT NULL,
  CONSTRAINT pk_storage_locations PRIMARY KEY (id),
  CONSTRAINT uq_storage_locations_path UNIQUE (path),
  CONSTRAINT ck_storage_locations_path CHECK (substr(path, 1, 1) = '/' OR path GLOB '[A-Za-z]:[\\/]*'),
  CONSTRAINT ck_storage_locations_read_only CHECK (read_only IN (0, 1)),
  CONSTRAINT ck_storage_locations_enabled CHECK (enabled IN (0, 1)),
  CONSTRAINT ck_storage_locations_agent_read CHECK (agent_read IN (0, 1))
);

CREATE TABLE folders (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'folder',
  name TEXT NOT NULL,
  parent_folder_id TEXT,
  location_id TEXT,
  relative_path TEXT,
  CONSTRAINT pk_folders PRIMARY KEY (id),
  CONSTRAINT ck_folders_type CHECK (entity_type = 'folder'),
  CONSTRAINT ck_folders_name CHECK (length(trim(name)) > 0),
  CONSTRAINT ck_folders_parent CHECK (parent_folder_id IS NULL OR parent_folder_id <> id),
  CONSTRAINT ck_folders_location CHECK ((location_id IS NULL) = (relative_path IS NULL)),
  CONSTRAINT fk_folders_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_folders_parent FOREIGN KEY (parent_folder_id) REFERENCES folders (id) ON DELETE RESTRICT,
  CONSTRAINT fk_folders_location FOREIGN KEY (location_id) REFERENCES storage_locations (id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX ux_folders_root_name ON folders (name) WHERE parent_folder_id IS NULL;
CREATE UNIQUE INDEX ux_folders_child_name ON folders (parent_folder_id, name) WHERE parent_folder_id IS NOT NULL;
CREATE TRIGGER trg_folders_delete_entity AFTER DELETE ON folders BEGIN
  DELETE FROM entities WHERE id = old.id;
END;
CREATE TRIGGER trg_folders_no_cycle BEFORE UPDATE OF parent_folder_id ON folders
WHEN new.parent_folder_id IS NOT NULL BEGIN
  SELECT raise(ABORT, 'folder_hierarchy_cycle') WHERE EXISTS (
    WITH RECURSIVE up(id) AS (
      SELECT new.parent_folder_id
      UNION
      SELECT f.parent_folder_id FROM folders f JOIN up ON f.id = up.id WHERE f.parent_folder_id IS NOT NULL
    ) SELECT 1 FROM up WHERE id = new.id
  );
END;

CREATE TABLE resources (
  id TEXT NOT NULL,
  entity_type TEXT NOT NULL DEFAULT 'resource',
  title TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  folder_id TEXT,
  location_id TEXT,
  relative_path TEXT,
  url TEXT,
  note_body TEXT,
  description TEXT,
  mime_type TEXT,
  size_bytes INTEGER,
  content_hash TEXT,
  source_modified_at TEXT,
  availability_status TEXT NOT NULL DEFAULT 'available',
  index_status TEXT NOT NULL DEFAULT 'none',
  indexed_at TEXT,
  index_error_code TEXT,
  CONSTRAINT pk_resources PRIMARY KEY (id),
  CONSTRAINT ck_resources_type CHECK (entity_type = 'resource'),
  CONSTRAINT ck_resources_title CHECK (length(trim(title)) > 0),
  CONSTRAINT ck_resources_resource_type CHECK (resource_type IN ('image','document','pdf','text','code','link','note','study_note','archive','other')),
  CONSTRAINT ck_resources_location CHECK ((location_id IS NULL) = (relative_path IS NULL)),
  CONSTRAINT ck_resources_relative_path CHECK (relative_path IS NULL OR (substr(relative_path, 1, 1) <> '/' AND '/' || relative_path || '/' NOT LIKE '%/../%')),
  CONSTRAINT ck_resources_link CHECK (resource_type <> 'link' OR url IS NOT NULL),
  CONSTRAINT ck_resources_url CHECK (url IS NULL OR url LIKE 'http://%' OR url LIKE 'https://%'),
  CONSTRAINT ck_resources_note CHECK (resource_type NOT IN ('note','study_note') OR note_body IS NOT NULL OR location_id IS NOT NULL),
  CONSTRAINT ck_resources_size CHECK (size_bytes IS NULL OR size_bytes >= 0),
  CONSTRAINT ck_resources_availability CHECK (availability_status IN ('available','missing','moved','unreachable','forbidden')),
  CONSTRAINT ck_resources_index CHECK (index_status IN ('none','pending','indexed','failed','skipped')),
  CONSTRAINT fk_resources_entity FOREIGN KEY (id, entity_type) REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
  CONSTRAINT fk_resources_folder FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE RESTRICT,
  CONSTRAINT fk_resources_location FOREIGN KEY (location_id) REFERENCES storage_locations (id) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX ux_resources_path ON resources (location_id, relative_path) WHERE location_id IS NOT NULL;
CREATE INDEX ix_resources_folder ON resources (folder_id);
CREATE INDEX ix_resources_type ON resources (resource_type);
CREATE INDEX ix_resources_hash ON resources (content_hash);
CREATE TRIGGER trg_resources_delete_entity AFTER DELETE ON resources BEGIN
  DELETE FROM entities WHERE id = old.id;
END;
