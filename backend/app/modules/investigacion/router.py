"""
Módulo: investigacion

Endpoints para lanzar y consultar investigaciones de empresa.
El trabajo pesado lo hace el InvestigadorWeb en background.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

import asyncpg

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.investigacion import servicio

router = APIRouter(prefix="/investigacion", tags=["investigacion"])


@router.post("/{cuenta_id}", status_code=status.HTTP_202_ACCEPTED)
async def lanzar_investigacion(
    cuenta_id: UUID,
    background: BackgroundTasks,
    forzar: bool = False,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Lanza la investigación de una empresa en background.
    Si ya existe una investigación reciente (< 30 días), la reutiliza salvo forzar=true.
    """
    resultado = await servicio.iniciar_investigacion(cuenta_id, forzar, conexion, background)
    return resultado


@router.get("/{cuenta_id}/estado")
async def estado_investigacion(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Devuelve el estado y datos de la investigación más reciente para una cuenta."""
    inv = await servicio.obtener_investigacion(cuenta_id, conexion)
    if not inv:
        raise HTTPException(status_code=404, detail="Sin investigaciones para esta cuenta")
    return inv


@router.get("/{cuenta_id}/historial")
async def historial_investigaciones(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Lista todas las investigaciones de una cuenta, más recientes primero."""
    return await servicio.listar_investigaciones(cuenta_id, conexion)
