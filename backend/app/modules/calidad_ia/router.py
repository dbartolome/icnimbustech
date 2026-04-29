"""
Router del módulo Calidad IA.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.calidad_ia import servicio
from app.modules.calidad_ia.schemas import ForzarExportacionCrear, TipoEntregable, ValidacionCalidadRespuesta

router = APIRouter(prefix="/calidad", tags=["calidad"])


@router.get("/validar/{cuenta_id}", response_model=ValidacionCalidadRespuesta)
async def validar(
    cuenta_id: UUID,
    tipo: TipoEntregable = Query(...),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.validar_entregable(
        conexion=conexion,
        cuenta_id=cuenta_id,
        tipo_entregable=tipo,
        usuario_id=UUID(usuario.usuario_id),
    )


@router.get("/historial/{cuenta_id}")
async def historial(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.historial_validaciones(conexion, cuenta_id)


@router.post("/forzar/{cuenta_id}")
async def forzar(
    cuenta_id: UUID,
    payload: ForzarExportacionCrear,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.registrar_forzado(
        conexion=conexion,
        cuenta_id=cuenta_id,
        tipo_entregable=payload.tipo_entregable,
        usuario_id=UUID(usuario.usuario_id),
        motivo=payload.motivo,
    )
