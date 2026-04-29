-- =============================================================================
-- Migración 013 — Coaching comercial + Calidad de entregables IA
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_coaching') THEN
        CREATE TYPE tipo_coaching AS ENUM ('analisis_notas', 'plan_mejora', 'feedback_pitch');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS coaching_sesiones (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cuenta_id   UUID REFERENCES cuentas(id) ON DELETE SET NULL,
    tipo        tipo_coaching NOT NULL,
    resultado   JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_coaching_usuario ON coaching_sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_coaching_cuenta  ON coaching_sesiones(cuenta_id);

CREATE TABLE IF NOT EXISTS validaciones_calidad (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id        UUID NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
    tipo_entregable  VARCHAR(20) NOT NULL CHECK (tipo_entregable IN ('pdf', 'pptx', 'deck', 'briefing')),
    valido           BOOLEAN NOT NULL,
    nivel            VARCHAR(10) NOT NULL CHECK (nivel IN ('ok', 'warning', 'error')),
    checks           JSONB NOT NULL DEFAULT '[]'::jsonb,
    usuario_id       UUID REFERENCES usuarios(id),
    forzado          BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_validaciones_cuenta ON validaciones_calidad(cuenta_id);
