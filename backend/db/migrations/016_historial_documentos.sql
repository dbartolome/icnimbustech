-- =============================================================================
-- Migración 016 — Historial de documentos generados por agentes IA
-- Almacena referencias a PDFs, PPTXs e informes subidos a MinIO.
-- =============================================================================

CREATE TYPE tipo_documento_generado AS ENUM (
    'investigacion',
    'propuesta',
    'pdf',
    'pptx',
    'briefing'
);

CREATE TABLE IF NOT EXISTS historial_documentos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id       UUID NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo            tipo_documento_generado NOT NULL,
    nombre_fichero  VARCHAR(300) NOT NULL,
    storage_key     TEXT NOT NULL,
    tamano_bytes    INTEGER,
    metadatos       JSONB NOT NULL DEFAULT '{}',
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_historial_cuenta   ON historial_documentos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_historial_usuario  ON historial_documentos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_historial_tipo     ON historial_documentos(tipo);
CREATE INDEX IF NOT EXISTS idx_historial_creado   ON historial_documentos(creado_en DESC);
