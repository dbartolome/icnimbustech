-- Migración 018: Estudios IA por cuenta
-- Almacena los análisis de cross-selling generados por IA

CREATE TABLE IF NOT EXISTS estudios_ia_cuentas (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id   UUID NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    analisis    JSONB NOT NULL DEFAULT '{}',
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_estudios_ia_cuenta ON estudios_ia_cuentas (cuenta_id);
CREATE INDEX IF NOT EXISTS idx_estudios_ia_usuario ON estudios_ia_cuentas (usuario_id);
