-- Migración 020: añadir columnas faltantes a conversaciones_ia
-- Las columnas cuenta_id, rol_usuario y respuesta son requeridas
-- por guardar_conversacion() y listar_conversaciones() pero no estaban en el esquema inicial.

ALTER TABLE conversaciones_ia
  ADD COLUMN IF NOT EXISTS cuenta_id   UUID        REFERENCES cuentas(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS rol_usuario TEXT        NOT NULL DEFAULT 'comercial',
  ADD COLUMN IF NOT EXISTS respuesta   TEXT        NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_conversaciones_ia_cuenta_id ON conversaciones_ia(cuenta_id);
