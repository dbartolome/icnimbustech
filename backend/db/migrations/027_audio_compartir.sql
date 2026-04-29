-- =============================================================================
-- Migración 027 — Audio MP3 persistente + sistema de compartición de artefactos
-- =============================================================================

-- 1. Nuevo valor en enum: 'audio' para briefings convertidos a MP3
ALTER TYPE tipo_documento_generado ADD VALUE IF NOT EXISTS 'audio';

-- 2. Vincular audio generado con su script de origen
ALTER TABLE historial_documentos
    ADD COLUMN IF NOT EXISTS audio_origen_id UUID REFERENCES historial_documentos(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_historial_audio_origen ON historial_documentos(audio_origen_id)
    WHERE audio_origen_id IS NOT NULL;

-- 3. Tokens de compartición pública (sin autenticación requerida en destino)
CREATE TABLE IF NOT EXISTS artefacto_compartidos (
    token      TEXT        PRIMARY KEY DEFAULT encode(gen_random_bytes(32), 'hex'),
    doc_id     UUID        NOT NULL REFERENCES historial_documentos(id) ON DELETE CASCADE,
    creado_por UUID        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    expira_en  TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '7 days'),
    usos       INTEGER     NOT NULL DEFAULT 0,
    creado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_compartidos_doc    ON artefacto_compartidos(doc_id);
CREATE INDEX IF NOT EXISTS idx_compartidos_expira ON artefacto_compartidos(expira_en);
