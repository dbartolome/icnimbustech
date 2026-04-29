"""
Router del módulo Mi Perfil.
10 endpoints: perfil, stats, objetivos (CRUD), config notificaciones.
"""

from uuid import UUID

import asyncpg
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

log = structlog.get_logger()

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.perfil import servicio
from app.modules.perfil.schemas import (
    NotificacionesConfig,
    NotificacionesUpdate,
    ObjetivoCreate,
    ObjetivoRead,
    ObjetivoUpdate,
    PerfilRead,
    PerfilStats,
    PerfilUpdate,
)

router = APIRouter(prefix="/perfil", tags=["perfil"])


# ── Perfil propio ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=PerfilRead)
async def obtener_mi_perfil(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        return await servicio.obtener_perfil(UUID(usuario.usuario_id), conexion)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/me", response_model=PerfilRead)
async def actualizar_mi_perfil(
    datos: PerfilUpdate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.actualizar_perfil(UUID(usuario.usuario_id), datos, conexion)


@router.get("/me/stats", response_model=PerfilStats)
async def obtener_mis_stats(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.obtener_stats(UUID(usuario.usuario_id), conexion)


@router.get("/me/exportar-csv")
async def exportar_mi_informacion_csv(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        contenido, nombre_fichero = await servicio.exportar_csv_perfil(
            UUID(usuario.usuario_id), conexion
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    log.info("exportacion_csv", usuario_id=str(usuario.usuario_id), fichero=nombre_fichero)

    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


# ── Resetear cuenta ───────────────────────────────────────────────────────────

@router.delete("/me/reset", status_code=status.HTTP_200_OK)
async def resetear_mi_cuenta(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    resultado = await servicio.resetear_cuenta(UUID(usuario.usuario_id), conexion)
    log.info("cuenta_reseteada", usuario_id=str(usuario.usuario_id), **resultado)
    return resultado


# ── Ver perfil de otro comercial (solo managers/admins) ───────────────────────

@router.get("/{usuario_id}", response_model=PerfilRead)
async def obtener_perfil_comercial(
    usuario_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    if not usuario.es_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo managers y admins pueden ver perfiles de otros usuarios.",
        )
    try:
        return await servicio.obtener_perfil(usuario_id, conexion)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Objetivos ─────────────────────────────────────────────────────────────────

@router.get("/me/objetivos", response_model=list[ObjetivoRead])
async def listar_mis_objetivos(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_objetivos(UUID(usuario.usuario_id), conexion)


@router.post("/me/objetivos", response_model=ObjetivoRead, status_code=status.HTTP_201_CREATED)
async def crear_objetivo(
    datos: ObjetivoCreate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.crear_objetivo(UUID(usuario.usuario_id), datos, conexion)


@router.put("/me/objetivos/{objetivo_id}", response_model=ObjetivoRead)
async def actualizar_objetivo(
    objetivo_id: UUID,
    datos: ObjetivoUpdate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        return await servicio.actualizar_objetivo(
            objetivo_id, UUID(usuario.usuario_id), datos, conexion
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/me/objetivos/{objetivo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_objetivo(
    objetivo_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        await servicio.eliminar_objetivo(objetivo_id, UUID(usuario.usuario_id), conexion)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Config notificaciones ─────────────────────────────────────────────────────

@router.get("/me/notificaciones", response_model=NotificacionesConfig)
async def obtener_config_notificaciones(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.obtener_config_notificaciones(UUID(usuario.usuario_id), conexion)


@router.put("/me/notificaciones", response_model=NotificacionesConfig)
async def actualizar_config_notificaciones(
    datos: NotificacionesUpdate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.actualizar_config_notificaciones(
        UUID(usuario.usuario_id), datos, conexion
    )
