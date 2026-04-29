-- =============================================================================
-- Migración 029 — Transcripción de audio para documentos subidos
-- =============================================================================

-- Columna para almacenar el texto transcrito directamente en la tabla documentos
ALTER TABLE documentos ADD COLUMN IF NOT EXISTS transcripcion_texto TEXT;

CREATE INDEX IF NOT EXISTS idx_documentos_transcripcion
    ON documentos(id) WHERE transcripcion_texto IS NOT NULL;
