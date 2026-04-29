-- =============================================================================
-- SGS España — Plataforma de Inteligencia Comercial
-- Migración 001: Schema inicial
-- PostgreSQL 15+
-- =============================================================================

-- Extensiones
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- TIPOS ENUM
-- =============================================================================

CREATE TYPE rol_usuario AS ENUM ('admin', 'manager', 'comercial');

CREATE TYPE etapa_oportunidad AS ENUM (
    'estimation_sent',
    'technically_approved',
    'in_progress',
    'discover',
    'contract_offer_sent',
    'propose',
    'estimation_accepted',
    'negotiate',
    'closed_won',
    'closed_lost',
    'closed_withdrawn'
);

CREATE TYPE tipo_oportunidad AS ENUM ('nueva', 'renovacion', 'ampliacion');

CREATE TYPE estado_importacion AS ENUM ('procesando', 'completado', 'error');

CREATE TYPE nivel_alerta AS ENUM ('critico', 'seguimiento', 'oportunidad');

-- =============================================================================
-- FUNCIÓN TRIGGER: actualizar_updated_en
-- Se asigna a todas las tablas para mantener actualizado_en automáticamente
-- =============================================================================

CREATE OR REPLACE FUNCTION actualizar_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TABLA: sbu (Strategic Business Units)
-- =============================================================================

