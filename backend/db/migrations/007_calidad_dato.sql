-- Módulo C: Calidad del dato
-- 1. Vista ops_clean: oportunidades sin "fantasmas" (importe = 0)
-- 2. Vistas materializadas "limpias" para KPIs sin distorsión
-- 3. Enums controlados de Business Line y Canal de Venta

-- =============================================================================
-- 1. Vista ops_clean
-- Excluye oportunidades con importe = 0 (326 ops fantasma del Salesforce export)
-- =============================================================================

CREATE OR REPLACE VIEW ops_clean AS
SELECT *
FROM oportunidades
WHERE importe > 0
  AND eliminado_en IS NULL;

-- =============================================================================
-- 2. KPIs limpios (sin fantasmas) como vista normal (ligera)
-- Se consulta bajo demanda según el parámetro incluir_fantasmas del endpoint
-- =============================================================================

CREATE OR REPLACE VIEW v_kpis_clean AS
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
    CASE
        WHEN COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE etapa = 'closed_won')::NUMERIC
            / COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) * 100,
            1
        )
        ELSE 0
    END                                                             AS win_rate_global,
    ROUND(
        COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 0), 2
    )                                                               AS ticket_medio_ganado,
    NOW()                                                           AS calculado_en
FROM ops_clean;

-- =============================================================================
-- 3. Enums controlados
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linea_negocio_enum') THEN
        CREATE TYPE linea_negocio_enum AS ENUM (
            'Certification',
            'ESG Solutions',
            'Second Party',
            'Testing',
            'Inspection',
            'Training & Qualification',
            'Product Certification',
            'Customized Assurance',
            'Digital Trust',
            'Healthcare',
            'Food & Retail',
            'Technical Advisory',
            'Government & Sustainability'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'canal_venta_enum') THEN
        CREATE TYPE canal_venta_enum AS ENUM (
            'Directo',
            'Indirecto',
            'Alliance',
            'Online'
        );
    END IF;
END$$;

-- Nota: NO migramos las columnas existentes a enum todavía para no romper la importación.
-- La validación se aplica en capa Pydantic (backend). La migración de columna
-- se hará cuando todos los datos históricos estén normalizados.
