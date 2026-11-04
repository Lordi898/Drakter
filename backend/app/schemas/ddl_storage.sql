-- Propuesta para drakter-11, sin numerar: columnas que faltan en 0005_storage.sql.
-- agent_read: permiso explícito para que el agente lea una ubicación; por defecto no.
-- root_dev/root_ino: identidad de la raíz, comprobada al abrir para detectar que la sustituyeron.
-- La identidad de cada archivo (file_dev, file_ino) y `index_content` del recurso
-- van en entities.metadata_json y no necesitan columna.
ALTER TABLE storage_locations ADD COLUMN agent_read INTEGER NOT NULL DEFAULT 0
  CONSTRAINT ck_storage_locations_agent_read CHECK (agent_read IN (0, 1));
ALTER TABLE storage_locations ADD COLUMN root_dev INTEGER;
ALTER TABLE storage_locations ADD COLUMN root_ino INTEGER;