CREATE TABLE sbu (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(100) NOT NULL UNIQUE,
    codigo          VARCHAR(20)  NOT NULL UNIQUE,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_sbu_actualizado_en
    BEFORE UPDATE ON sbu
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

-- Datos base de SBUs se cargan en 010_seed_mvp.sql para mantener IDs estables.

-- =============================================================================
-- TABLA: usuarios
-- =============================================================================

CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    nombre_completo VARCHAR(150) NOT NULL,
    hash_contrasena TEXT         NOT NULL,
    rol             rol_usuario  NOT NULL DEFAULT 'comercial',
    manager_id      UUID         REFERENCES usuarios(id) ON DELETE SET NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    eliminado_en    TIMESTAMPTZ,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_usuarios_actualizado_en
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_usuarios_email       ON usuarios(email);
CREATE INDEX idx_usuarios_rol         ON usuarios(rol);
CREATE INDEX idx_usuarios_manager_id  ON usuarios(manager_id);

-- =============================================================================
-- TABLA: cuentas (empresas/clientes)
-- =============================================================================

CREATE TABLE cuentas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(255) NOT NULL,
    eliminado_en    TIMESTAMPTZ,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_cuentas_actualizado_en
    BEFORE UPDATE ON cuentas
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_cuentas_nombre ON cuentas(nombre);

-- =============================================================================
-- TABLA: productos (normas y servicios)
-- =============================================================================

CREATE TABLE productos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre          VARCHAR(150) NOT NULL UNIQUE,
    sbu_id          UUID         REFERENCES sbu(id) ON DELETE SET NULL,
    activo          BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_productos_actualizado_en
    BEFORE UPDATE ON productos
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_productos_sbu_id ON productos(sbu_id);

-- Datos base de productos se cargan en 010_seed_mvp.sql para mantener IDs estables.

-- =============================================================================
-- TABLA: oportunidades (tabla principal del pipeline)
-- =============================================================================

CREATE TABLE oportunidades (
    id              UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id     VARCHAR(100)      UNIQUE,          -- ID de Salesforce para upsert
    nombre          VARCHAR(500)      NOT NULL,
    cuenta_id       UUID              REFERENCES cuentas(id) ON DELETE SET NULL,
    propietario_id  UUID              REFERENCES usuarios(id) ON DELETE SET NULL,
    sbu_id          UUID              REFERENCES sbu(id) ON DELETE SET NULL,
    producto_id     UUID              REFERENCES productos(id) ON DELETE SET NULL,
    linea_negocio   VARCHAR(100),
    canal_venta     VARCHAR(50),
    importe         NUMERIC(12, 2)    NOT NULL DEFAULT 0,
    etapa           etapa_oportunidad NOT NULL,
    tipo            tipo_oportunidad,
    fecha_creacion  DATE              NOT NULL,
    fecha_decision  DATE,
    eliminado_en    TIMESTAMPTZ,
    creado_en       TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    actualizado_en  TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_oportunidades_actualizado_en
    BEFORE UPDATE ON oportunidades
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_oportunidades_etapa         ON oportunidades(etapa);
CREATE INDEX idx_oportunidades_propietario   ON oportunidades(propietario_id);
CREATE INDEX idx_oportunidades_sbu           ON oportunidades(sbu_id);
CREATE INDEX idx_oportunidades_producto      ON oportunidades(producto_id);
CREATE INDEX idx_oportunidades_fecha_creacion ON oportunidades(fecha_creacion);
CREATE INDEX idx_oportunidades_importe       ON oportunidades(importe);
CREATE INDEX idx_oportunidades_external_id   ON oportunidades(external_id);

-- =============================================================================
-- TABLA: alertas
-- =============================================================================

CREATE TABLE alertas (
    id               UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    titulo           VARCHAR(200) NOT NULL,
    descripcion      TEXT,
    nivel            nivel_alerta NOT NULL DEFAULT 'seguimiento',
    oportunidad_id   UUID         REFERENCES oportunidades(id) ON DELETE CASCADE,
    usuario_id       UUID         REFERENCES usuarios(id) ON DELETE SET NULL,
    resuelta         BOOLEAN      NOT NULL DEFAULT FALSE,
    resuelta_en      TIMESTAMPTZ,
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    actualizado_en   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_alertas_actualizado_en
    BEFORE UPDATE ON alertas
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_alertas_nivel        ON alertas(nivel);
CREATE INDEX idx_alertas_usuario_id   ON alertas(usuario_id);
CREATE INDEX idx_alertas_resuelta     ON alertas(resuelta);

-- =============================================================================
-- TABLA: sesiones_audio (Voice Studio)
-- =============================================================================

CREATE TABLE sesiones_audio (
    id                    UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id            UUID         NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    propietario_objetivo  UUID         REFERENCES usuarios(id) ON DELETE SET NULL,
    foco                  VARCHAR(50)  NOT NULL,  -- pipeline | alertas | productos | acciones
    duracion_min          SMALLINT     NOT NULL,
    script                TEXT         NOT NULL,
    num_palabras          INTEGER,
    duracion_estimada_seg INTEGER,
    notas                 TEXT,
    creado_en             TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sesiones_audio_usuario_id ON sesiones_audio(usuario_id);

-- =============================================================================
-- TABLA: conversaciones_ia (IA Copilot)
-- =============================================================================

CREATE TABLE conversaciones_ia (
    id             UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id     UUID        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    mensajes       JSONB       NOT NULL DEFAULT '[]',  -- [{role, content}]
    tokens_usados  INTEGER     NOT NULL DEFAULT 0,
    creado_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_conversaciones_ia_actualizado_en
    BEFORE UPDATE ON conversaciones_ia
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_conversaciones_ia_usuario_id ON conversaciones_ia(usuario_id);

-- =============================================================================
-- TABLA: importaciones (log de importaciones CSV)
-- =============================================================================

CREATE TABLE importaciones (
    id               UUID              PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id       UUID              NOT NULL REFERENCES usuarios(id) ON DELETE SET NULL,
    nombre_archivo   VARCHAR(255)      NOT NULL,
    modo             VARCHAR(20)       NOT NULL,  -- append | upsert | replace_all
    estado           estado_importacion NOT NULL DEFAULT 'procesando',
    total_filas      INTEGER           NOT NULL DEFAULT 0,
    filas_procesadas INTEGER           NOT NULL DEFAULT 0,
    filas_creadas    INTEGER           NOT NULL DEFAULT 0,
    filas_actualizadas INTEGER         NOT NULL DEFAULT 0,
    filas_error      INTEGER           NOT NULL DEFAULT 0,
    errores          JSONB             NOT NULL DEFAULT '[]',
    creado_en        TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
    actualizado_en   TIMESTAMPTZ       NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_importaciones_actualizado_en
    BEFORE UPDATE ON importaciones
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

CREATE INDEX idx_importaciones_usuario_id ON importaciones(usuario_id);
CREATE INDEX idx_importaciones_estado     ON importaciones(estado);

-- =============================================================================
-- TABLA: audit_log
-- =============================================================================

CREATE TABLE audit_log (
    id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id    UUID        REFERENCES usuarios(id) ON DELETE SET NULL,
    accion        VARCHAR(20) NOT NULL,   -- INSERT | UPDATE | DELETE
    tabla         VARCHAR(50) NOT NULL,
    registro_id   UUID,
    valor_anterior JSONB,
    valor_nuevo    JSONB,
    ip_origen     INET,
    creado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_usuario_id  ON audit_log(usuario_id);
CREATE INDEX idx_audit_log_tabla       ON audit_log(tabla);
CREATE INDEX idx_audit_log_registro_id ON audit_log(registro_id);
CREATE INDEX idx_audit_log_creado_en   ON audit_log(creado_en);

-- =============================================================================
-- FUNCIÓN: calcular_win_rate
-- =============================================================================

CREATE OR REPLACE FUNCTION calcular_win_rate(
    p_propietario_id UUID DEFAULT NULL,
    p_producto_id    UUID DEFAULT NULL,
    p_sbu_id         UUID DEFAULT NULL
)
RETURNS NUMERIC AS $$
DECLARE
    v_ganadas  INTEGER;
    v_perdidas INTEGER;
BEGIN
    SELECT
        COUNT(*) FILTER (WHERE etapa = 'closed_won'),
        COUNT(*) FILTER (WHERE etapa IN ('closed_won', 'closed_lost'))
    INTO v_ganadas, v_perdidas
    FROM oportunidades
    WHERE eliminado_en IS NULL
      AND (p_propietario_id IS NULL OR propietario_id = p_propietario_id)
      AND (p_producto_id    IS NULL OR producto_id    = p_producto_id)
      AND (p_sbu_id         IS NULL OR sbu_id         = p_sbu_id);

    IF v_perdidas = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((v_ganadas::NUMERIC / v_perdidas) * 100, 1);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VISTA MATERIALIZADA: mv_kpis_pipeline
-- KPIs globales del dashboard — se refresca tras cada importación
-- =============================================================================

CREATE MATERIALIZED VIEW mv_kpis_pipeline AS
SELECT
    COUNT(*)                                                        AS total_oportunidades,
    COUNT(*) FILTER (WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn'))
                                                                    AS oportunidades_activas,
    COUNT(*) FILTER (WHERE etapa = 'closed_won')                    AS oportunidades_ganadas,
    COUNT(*) FILTER (WHERE etapa = 'closed_lost')                   AS oportunidades_perdidas,

    COALESCE(SUM(importe), 0)                                       AS pipeline_total,
    COALESCE(SUM(importe) FILTER (
        WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
    ), 0)                                                           AS pipeline_activo,
    COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_won'), 0)   AS importe_ganado,
    COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_lost'), 0)  AS importe_perdido,

    COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 0)   AS ticket_medio_ganado,

    calcular_win_rate()                                             AS win_rate_global,

    NOW()                                                           AS calculado_en
FROM oportunidades
WHERE eliminado_en IS NULL;

CREATE UNIQUE INDEX idx_mv_kpis_pipeline ON mv_kpis_pipeline(calculado_en);

-- =============================================================================
-- VISTA MATERIALIZADA: mv_pipeline_por_etapa
-- Pipeline agrupado por etapa para el funnel del dashboard
-- =============================================================================

CREATE MATERIALIZED VIEW mv_pipeline_por_etapa AS
SELECT
    etapa,
    COUNT(*)            AS num_oportunidades,
    SUM(importe)        AS importe_total,
    AVG(importe)        AS importe_medio
FROM oportunidades
WHERE eliminado_en IS NULL
  AND etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
GROUP BY etapa
ORDER BY importe_total DESC;

CREATE UNIQUE INDEX idx_mv_pipeline_por_etapa ON mv_pipeline_por_etapa(etapa);

-- =============================================================================
-- POLÍTICAS RLS (producción — Supabase)
-- En local están definidas pero RLS no está activado por tabla
-- =============================================================================

-- Comercial: solo ve sus propias oportunidades
-- Manager: ve las de su equipo completo
-- Admin: acceso total
--
-- CREATE POLICY "ver_propias_oportunidades" ON oportunidades
--   FOR SELECT USING (
--     auth.uid() = propietario_id
--     OR EXISTS (
--       SELECT 1 FROM usuarios
--       WHERE id = auth.uid() AND rol IN ('admin', 'manager')
--     )
--   );
--
-- CREATE POLICY "ver_equipo_oportunidades" ON oportunidades
--   FOR SELECT USING (
--     propietario_id IN (
--       SELECT id FROM usuarios WHERE manager_id = auth.uid()
--     )
--     OR auth.uid() = propietario_id
--   );

-- =============================================================================
-- Seed de usuarios/SBU/productos se gestiona en 010_seed_mvp.sql
-- para evitar conflictos entre IDs aleatorios y IDs fijos del dataset demo.
-- =============================================================================
