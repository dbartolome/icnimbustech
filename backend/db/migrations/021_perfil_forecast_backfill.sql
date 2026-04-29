-- =============================================================================
-- Migracion 021: Backfill de tablas perfil + forecast
-- Corrige entornos con esquema parcial donde faltan tablas usadas por:
-- - /forecast/me
-- - /forecast/cross-sell-queue
-- - /perfil/me
-- - /perfil/me/objetivos
-- - /perfil/me/notificaciones
-- =============================================================================

CREATE TABLE IF NOT EXISTS comercial_perfil (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    telefono        VARCHAR(30),
    zona            VARCHAR(100),
    sbu_principal   VARCHAR(100),
    avatar_url      VARCHAR(500),
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comercial_perfil_usuario
    ON comercial_perfil(usuario_id);

DROP TRIGGER IF EXISTS trg_comercial_perfil_actualizado_en ON comercial_perfil;
CREATE TRIGGER trg_comercial_perfil_actualizado_en
    BEFORE UPDATE ON comercial_perfil
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE TABLE IF NOT EXISTS comercial_objetivos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nombre          VARCHAR(200) NOT NULL,
    valor_actual    NUMERIC(12,2) NOT NULL DEFAULT 0,
    valor_meta      NUMERIC(12,2) NOT NULL,
    unidad          VARCHAR(20) NOT NULL CHECK (unidad IN ('EUR', 'PCT', 'OPS', 'CUENTAS')),
    periodo         VARCHAR(20) NOT NULL,
    creado_en       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comercial_objetivos_usuario
    ON comercial_objetivos(usuario_id);

DROP TRIGGER IF EXISTS trg_comercial_objetivos_actualizado_en ON comercial_objetivos;
CREATE TRIGGER trg_comercial_objetivos_actualizado_en
    BEFORE UPDATE ON comercial_objetivos
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE TABLE IF NOT EXISTS notificaciones_config (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id            UUID NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    alertas_pipeline      BOOLEAN NOT NULL DEFAULT TRUE,
    briefing_diario       BOOLEAN NOT NULL DEFAULT FALSE,
    alerta_win_rate       BOOLEAN NOT NULL DEFAULT TRUE,
    hora_briefing         TIME NOT NULL DEFAULT TIME '08:00',
    umbral_win_rate       NUMERIC(5,2) NOT NULL DEFAULT 60.00,
    voz_tts               VARCHAR(50) NOT NULL DEFAULT 'es-ES',
    duracion_podcast_min  INTEGER NOT NULL DEFAULT 5 CHECK (duracion_podcast_min BETWEEN 1 AND 30),
    creado_en             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notificaciones_config_usuario
    ON notificaciones_config(usuario_id);

DROP TRIGGER IF EXISTS trg_notificaciones_config_actualizado_en ON notificaciones_config;
CREATE TRIGGER trg_notificaciones_config_actualizado_en
    BEFORE UPDATE ON notificaciones_config
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

-- Tablas de forecast/cross-sell (se recrean de forma idempotente por seguridad)
CREATE TABLE IF NOT EXISTS forecast_snapshots (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id       UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_nombre   VARCHAR(255) NOT NULL,
    snapshot_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    mes_1            VARCHAR(7) NOT NULL,
    mes_2            VARCHAR(7) NOT NULL,
    mes_3            VARCHAR(7) NOT NULL,
    pipeline_total   NUMERIC(12,2) DEFAULT 0,
    pipeline_maduro  NUMERIC(12,2) DEFAULT 0,
    baseline_mediana NUMERIC(12,2) DEFAULT 0,
    sbu_dominante    VARCHAR(100),
    wr_sbu           NUMERIC(5,2),
    pesimista_m1     NUMERIC(12,2) DEFAULT 0,
    pesimista_m2     NUMERIC(12,2) DEFAULT 0,
    pesimista_m3     NUMERIC(12,2) DEFAULT 0,
    pesimista_total  NUMERIC(12,2) DEFAULT 0,
    base_m1          NUMERIC(12,2) DEFAULT 0,
    base_m2          NUMERIC(12,2) DEFAULT 0,
    base_m3          NUMERIC(12,2) DEFAULT 0,
    base_total       NUMERIC(12,2) DEFAULT 0,
    optimista_m1     NUMERIC(12,2) DEFAULT 0,
    optimista_m2     NUMERIC(12,2) DEFAULT 0,
    optimista_m3     NUMERIC(12,2) DEFAULT 0,
    optimista_total  NUMERIC(12,2) DEFAULT 0,
    real_m1          NUMERIC(12,2),
    real_m2          NUMERIC(12,2),
    real_m3          NUMERIC(12,2),
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fs_usuario  ON forecast_snapshots(usuario_id);
CREATE INDEX IF NOT EXISTS idx_fs_snapshot ON forecast_snapshots(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_fs_mes1     ON forecast_snapshots(mes_1);

CREATE TABLE IF NOT EXISTS owner_cross_sell_queue (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id         UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_nombre     VARCHAR(255) NOT NULL,
    cuenta_nombre      VARCHAR(300) NOT NULL,
    sbu_actual         VARCHAR(100),
    productos_won      TEXT,
    ops_abiertas       INTEGER DEFAULT 0,
    pipeline_abierto   NUMERIC(12,2) DEFAULT 0,
    oportunidades_top  TEXT,
    mensaje_comercial  TEXT,
    preguntas_discovery TEXT,
    confianza          VARCHAR(20),
    score              NUMERIC(8,2) DEFAULT 0,
    semana             VARCHAR(10),
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ocq_usuario ON owner_cross_sell_queue(usuario_id);
CREATE INDEX IF NOT EXISTS idx_ocq_semana  ON owner_cross_sell_queue(semana);
CREATE INDEX IF NOT EXISTS idx_ocq_score   ON owner_cross_sell_queue(score DESC);
