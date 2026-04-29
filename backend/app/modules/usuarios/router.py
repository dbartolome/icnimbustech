"""
Endpoints de gestión de usuarios (admin only) + endpoint de permisos del usuario actual.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.usuarios.schemas import (
    PermisosUsuario,
    UsuarioCreate,
    UsuarioRead,
    UsuarioUpdate,
)
from app.modules.usuarios.servicio import (
    actualizar_usuario,
    calcular_permisos,
    crear_usuario,
    eliminar_usuario,
    listar_usuarios,
    obtener_usuario,
)

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

_solo_admin = Depends(requerir_rol("admin"))


# =============================================================================
# GET /usuarios/me/permisos  (cualquier usuario autenticado)
# =============================================================================

@router.get("/me/permisos", response_model=PermisosUsuario)
async def permisos_usuario_actual(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    return calcular_permisos(usuario.rol)


# =============================================================================
# GET /usuarios  (admin)
# =============================================================================

@router.get("", response_model=dict)
async def listar(
    rol: str | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=50, ge=1, le=200),
    _: UsuarioAutenticado = _solo_admin,
    conexion=Depends(obtener_conexion),
):
    return await listar_usuarios(
        conexion, rol=rol, busqueda=busqueda, pagina=pagina, por_pagina=por_pagina
    )


# =============================================================================
# GET /usuarios/{id}  (admin)
# =============================================================================

@router.get("/{usuario_id}", response_model=UsuarioRead)
async def obtener(
    usuario_id: UUID,
    _: UsuarioAutenticado = _solo_admin,
    conexion=Depends(obtener_conexion),
):
    usuario = await obtener_usuario(conexion, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return usuario


# =============================================================================
# POST /usuarios  (admin)
# =============================================================================

@router.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def crear(
    datos: UsuarioCreate,
    admin: UsuarioAutenticado = _solo_admin,
    conexion=Depends(obtener_conexion),
):
    try:
        return await crear_usuario(conexion, datos, admin.usuario_id)
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese email.",
            )
        raise


# =============================================================================
# PUT /usuarios/{id}  (admin)
# =============================================================================

@router.put("/{usuario_id}", response_model=UsuarioRead)
async def actualizar(
    usuario_id: UUID,
    datos: UsuarioUpdate,
    admin: UsuarioAutenticado = _solo_admin,
    conexion=Depends(obtener_conexion),
):
    usuario = await actualizar_usuario(conexion, usuario_id, datos, admin.usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
    return usuario


# =============================================================================
# DELETE /usuarios/{id}  (admin)
# =============================================================================

@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    usuario_id: UUID,
    admin: UsuarioAutenticado = _solo_admin,
    conexion=Depends(obtener_conexion),
):
    # No se puede eliminar a uno mismo
    if str(usuario_id) == admin.usuario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes eliminar tu propia cuenta.",
        )
    eliminado = await eliminar_usuario(conexion, usuario_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")
