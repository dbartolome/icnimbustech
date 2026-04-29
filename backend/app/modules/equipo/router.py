"""
Endpoints del módulo Equipo.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import UsuarioAutenticado, requerir_rol
from app.database import obtener_conexion
from app.modules.equipo import servicio

router = APIRouter(prefix="/equipo", tags=["equipo"])


@router.get("/ranking")
async def ranking(
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor")),
    conexion=Depends(obtener_conexion),
):
    return await servicio.obtener_ranking(conexion)


@router.get("/{propietario_id}/estadisticas")
async def estadisticas(
    propietario_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor")),
    conexion=Depends(obtener_conexion),
):
    datos = await servicio.obtener_estadisticas(conexion, propietario_id)
    if not datos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comercial no encontrado.")
    return datos


@router.get("/{propietario_id}/pipeline")
async def pipeline_comercial(
    propietario_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor")),
    conexion=Depends(obtener_conexion),
):
    return await servicio.obtener_pipeline_comercial(conexion, propietario_id)
