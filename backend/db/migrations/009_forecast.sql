-- =============================================================================
-- Migración 009: Forecast por Comercial + Cola Cross-sell
-- P12 — Modelo de predicción a 3 meses + cross-sell asignado por owner
-- =============================================================================

-- Snapshots de forecast (uno por recálculo, compara forecast vs real)
CREATE TABLE IF NOT EXISTS forecast_snapshots (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id       UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_nombre   VARCHAR(255) NOT NULL,
    snapshot_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    mes_1            VARCHAR(7) NOT NULL,   -- "2026-04"
    mes_2            VARCHAR(7) NOT NULL,   -- "2026-05"
    mes_3            VARCHAR(7) NOT NULL,   -- "2026-06"
    -- Inputs del modelo
    pipeline_total   NUMERIC(12,2) DEFAULT 0,
    pipeline_maduro  NUMERIC(12,2) DEFAULT 0,
    baseline_mediana NUMERIC(12,2) DEFAULT 0,
    sbu_dominante    VARCHAR(100),
    wr_sbu           NUMERIC(5,2),
    -- Escenario pesimista (solo baseline histórico × 3)
    pesimista_m1     NUMERIC(12,2) DEFAULT 0,
    pesimista_m2     NUMERIC(12,2) DEFAULT 0,
    pesimista_m3     NUMERIC(12,2) DEFAULT 0,
    pesimista_total  NUMERIC(12,2) DEFAULT 0,
    -- Escenario base (baseline + 10% pipeline maduro)
    base_m1          NUMERIC(12,2) DEFAULT 0,
    base_m2          NUMERIC(12,2) DEFAULT 0,
    base_m3          NUMERIC(12,2) DEFAULT 0,
    base_total       NUMERIC(12,2) DEFAULT 0,
    -- Escenario optimista (baseline + 20% maduro + 15% cross-sell)
    optimista_m1     NUMERIC(12,2) DEFAULT 0,
    optimista_m2     NUMERIC(12,2) DEFAULT 0,
    optimista_m3     NUMERIC(12,2) DEFAULT 0,
    optimista_total  NUMERIC(12,2) DEFAULT 0,
    -- Real a fin de mes (se rellena a posteriori)
    real_m1          NUMERIC(12,2),
    real_m2          NUMERIC(12,2),
    real_m3          NUMERIC(12,2),
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fs_usuario      ON forecast_snapshots(usuario_id);
CREATE INDEX IF NOT EXISTS idx_fs_snapshot     ON forecast_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_fs_mes1         ON forecast_snapshots(mes_1);

-- Cola de cross-sell priorizada por comercial (caché semanal)
CREATE TABLE IF NOT EXISTS owner_cross_sell_queue (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id       UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_nombre   VARCHAR(255) NOT NULL,
    cuenta_nombre    VARCHAR(300) NOT NULL,
    sbu_actual       VARCHAR(100),
    productos_won    TEXT,
    ops_abiertas     INTEGER DEFAULT 0,
    pipeline_abierto NUMERIC(12,2) DEFAULT 0,
    oportunidades_top TEXT,
    mensaje_comercial TEXT,
    preguntas_discovery TEXT,
    confianza        VARCHAR(20),
    score            NUMERIC(8,2) DEFAULT 0,
    semana           VARCHAR(10),   -- "2026-W12"
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocq_usuario ON owner_cross_sell_queue(usuario_id);
CREATE INDEX IF NOT EXISTS idx_ocq_semana  ON owner_cross_sell_queue(semana);
CREATE INDEX IF NOT EXISTS idx_ocq_score   ON owner_cross_sell_queue(score DESC);
