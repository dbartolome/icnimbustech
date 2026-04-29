-- =============================================================================
-- Migración 012 — Seguimientos + Lead Scoring base
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_seguimiento') THEN
        CREATE TYPE tipo_seguimiento AS ENUM ('recordatorio', 'proximo_paso', 'cadencia');
    END IF;
END
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_seguimiento') THEN
        CREATE TYPE estado_seguimiento AS ENUM ('pendiente', 'completado', 'cancelado');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS seguimientos (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oportunidad_id    UUID REFERENCES oportunidades(id) ON DELETE CASCADE,
    cuenta_id         UUID REFERENCES cuentas(id) ON DELETE CASCADE,
    usuario_id        UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    creado_por        UUID NOT NULL REFERENCES usuarios(id),
    tipo              tipo_seguimiento NOT NULL DEFAULT 'proximo_paso',
    titulo            VARCHAR(300) NOT NULL,
    descripcion       TEXT,
    fecha_vencimiento DATE NOT NULL,
    estado            estado_seguimiento NOT NULL DEFAULT 'pendiente',
    completado_en     TIMESTAMPTZ,
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (oportunidad_id IS NOT NULL OR cuenta_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_seguimientos_oportunidad ON seguimientos(oportunidad_id);
CREATE INDEX IF NOT EXISTS idx_seguimientos_cuenta      ON seguimientos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_seguimientos_usuario     ON seguimientos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_seguimientos_estado      ON seguimientos(estado);
CREATE INDEX IF NOT EXISTS idx_seguimientos_vencimiento ON seguimientos(fecha_vencimiento);

DROP TRIGGER IF EXISTS trg_seguimientos_actualizado_en ON seguimientos;
CREATE TRIGGER trg_seguimientos_actualizado_en
    BEFORE UPDATE ON seguimientos
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE TABLE IF NOT EXISTS lead_scores (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oportunidad_id UUID NOT NULL UNIQUE REFERENCES oportunidades(id) ON DELETE CASCADE,
    score          INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    factores       JSONB NOT NULL DEFAULT '{}'::jsonb,
    calculado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lead_scores_oportunidad ON lead_scores(oportunidad_id);
CREATE INDEX IF NOT EXISTS idx_lead_scores_score       ON lead_scores(score);
