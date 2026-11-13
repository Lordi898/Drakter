-- Endurecimiento de pending_confirmations (revisión adversarial, CONF-03/04/06/07).
-- Una fila nace pendiente, su identidad no cambia y, una vez cerrada, nada la reescribe.
CREATE TRIGGER trg_pc_identity BEFORE UPDATE OF id, turn_id ON pending_confirmations
WHEN new.id IS NOT old.id OR new.turn_id IS NOT old.turn_id BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;
CREATE TRIGGER trg_pc_born_pending BEFORE INSERT ON pending_confirmations
WHEN new.status IS NOT 'pending' OR new.decided_at IS NOT NULL OR new.executed_at IS NOT NULL
  OR new.result_json IS NOT NULL OR new.error_code IS NOT NULL BEGIN
  SELECT raise(ABORT, 'confirmation_invalid_transition');
END;
CREATE TRIGGER trg_pc_closed BEFORE UPDATE ON pending_confirmations
WHEN old.status IN ('executed','failed','rejected','expired') BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;
CREATE TRIGGER trg_pc_decided_once BEFORE UPDATE OF decided_at, decided_via ON pending_confirmations
WHEN old.decided_at IS NOT NULL
  AND (new.decided_at IS NOT old.decided_at OR new.decided_via IS NOT old.decided_via) BEGIN
  SELECT raise(ABORT, 'confirmation_immutable');
END;
