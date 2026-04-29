-- =============================================================================
-- Migración 022 — Contexto IA unificado para trazabilidad de artefactos
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'contexto_ia_tipo') THEN
        CREATE TYPE contexto_ia_tipo AS ENUM ('cuenta', 'cliente', 'producto', 'oportunidad');
    END IF;
END $$;

ALTER TABLE historial_documentos
    ALTER COLUMN cuenta_id DROP NOT NULL;

ALTER TABLE historial_documentos
    ADD COLUMN IF NOT EXISTS contexto_tipo contexto_ia_tipo,
    ADD COLUMN IF NOT EXISTS contexto_id UUID;

UPDATE historial_documentos
SET
    contexto_tipo = COALESCE(contexto_tipo, 'cuenta'::contexto_ia_tipo),
    contexto_id = COALESCE(contexto_id, cuenta_id)
WHERE contexto_tipo IS NULL OR contexto_id IS NULL;

ALTER TABLE historial_documentos
    ALTER COLUMN contexto_tipo SET DEFAULT 'cuenta',
    ALTER COLUMN contexto_tipo SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_historial_contexto
    ON historial_documentos(contexto_tipo, contexto_id);

