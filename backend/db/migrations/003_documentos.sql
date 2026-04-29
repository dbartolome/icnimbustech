-- =============================================================================
-- SGS España — Migración 003: Documentos adjuntos por oportunidad
-- =============================================================================

CREATE TABLE documentos (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    oportunidad_id  UUID         REFERENCES oportunidades(id) ON DELETE SET NULL,
    nombre_original VARCHAR(255) NOT NULL,
    nombre_guardado VARCHAR(255) NOT NULL UNIQUE,  -- nombre en disco (uuid + extensión)
    tipo_mime       VARCHAR(100),
    tamaño_bytes    INTEGER,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documentos_usuario_id     ON documentos(usuario_id);
CREATE INDEX idx_documentos_oportunidad_id ON documentos(oportunidad_id);
CREATE INDEX idx_documentos_creado_en      ON documentos(creado_en DESC);
