-- ============================================================================
-- MIGRACIÓN 015: Campos operacionales de configuración IA
-- ============================================================================

BEGIN;

ALTER TABLE ia_configuracion
ADD COLUMN IF NOT EXISTS operational_configs JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMIT;
