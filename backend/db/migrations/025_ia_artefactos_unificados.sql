-- =============================================================================
-- Migración 025 — Modelo unificado de artefactos IA con versionado y trazabilidad
-- =============================================================================

CREATE TABLE IF NOT EXISTS ia_artefactos (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tipo               VARCHAR(40) NOT NULL,         -- chat | informe | documento | audio | resumen
    subtipo            VARCHAR(80) NOT NULL,         -- copilot | ejecutivo_mensual | pdf | pptx | briefing...
    entidad_tipo       VARCHAR(40),                  -- cuenta | cliente | producto | oportunidad | comercial
    entidad_id         UUID,
    cuenta_id          UUID REFERENCES cuentas(id) ON DELETE SET NULL,
    usuario_id         UUID NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    titulo             VARCHAR(300) NOT NULL,
    estado             VARCHAR(30) NOT NULL DEFAULT 'activo',
    version_actual     INTEGER NOT NULL DEFAULT 1,
    origen_tabla       VARCHAR(80),
    origen_id          TEXT,
    metadatos          JSONB NOT NULL DEFAULT '{}',
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en     TIMESTAMPTZ NOT NULL DEFAULT now(),
    eliminado_en       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_ia_artefactos_usuario ON ia_artefactos(usuario_id);
CREATE INDEX IF NOT EXISTS idx_ia_artefactos_tipo ON ia_artefactos(tipo, subtipo);
CREATE INDEX IF NOT EXISTS idx_ia_artefactos_entidad ON ia_artefactos(entidad_tipo, entidad_id);
CREATE INDEX IF NOT EXISTS idx_ia_artefactos_cuenta ON ia_artefactos(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_ia_artefactos_actualizado ON ia_artefactos(actualizado_en DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ia_artefactos_origen
    ON ia_artefactos(origen_tabla, origen_id)
    WHERE origen_tabla IS NOT NULL AND origen_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS ia_artefacto_versiones (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artefacto_id       UUID NOT NULL REFERENCES ia_artefactos(id) ON DELETE CASCADE,
    version_num        INTEGER NOT NULL,
    es_actual          BOOLEAN NOT NULL DEFAULT TRUE,
    prompt             TEXT,
    resultado_texto    TEXT,
    resultado_json     JSONB NOT NULL DEFAULT '{}',
    storage_key        TEXT,
    modelo             VARCHAR(140),
    plantilla_id       UUID,
    metadatos          JSONB NOT NULL DEFAULT '{}',
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (artefacto_id, version_num)
);

CREATE INDEX IF NOT EXISTS idx_ia_artefacto_versiones_artefacto ON ia_artefacto_versiones(artefacto_id, version_num DESC);
CREATE INDEX IF NOT EXISTS idx_ia_artefacto_versiones_actual ON ia_artefacto_versiones(artefacto_id, es_actual);

CREATE TABLE IF NOT EXISTS ia_artefacto_fuentes (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id           UUID NOT NULL REFERENCES ia_artefacto_versiones(id) ON DELETE CASCADE,
    fuente_artefacto_id  UUID REFERENCES ia_artefactos(id) ON DELETE SET NULL,
    fuente_tipo          VARCHAR(40) NOT NULL DEFAULT 'artefacto', -- artefacto | documento | nota_manual
    fuente_ref           TEXT,
    peso                 NUMERIC(5, 2),
    creado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ia_artefacto_fuentes_version ON ia_artefacto_fuentes(version_id);
CREATE INDEX IF NOT EXISTS idx_ia_artefacto_fuentes_artefacto ON ia_artefacto_fuentes(fuente_artefacto_id);

CREATE TABLE IF NOT EXISTS ia_artefacto_auditoria (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artefacto_id     UUID NOT NULL REFERENCES ia_artefactos(id) ON DELETE CASCADE,
    version_id       UUID REFERENCES ia_artefacto_versiones(id) ON DELETE SET NULL,
    usuario_id       UUID REFERENCES usuarios(id) ON DELETE SET NULL,
    accion           VARCHAR(40) NOT NULL, -- crear | versionar | marcar_actual | eliminar
    detalle          JSONB NOT NULL DEFAULT '{}',
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ia_artefacto_auditoria_artefacto ON ia_artefacto_auditoria(artefacto_id, creado_en DESC);

DO $$
BEGIN
    IF to_regclass('public.plantillas_documentacion') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_ia_artefacto_versiones_plantilla_documentacion'
        ) THEN
            ALTER TABLE ia_artefacto_versiones
            ADD CONSTRAINT fk_ia_artefacto_versiones_plantilla_documentacion
            FOREIGN KEY (plantilla_id) REFERENCES plantillas_documentacion(id) ON DELETE SET NULL;
        END IF;
    ELSIF to_regclass('public.plantillas_documentos') IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'fk_ia_artefacto_versiones_plantilla_documentos'
        ) THEN
            ALTER TABLE ia_artefacto_versiones
            ADD CONSTRAINT fk_ia_artefacto_versiones_plantilla_documentos
            FOREIGN KEY (plantilla_id) REFERENCES plantillas_documentos(id) ON DELETE SET NULL;
        END IF;
    END IF;
END $$;

CREATE OR REPLACE FUNCTION ia_actualizar_actualizado_en()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ia_artefactos_actualizado_en ON ia_artefactos;
CREATE TRIGGER trg_ia_artefactos_actualizado_en
BEFORE UPDATE ON ia_artefactos
FOR EACH ROW EXECUTE FUNCTION ia_actualizar_actualizado_en();
