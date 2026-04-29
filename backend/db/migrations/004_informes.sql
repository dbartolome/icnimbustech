-- =============================================================================
-- SGS España — Migración 004: Informes PDF generados con IA
-- =============================================================================

CREATE TYPE tipo_informe AS ENUM (
    'ejecutivo_mensual',
    'analisis_comercial',
    'propuesta_cliente',
    'revision_pipeline'
);

CREATE TYPE estado_informe AS ENUM (
    'pendiente',
    'generando',
    'completado',
    'error'
);

CREATE TABLE informes_generados (
    id              UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID           NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo            tipo_informe   NOT NULL,
    titulo          VARCHAR(300)   NOT NULL,
    periodo         VARCHAR(50),                   -- ej: "2025-Q4", "2025-ANUAL"
    destinatario    VARCHAR(150),
    contexto        TEXT,
    indice_json     JSONB,                         -- índice generado por Claude
    ruta_pdf        TEXT,                          -- path local en dev
    paginas         INTEGER,
    estado          estado_informe NOT NULL DEFAULT 'pendiente',
    error_msg       TEXT,
    creado_en       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    completado_en   TIMESTAMPTZ
);

CREATE INDEX idx_informes_usuario_id ON informes_generados(usuario_id);
CREATE INDEX idx_informes_estado     ON informes_generados(estado);
CREATE INDEX idx_informes_creado_en  ON informes_generados(creado_en DESC);
