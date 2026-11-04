-- Propuesta de tablas del almacén, sin numerar. La absorbe y numera drakter-11.
-- Requiere de contracts: entities(id, entity_type, created_at, updated_at,
-- archived_at, revision, metadata_json, UNIQUE(id, entity_type)), tags y entity_tags.
-- Si contracts fija search_documents/search_fts para todo el Workspace, esa parte
-- de este archivo se descarta y el código sigue valiendo: usa esos mismos nombres.

CREATE TABLE storage_locations (
    id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    label TEXT NOT NULL,
    read_only INTEGER NOT NULL DEFAULT 1,
    agent_read INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    root_dev INTEGER,
    root_ino INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT uq_storage_locations_path UNIQUE (path),
    CONSTRAINT ck_storage_locations_path_absolute CHECK (substr(path, 1, 1) = '/'),
    CONSTRAINT ck_storage_locations_read_only CHECK (read_only IN (0, 1)),
    CONSTRAINT ck_storage_locations_agent_read CHECK (agent_read IN (0, 1)),
    CONSTRAINT ck_storage_locations_enabled CHECK (enabled IN (0, 1))
);

CREATE TABLE folders (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'folder',
    name TEXT NOT NULL,
    parent_folder_id TEXT,
    CONSTRAINT ck_folders_entity_type CHECK (entity_type = 'folder'),
    CONSTRAINT ck_folders_name CHECK (length(trim(name)) > 0),
    CONSTRAINT ck_folders_not_own_parent CHECK (parent_folder_id IS NULL OR parent_folder_id <> id),
    CONSTRAINT fk_folders_entity FOREIGN KEY (id, entity_type)
        REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
    CONSTRAINT fk_folders_parent FOREIGN KEY (parent_folder_id)
        REFERENCES folders (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_folders_parent_name ON folders (coalesce(parent_folder_id, ''), name);

CREATE TRIGGER trg_folders_no_cycle
BEFORE UPDATE OF parent_folder_id ON folders
WHEN new.parent_folder_id IS NOT NULL
BEGIN
    SELECT raise(ABORT, 'folder_hierarchy_cycle')
    WHERE EXISTS (
        WITH RECURSIVE up(id) AS (
            SELECT new.parent_folder_id
            UNION
            SELECT f.parent_folder_id
            FROM folders AS f JOIN up ON f.id = up.id
            WHERE f.parent_folder_id IS NOT NULL
        )
        SELECT 1 FROM up WHERE id = new.id
    );
END;

CREATE TRIGGER trg_folders_delete_entity
AFTER DELETE ON folders
BEGIN
    DELETE FROM entities WHERE id = old.id AND entity_type = 'folder';
END;

CREATE TABLE resources (
    id TEXT PRIMARY KEY,
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
    file_dev INTEGER,
    file_ino INTEGER,
    availability_status TEXT NOT NULL DEFAULT 'available',
    index_content INTEGER NOT NULL DEFAULT 0,
    index_status TEXT NOT NULL DEFAULT 'none',
    index_error_code TEXT,
    indexed_at TEXT,
    CONSTRAINT ck_resources_entity_type CHECK (entity_type = 'resource'),
    CONSTRAINT ck_resources_title CHECK (length(trim(title)) > 0),
    CONSTRAINT ck_resources_type CHECK (resource_type IN (
        'image', 'document', 'pdf', 'text', 'code', 'link',
        'note', 'study_note', 'archive', 'other'
    )),
    CONSTRAINT ck_resources_location_pair CHECK ((location_id IS NULL) = (relative_path IS NULL)),
    CONSTRAINT ck_resources_link_has_url CHECK (resource_type <> 'link' OR url IS NOT NULL),
    CONSTRAINT ck_resources_url_scheme CHECK (url IS NULL OR url LIKE 'http://%' OR url LIKE 'https://%'),
    CONSTRAINT ck_resources_size CHECK (size_bytes IS NULL OR size_bytes >= 0),
    CONSTRAINT ck_resources_availability CHECK (availability_status IN (
        'available', 'missing', 'moved', 'unreachable', 'forbidden'
    )),
    CONSTRAINT ck_resources_index_content CHECK (index_content IN (0, 1)),
    CONSTRAINT ck_resources_index_status CHECK (index_status IN (
        'none', 'pending', 'indexed', 'failed', 'skipped'
    )),
    CONSTRAINT fk_resources_entity FOREIGN KEY (id, entity_type)
        REFERENCES entities (id, entity_type) ON DELETE RESTRICT,
    CONSTRAINT fk_resources_folder FOREIGN KEY (folder_id)
        REFERENCES folders (id) ON DELETE RESTRICT,
    CONSTRAINT fk_resources_location FOREIGN KEY (location_id)
        REFERENCES storage_locations (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_resources_location_path ON resources (location_id, relative_path)
    WHERE location_id IS NOT NULL;
CREATE INDEX ix_resources_folder ON resources (folder_id);
CREATE INDEX ix_resources_type ON resources (resource_type);
CREATE INDEX ix_resources_availability ON resources (availability_status);
CREATE INDEX ix_resources_file_identity ON resources (file_dev, file_ino);

CREATE TRIGGER trg_resources_delete_entity
AFTER DELETE ON resources
BEGIN
    DELETE FROM entities WHERE id = old.id AND entity_type = 'resource';
END;

-- Índice textual común. `doc_id` existe porque FTS5 external content necesita
-- un rowid estable y las entidades usan UUID.
CREATE TABLE search_documents (
    doc_id INTEGER PRIMARY KEY,
    entity_id TEXT NOT NULL,
    chunk_no INTEGER NOT NULL DEFAULT 0,
    entity_type TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    CONSTRAINT uq_search_documents_chunk UNIQUE (entity_id, chunk_no),
    CONSTRAINT fk_search_documents_entity FOREIGN KEY (entity_id)
        REFERENCES entities (id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE search_fts USING fts5(
    title, body, tags,
    content = 'search_documents',
    content_rowid = 'doc_id',
    tokenize = "unicode61 remove_diacritics 2",
    prefix = '2 3'
);

CREATE TRIGGER trg_search_documents_ai AFTER INSERT ON search_documents BEGIN
    INSERT INTO search_fts (rowid, title, body, tags)
    VALUES (new.doc_id, new.title, new.body, new.tags);
END;

CREATE TRIGGER trg_search_documents_ad AFTER DELETE ON search_documents BEGIN
    INSERT INTO search_fts (search_fts, rowid, title, body, tags)
    VALUES ('delete', old.doc_id, old.title, old.body, old.tags);
END;

CREATE TRIGGER trg_search_documents_au AFTER UPDATE ON search_documents BEGIN
    INSERT INTO search_fts (search_fts, rowid, title, body, tags)
    VALUES ('delete', old.doc_id, old.title, old.body, old.tags);
    INSERT INTO search_fts (rowid, title, body, tags)
    VALUES (new.doc_id, new.title, new.body, new.tags);
END;
