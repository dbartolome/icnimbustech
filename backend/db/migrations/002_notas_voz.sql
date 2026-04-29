-- =============================================================================
-- SGS España — Migración 002: Notas de voz por oportunidad
-- =============================================================================

CREATE TABLE notas_voz (
    id             UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id     UUID         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    oportunidad_id UUID         REFERENCES oportunidades(id) ON DELETE SET NULL,
    titulo         VARCHAR(200) NOT NULL,
    transcripcion  TEXT         NOT NULL,
    duracion_seg   INTEGER,
    creado_en      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notas_voz_usuario_id     ON notas_voz(usuario_id);
CREATE INDEX idx_notas_voz_oportunidad_id ON notas_voz(oportunidad_id);
CREATE INDEX idx_notas_voz_creado_en      ON notas_voz(creado_en DESC);
