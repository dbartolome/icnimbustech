-- Módulo A: Cross-Selling Intelligence
-- Tabla que consolida datos de priorización, mensajes comerciales y señales de compra

CREATE TABLE IF NOT EXISTS cross_selling_intelligence (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_name        VARCHAR(300) NOT NULL,
    CONSTRAINT uq_cross_selling_account UNIQUE (account_name),

    -- Del Top 50: base de datos de penetración baja / alto potencial
    sbu                 VARCHAR(100),
    servicio_actual     TEXT,
    ops_abiertas        INTEGER,
    oportunidades_top   TEXT,

    -- Del Top 25: contexto OSINT y señales de activación
    sector_osint        VARCHAR(200),
    trigger_activador   TEXT,
    confianza           VARCHAR(20) CHECK (confianza IN ('Alta', 'Media-Alta', 'Media', 'Media-Baja', 'Baja')),

    -- Del Ranking 10: discurso comercial curado
    ranking_accionable  INTEGER,
    mensaje_comercial   TEXT,
    preguntas_discovery TEXT,

    creado_en           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cross_sbu ON cross_selling_intelligence (sbu);
CREATE INDEX IF NOT EXISTS idx_cross_ranking ON cross_selling_intelligence (ranking_accionable) WHERE ranking_accionable IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cross_confianza ON cross_selling_intelligence (confianza);
CREATE INDEX IF NOT EXISTS idx_cross_account_name ON cross_selling_intelligence USING gin (to_tsvector('spanish', account_name));
