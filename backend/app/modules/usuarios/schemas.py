"""
Schemas Pydantic para gestión de usuarios (admin only).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr

# =============================================================================
# Permisos calculados por rol
# =============================================================================

class PermisosUsuario(BaseModel):
    ver_equipo: bool
    ver_todos_pipeline: bool
    gestionar_usuarios: bool
    importar_datos: bool
    ver_informes_ejecutivos: bool
    gestionar_alertas: bool


# =============================================================================
# Lectura de usuario
# =============================================================================

class UsuarioRead(BaseModel):
    id: UUID
    email: str
    nombre_completo: str
    rol: Literal["admin", "manager", "supervisor", "comercial"]
    nombre_csv: str | None
    manager_id: UUID | None
    activo: bool
    creado_en: datetime
    sbus_asignados: list[str]  # códigos SBU ["CERT", "TECH", ...]


# =============================================================================
# Creación de usuario (admin only)
# =============================================================================

class UsuarioCreate(BaseModel):
    email: EmailStr
    nombre_completo: str
    contrasena: str
    rol: Literal["admin", "manager", "supervisor", "comercial"] = "comercial"
    nombre_csv: str | None = None
    manager_id: UUID | None = None
    sbus_ids: list[UUID] = []  # solo relevante si rol == "manager"


# =============================================================================
# Actualización de usuario (admin only)
# =============================================================================

class UsuarioUpdate(BaseModel):
    nombre_completo: str | None = None
    rol: Literal["admin", "manager", "supervisor", "comercial"] | None = None
    nombre_csv: str | None = None
    manager_id: UUID | None = None
    activo: bool | None = None
    sbus_ids: list[UUID] | None = None  # reemplaza SBUs asignados
    motivo_cambio_rol: str | None = None  # para audit_role_changes
