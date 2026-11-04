-- Indice unico FTS5 sobre una tabla puente con rowid estable. El servicio escribe search_documents en la misma transaccion.
-- Reconstruible: INSERT INTO search_fts(search_fts) VALUES('rebuild').
CREATE TABLE search_documents (
  doc_id INTEGER PRIMARY KEY,
  entity_id TEXT NOT NULL,
  chunk_no INTEGER NOT NULL DEFAULT 0,
  entity_type TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL DEFAULT '',
  tags TEXT NOT NULL DEFAULT '',
  CONSTRAINT uq_search_documents UNIQUE (entity_id, chunk_no),
  CONSTRAINT ck_search_chunk CHECK (chunk_no >= 0),
  CONSTRAINT fk_search_documents_entity FOREIGN KEY (entity_id, entity_type) REFERENCES entities (id, entity_type) ON DELETE CASCADE
);
CREATE INDEX ix_search_documents_type ON search_documents (entity_type);
CREATE VIRTUAL TABLE search_fts USING fts5(
  title, body, tags,
  content='search_documents', content_rowid='doc_id',
  tokenize="unicode61 remove_diacritics 2", prefix='2 3'
);
CREATE TRIGGER trg_search_ai AFTER INSERT ON search_documents BEGIN
  INSERT INTO search_fts (rowid, title, body, tags) VALUES (new.doc_id, new.title, new.body, new.tags);
END;
CREATE TRIGGER trg_search_ad AFTER DELETE ON search_documents BEGIN
  INSERT INTO search_fts (search_fts, rowid, title, body, tags) VALUES ('delete', old.doc_id, old.title, old.body, old.tags);
END;
CREATE TRIGGER trg_search_au AFTER UPDATE ON search_documents BEGIN
  INSERT INTO search_fts (search_fts, rowid, title, body, tags) VALUES ('delete', old.doc_id, old.title, old.body, old.tags);
  INSERT INTO search_fts (rowid, title, body, tags) VALUES (new.doc_id, new.title, new.body, new.tags);
END;
