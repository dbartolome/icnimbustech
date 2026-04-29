-- =============================================================================
-- Migración 026 — Objetivos comerciales accionables (IA + cross-selling)
-- =============================================================================

CREATE TABLE IF NOT EXISTS objetivos_comerciales (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id        UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cuenta_id         UUID REFERENCES cuentas(id) ON DELETE SET NULL,
    oportunidad_id    UUID REFERENCES oportunidades(id) ON DELETE SET NULL,
    tipo_objetivo     VARCHAR(40) NOT NULL,      -- cierre | upsell | recuperacion | cross_sell
    origen            VARCHAR(40) NOT NULL,      -- manual | sugerido_ia | cross_selling
    titulo            VARCHAR(260) NOT NULL,
    descripcion       TEXT,
    prioridad         SMALLINT NOT NULL DEFAULT 3 CHECK (prioridad BETWEEN 1 AND 5),
    estado            VARCHAR(30) NOT NULL DEFAULT 'abierto', -- abierto | en_progreso | bloqueado | completado | descartado
    fecha_objetivo    DATE,
    score_impacto     NUMERIC(6,2) NOT NULL DEFAULT 0,
    score_confianza   NUMERIC(6,2) NOT NULL DEFAULT 0,
    cross_sell_ref    TEXT,
    metadatos         JSONB NOT NULL DEFAULT '{}',
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    eliminado_en      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_objetivos_usuario ON objetivos_comerciales(usuario_id) WHERE eliminado_en IS NULL;
CREATE INDEX IF NOT EXISTS idx_objetivos_cuenta ON objetivos_comerciales(cuenta_id) WHERE eliminado_en IS NULL;
CREATE INDEX IF NOT EXISTS idx_objetivos_oportunidad ON objetivos_comerciales(oportunidad_id) WHERE eliminado_en IS NULL;
CREATE INDEX IF NOT EXISTS idx_objetivos_estado ON objetivos_comerciales(estado) WHERE eliminado_en IS NULL;
CREATE INDEX IF NOT EXISTS idx_objetivos_prioridad ON objetivos_comerciales(prioridad DESC, score_impacto DESC) WHERE eliminado_en IS NULL;

DROP TRIGGER IF EXISTS trg_objetivos_comerciales_actualizado_en ON objetivos_comerciales;
CREATE TRIGGER trg_objetivos_comerciales_actualizado_en
BEFORE UPDATE ON objetivos_comerciales
FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE TABLE IF NOT EXISTS objetivo_artefactos_ia (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    objetivo_id         UUID NOT NULL REFERENCES objetivos_comerciales(id) ON DELETE CASCADE,
    artefacto_id        UUID NOT NULL REFERENCES ia_artefactos(id) ON DELETE CASCADE,
    tipo_relacion       VARCHAR(30) NOT NULL DEFAULT 'generado', -- generado | fuente | soporte
    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (objetivo_id, artefacto_id)
);

CREATE INDEX IF NOT EXISTS idx_objetivo_artefactos_objetivo ON objetivo_artefactos_ia(objetivo_id);
CREATE INDEX IF NOT EXISTS idx_objetivo_artefactos_artefacto ON objetivo_artefactos_ia(artefacto_id);
