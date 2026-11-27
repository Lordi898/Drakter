-- Revisión de seguridad del PR #76, N1. trg_pc_args (0016) dejaba reescribir args_json en el
-- mismo UPDATE que cerraba la fila, porque solo miraba new.status. La redacción solo vale
-- sobre una fila que ya estaba cerrada antes del UPDATE (el backend redacta en un UPDATE
-- aparte, tras cerrar), así que se exige también old.status cerrado.
DROP TRIGGER trg_pc_args;
CREATE TRIGGER trg_pc_args BEFORE UPDATE OF args_json ON pending_confirmations
WHEN new.args_json IS NOT old.args_json AND NOT (
  old.redacted_at IS NULL AND new.redacted_at IS NOT NULL
  AND old.status IN ('executed','failed','rejected','expired')
  AND new.status IN ('executed','failed','rejected','expired')
) BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;
