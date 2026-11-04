-- Ajustes: `value` es texto corto y no sensible (propuesta de drakter/hoy-ajustes).
-- value_json es columna generada de solo lectura para quien ya la lee: numero o JSON valido tal cual, texto entrecomillado.
-- Unica reconstruccion admitida en v1: settings no tiene hijos, FK ni triggers.
-- Un valor existente que no quepa en 64 caracteres aborta la migracion en vez de perderse.
CREATE TABLE settings_v2 (
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  value_json TEXT GENERATED ALWAYS AS (CASE WHEN json_valid(value) THEN value ELSE json_quote(value) END) VIRTUAL,
  CONSTRAINT pk_settings PRIMARY KEY (key),
  CONSTRAINT ck_settings_key CHECK (length(key) BETWEEN 1 AND 64),
  CONSTRAINT ck_settings_value CHECK (length(value) BETWEEN 1 AND 64)
);
INSERT INTO settings_v2 (key, value, updated_at)
SELECT key, CASE WHEN json_type(value_json) = 'text' THEN json_extract(value_json, '$') ELSE value_json END, updated_at
FROM settings;
DROP TABLE settings;
ALTER TABLE settings_v2 RENAME TO settings;
