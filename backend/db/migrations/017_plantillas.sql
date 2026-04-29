-- =============================================================================
-- Migración 017 — Plantillas de documentación (admin)
-- CRUD de plantillas Jinja2 para PDFs, PPTXs e informes.
-- =============================================================================

CREATE TYPE tipo_plantilla AS ENUM (
    'pdf',
    'pptx',
    'investigacion',
    'propuesta',
    'briefing'
);

CREATE TABLE IF NOT EXISTS plantillas_documentacion (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre          VARCHAR(200) NOT NULL,
    tipo            tipo_plantilla NOT NULL,
    activa          BOOLEAN NOT NULL DEFAULT TRUE,
    -- Estructura del contenido según tipo:
    -- pdf/pptx:      { "secciones": [{ "titulo": "", "cuerpo": "template Jinja2", "orden": 1 }] }
    -- investigacion: { "campos": [{ "clave": "", "etiqueta": "", "placeholder": "" }] }
    contenido       JSONB NOT NULL DEFAULT '{}',
    -- Variables disponibles para usar en los templates, e.g. ["cuenta_nombre", "sector"]
    variables       JSONB NOT NULL DEFAULT '[]',
    creado_por      UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plantillas_tipo   ON plantillas_documentacion(tipo);
CREATE INDEX IF NOT EXISTS idx_plantillas_activa ON plantillas_documentacion(activa);

CREATE TRIGGER trg_plantillas_actualizado_en
    BEFORE UPDATE ON plantillas_documentacion
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();
