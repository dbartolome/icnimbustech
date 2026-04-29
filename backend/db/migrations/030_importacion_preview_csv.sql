-- MIGRACIÓN 030: Vista previa persistida de CSV por importación

ALTER TABLE importaciones
    ADD COLUMN IF NOT EXISTS preview_columnas JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS preview_filas JSONB NOT NULL DEFAULT '[]'::jsonb;
