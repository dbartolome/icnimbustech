-- =============================================================================
-- Migración 019 — Documentos asociados a cuenta
-- Añade cuenta_id y contenido_extraido a documentos para soportar
-- la ficha de cliente: archivos propios + chat con documento.
-- =============================================================================

ALTER TABLE documentos
    ADD COLUMN IF NOT EXISTS cuenta_id         UUID REFERENCES cuentas(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS contenido_extraido TEXT;

CREATE INDEX IF NOT EXISTS idx_documentos_cuenta ON documentos(cuenta_id)
    WHERE cuenta_id IS NOT NULL;
