"""
Módulo: propuesta

Endpoints para generar y consultar propuestas comerciales.
El Agente 2 (AnalistaPipeline) trabaja en background con Ollama local.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
import asyncpg

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.propuesta import servicio

router = APIRouter(prefix="/propuesta", tags=["propuesta"])


@router.post("/{cuenta_id}", status_code=status.HTTP_202_ACCEPTED)
async def generar_propuesta(
    cuenta_id: UUID,
    background: BackgroundTasks,
    investigacion_id: str | None = None,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Genera una propuesta comercial para una cuenta en background.
    Si no se indica investigacion_id, usa la más reciente completada.
    Requiere que exista al menos una investigación completada.
    """
    return await servicio.iniciar_propuesta(cuenta_id, investigacion_id, conexion, background)


@router.post("/{cuenta_id}/pipeline-completo", status_code=status.HTTP_202_ACCEPTED)
async def pipeline_completo(
    cuenta_id: UUID,
    background: BackgroundTasks,
    forzar_reinvestigacion: bool = False,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Lanza el pipeline completo: Investigación → Propuesta en un solo paso.
    Si ya hay investigación reciente (< 30 días), la reutiliza.
    """
    return await servicio.iniciar_pipeline_completo(
        cuenta_id, forzar_reinvestigacion, conexion, background
    )


@router.get("/{cuenta_id}")
async def obtener_propuesta(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Devuelve la propuesta comercial más reciente de una cuenta."""
    propuesta = await servicio.obtener_propuesta(cuenta_id, conexion)
    if not propuesta:
        raise HTTPException(status_code=404, detail="Sin propuesta para esta cuenta")
    return propuesta


@router.get("/{cuenta_id}/estado")
async def estado_propuesta(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Estado rápido del último job de propuesta para polling desde el frontend."""
    return await servicio.estado_propuesta(cuenta_id, conexion)
