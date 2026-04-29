-- =============================================================================
-- Migración 023 — Extiende plantillas admin para informes IA
-- =============================================================================

ALTER TYPE tipo_plantilla ADD VALUE IF NOT EXISTS 'informe';

