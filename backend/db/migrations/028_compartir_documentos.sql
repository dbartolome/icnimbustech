-- =============================================================================
-- Migración 028 — Extiende artefacto_compartidos para documentos de usuario
-- =============================================================================

-- doc_id pasa a ser nullable (puede ser historial_documentos O documentos)
ALTER TABLE artefacto_compartidos
    ALTER COLUMN doc_id DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS documentos_id UUID REFERENCES documentos(id) ON DELETE CASCADE;

-- Garantizar que siempre hay exactamente una referencia
ALTER TABLE artefacto_compartidos
    DROP CONSTRAINT IF EXISTS chk_compartidos_una_fuente,
    ADD CONSTRAINT chk_compartidos_una_fuente CHECK (
        (doc_id IS NOT NULL AND documentos_id IS NULL)
        OR
        (doc_id IS NULL AND documentos_id IS NOT NULL)
    );

CREATE INDEX IF NOT EXISTS idx_compartidos_documentos ON artefacto_compartidos(documentos_id)
    WHERE documentos_id IS NOT NULL;
