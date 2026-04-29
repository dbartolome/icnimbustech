-- =============================================================================
-- Migración 011 — Sistema de Agentes IA
-- Tablas para investigación de empresas y propuestas comerciales.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabla: investigaciones_empresa
-- Resultado del Agente 1 (InvestigadorWeb) — solo información pública.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS investigaciones_empresa (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id                 UUID REFERENCES cuentas(id) ON DELETE CASCADE,
    estado                    TEXT NOT NULL DEFAULT 'pendiente'
                                CHECK (estado IN ('pendiente','procesando','completada','error')),
    -- Datos investigados
    sector                    TEXT,
    num_empleados             TEXT,
    facturacion_estimada      TEXT,
    certificaciones_actuales  JSONB NOT NULL DEFAULT '[]',
    noticias_relevantes       JSONB NOT NULL DEFAULT '[]',
    pain_points               JSONB NOT NULL DEFAULT '[]',
    oportunidades_detectadas  JSONB NOT NULL DEFAULT '[]',
    presencia_web             TEXT,
    fuentes                   JSONB NOT NULL DEFAULT '[]',
    -- Respuesta completa del agente (para debugging y re-proceso)
    raw_research              TEXT,
    error_msg                 TEXT,
    -- Metadata
    modelo_usado              TEXT DEFAULT 'claude-sonnet-4-20250514',
    iniciado_en               TIMESTAMPTZ,
    completado_en             TIMESTAMPTZ,
    creado_en                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_investigaciones_cuenta ON investigaciones_empresa(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_investigaciones_estado ON investigaciones_empresa(estado);

DROP TRIGGER IF EXISTS trg_investigaciones_actualizado_en ON investigaciones_empresa;
CREATE TRIGGER trg_investigaciones_actualizado_en
    BEFORE UPDATE ON investigaciones_empresa
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();

-- -----------------------------------------------------------------------------
-- Tabla: propuestas_comerciales
-- Resultado del Agente 2 (AnalistaPipeline) — datos confidenciales procesados
-- por Ollama local. NUNCA generados por Claude online.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS propuestas_comerciales (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id               UUID REFERENCES cuentas(id) ON DELETE CASCADE,
    investigacion_id        UUID REFERENCES investigaciones_empresa(id) ON DELETE SET NULL,
    estado                  TEXT NOT NULL DEFAULT 'pendiente'
                              CHECK (estado IN ('pendiente','procesando','completada','error')),
    -- Análisis generado por Ollama
    productos_recomendados  JSONB NOT NULL DEFAULT '[]',
    -- [{producto, score_fit, argumentario, norma}]
    escenario_optimista     JSONB,
    -- {importe, productos[], probabilidad, plazo_meses}
    escenario_medio         JSONB,
    escenario_pesimista     JSONB,
    plan_de_accion          JSONB NOT NULL DEFAULT '[]',
    -- [{accion, prioridad, tipo: nuevo|renovacion|upselling, plazo_dias}]
    argumentario_general    TEXT,
    -- Metadata del proceso
    modelo_usado            TEXT,
    error_msg               TEXT,
    iniciado_en             TIMESTAMPTZ,
    completado_en           TIMESTAMPTZ,
    creado_en               TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_propuestas_cuenta      ON propuestas_comerciales(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_propuestas_estado      ON propuestas_comerciales(estado);
CREATE INDEX IF NOT EXISTS idx_propuestas_investigacion ON propuestas_comerciales(investigacion_id);

DROP TRIGGER IF EXISTS trg_propuestas_actualizado_en ON propuestas_comerciales;
CREATE TRIGGER trg_propuestas_actualizado_en
    BEFORE UPDATE ON propuestas_comerciales
    FOR EACH ROW EXECUTE FUNCTION actualizar_actualizado_en();
