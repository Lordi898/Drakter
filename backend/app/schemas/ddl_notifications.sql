-- Propuesta sobre `notifications` de 0001_core_entities (sin numerar): la absorbe y numera drakter-11.
-- D-18 pide clave de deduplicacion y 0001 no la tiene. Sin este indice el tick falla y no emite,
-- que es lo correcto: emitir sin deduplicar repetiria avisos tras cada reinicio.
-- dedupe_key NULL = notificacion sin deduplicar (no la usan los recordatorios).
ALTER TABLE notifications ADD COLUMN dedupe_key TEXT;
CREATE UNIQUE INDEX ux_notifications_dedupe ON notifications (dedupe_key) WHERE dedupe_key IS NOT NULL;
