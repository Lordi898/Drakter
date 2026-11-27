-- Retención de pending_confirmations (revisión de seguridad del PR #76, I5).
-- Las herramientas que tocan texto de terceros o tecleado (act_in_app, open_target...) no
-- pueden dejar ese texto para siempre en la base. Cuando la fila queda cerrada, el backend
-- sustituye args_json por lo que ya guarda la auditoría (campos hasheados) y marca
-- redacted_at. args_hash no cambia: la auditoría sigue enlazando con la fila.
-- La única escritura nueva permitida es esa: una vez, sobre una fila cerrada.
ALTER TABLE pending_confirmations ADD COLUMN redacted_at TEXT;

DROP TRIGGER trg_pc_immutable;
CREATE TRIGGER trg_pc_immutable BEFORE UPDATE OF tool_name, actor_type, origin, correlation_id, args_hash, targets_json, summary, affected_count, risk, created_at, expires_at ON pending_confirmations
BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;

-- args_json solo cambia al redactar: fila cerrada, sin redactar antes y marcándola ahora.
CREATE TRIGGER trg_pc_args BEFORE UPDATE OF args_json ON pending_confirmations
WHEN new.args_json IS NOT old.args_json AND NOT (
  old.redacted_at IS NULL AND new.redacted_at IS NOT NULL
  AND new.status IN ('executed','failed','rejected','expired')
) BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;

-- Una fila cerrada no cambia, salvo la redacción única: mismo estado y decisión, y solo
-- args_json, result_json y redacted_at distintos.
DROP TRIGGER trg_pc_closed;
CREATE TRIGGER trg_pc_closed BEFORE UPDATE ON pending_confirmations
WHEN old.status IN ('executed','failed','rejected','expired') AND NOT (
  old.redacted_at IS NULL AND new.redacted_at IS NOT NULL
  AND new.status IS old.status AND new.decided_at IS old.decided_at
  AND new.decided_via IS old.decided_via AND new.executed_at IS old.executed_at
  AND new.error_code IS old.error_code
) BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;

CREATE TRIGGER trg_pc_redacted_once BEFORE UPDATE OF redacted_at ON pending_confirmations
WHEN old.redacted_at IS NOT NULL AND new.redacted_at IS NOT old.redacted_at BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;

CREATE TRIGGER trg_pc_born_unredacted BEFORE INSERT ON pending_confirmations
WHEN new.redacted_at IS NOT NULL BEGIN
  SELECT raise(ABORT, 'confirmation_invalid_transition');
END;
