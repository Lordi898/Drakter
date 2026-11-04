-- PROPUESTA de DDL del módulo de ajustes. Sin numerar: la absorbe y numera drakter-11.
-- Solo ajustes no sensibles (D: settings "no sensibles"). Las claves válidas las limita
-- app/services/settings_models.py#SETTING_KEYS: la base no es el sitio de los secretos.
-- Depende de `audit_events` (misma migración común): si no existe, escribir falla cerrado.

CREATE TABLE settings (
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CONSTRAINT pk_settings PRIMARY KEY (key),
    CONSTRAINT ck_settings_key CHECK (length(key) BETWEEN 1 AND 64),
    CONSTRAINT ck_settings_value CHECK (length(value) BETWEEN 1 AND 64)
);
