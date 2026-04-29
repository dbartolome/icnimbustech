"""
Router del módulo Seguimientos.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.seguimientos import servicio
from app.modules.seguimientos.schemas import (
    EstadoSeguimiento,
    SeguimientoActualizar,
    SeguimientoCrear,
    SeguimientoListaRespuesta,
    SeguimientoRespuesta,
)

router = APIRouter(prefix="/seguimientos", tags=["seguimientos"])


@router.get("", response_model=SeguimientoListaRespuesta)
async def listar_seguimientos(
    oportunidad_id: UUID | None = Query(default=None),
    cuenta_id: UUID | None = Query(default=None),
    estado: EstadoSeguimiento | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    datos = await servicio.listar_seguimientos(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
        oportunidad_id=oportunidad_id,
        cuenta_id=cuenta_id,
        estado=estado,
    )
    return {"datos": datos}


@router.post("", response_model=SeguimientoRespuesta, status_code=status.HTTP_201_CREATED)
async def crear_seguimiento(
    payload: SeguimientoCrear,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.crear_seguimiento(
        conexion=conexion,
        datos=payload,
        creado_por=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
    )


@router.put("/{seguimiento_id}", response_model=SeguimientoRespuesta)
async def actualizar_seguimiento(
    seguimiento_id: UUID,
    payload: SeguimientoActualizar,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    seguimiento = await servicio.actualizar_seguimiento(
        conexion=conexion,
        seguimiento_id=seguimiento_id,
        usuario_id=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
        datos=payload,
    )
    if not seguimiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seguimiento no encontrado.",
        )
    return seguimiento


@router.delete("/{seguimiento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_seguimiento(
    seguimiento_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    eliminado = await servicio.eliminar_seguimiento(
        conexion=conexion,
        seguimiento_id=seguimiento_id,
        usuario_id=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
    )
    if not eliminado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seguimiento no encontrado.",
        )


@router.put("/{seguimiento_id}/completar", status_code=status.HTTP_204_NO_CONTENT)
async def completar_seguimiento(
    seguimiento_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    completado = await servicio.completar_seguimiento(
        conexion=conexion,
        seguimiento_id=seguimiento_id,
        usuario_id=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
    )
    if not completado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seguimiento no encontrado o ya completado.",
        )
