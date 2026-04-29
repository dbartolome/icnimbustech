-- =============================================================================
-- SGS España — Plataforma de Inteligencia Comercial
-- Migración 005: RBAC — nombre_csv, manager_sbus, audit_role_changes
-- PostgreSQL 15+
-- =============================================================================

-- Columna para mapear usuario con "Opportunity Owner" del CSV de Salesforce
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS nombre_csv VARCHAR(200);

CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_csv ON usuarios(nombre_csv);

-- =============================================================================
-- TABLA: manager_sbus
-- Un manager puede gestionar múltiples SBUs (relación N:M)
-- =============================================================================

CREATE TABLE IF NOT EXISTS manager_sbus (
    manager_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    sbu_id      UUID NOT NULL REFERENCES sbu(id)      ON DELETE CASCADE,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (manager_id, sbu_id)
);

CREATE INDEX IF NOT EXISTS idx_manager_sbus_manager_id ON manager_sbus(manager_id);
CREATE INDEX IF NOT EXISTS idx_manager_sbus_sbu_id     ON manager_sbus(sbu_id);

-- =============================================================================
-- TABLA: audit_role_changes
-- Registro inmutable de cambios de rol para compliance
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_role_changes (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    rol_anterior    rol_usuario NOT NULL,
    rol_nuevo       rol_usuario NOT NULL,
    cambiado_por_id UUID        REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo          TEXT,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_role_changes_usuario_id ON audit_role_changes(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_role_changes_creado_en  ON audit_role_changes(creado_en);
