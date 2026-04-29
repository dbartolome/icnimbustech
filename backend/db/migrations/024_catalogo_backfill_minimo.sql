-- Hotfix v1.0.45
-- Garantiza la existencia del catálogo SGS y matriz sectorial
-- en entornos donde no se aplicó la migración 008.

CREATE TABLE IF NOT EXISTS catalogo_servicios (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    linea             VARCHAR(100) NOT NULL,
    servicio          TEXT NOT NULL,
    entregables       TEXT,
    normas_clave      TEXT,
    sectores_objetivo TEXT,
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalogo_linea ON catalogo_servicios (linea);
CREATE INDEX IF NOT EXISTS idx_catalogo_normas
    ON catalogo_servicios USING gin (to_tsvector('spanish', COALESCE(normas_clave, '')));

CREATE TABLE IF NOT EXISTS matriz_sectorial (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sector               VARCHAR(100) NOT NULL,
    certificaciones_tipo TEXT NOT NULL,
    pain_points          TEXT NOT NULL,
    servicios_sgs_tipo   TEXT NOT NULL,
    creado_en            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matriz_sector ON matriz_sectorial (sector);
