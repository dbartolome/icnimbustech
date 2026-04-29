-- ============================================================================
-- MIGRACIÓN 014: Configuración IA persistente (research + ollama URL)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS ia_configuracion (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    research_proveedor VARCHAR(50) NOT NULL DEFAULT 'anthropic',
    research_ollama_url TEXT NOT NULL DEFAULT 'http://localhost:11434',
    research_modelos JSONB NOT NULL DEFAULT '{}'::jsonb,
    research_api_keys JSONB NOT NULL DEFAULT '{}'::jsonb,
    operational_configs JSONB NOT NULL DEFAULT '{}'::jsonb,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO ia_configuracion (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

COMMIT;
