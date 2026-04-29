-- =============================================================================
-- PROMPT 10 · RBAC
-- Añade rol "supervisor" y crea un usuario inicial.
-- =============================================================================

ALTER TYPE rol_usuario ADD VALUE IF NOT EXISTS 'supervisor';

INSERT INTO public.usuarios (
    id,
    email,
    nombre_completo,
    hash_contrasena,
    rol,
    manager_id,
    activo,
    eliminado_en,
    creado_en,
    actualizado_en,
    nombre_csv
)
VALUES (
    'c3dc3f6f-6c73-4f06-87ab-745af7f54e6f',
    'supervisor.demo@sgs-dev.com',
    'Supervisor Demo',
    '$2b$12$6LCIIppVK9.Nkp3hFnusju22m6dSgyeFlspTbEnZtAvphPTv.IuVq',
    'supervisor',
    NULL,
    true,
    NULL,
    NOW(),
    NOW(),
    NULL
)
ON CONFLICT (email) DO NOTHING;
