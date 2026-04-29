"""
Endpoints del módulo Dashboard.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.dashboard import servicio

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/kpis")
async def kpis(
    incluir_fantasmas: bool = Query(True, description="Incluir oportunidades con importe=0"),
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.obtener_kpis(conexion, incluir_fantasmas, propietario_scope)


@router.get("/evolucion")
async def evolucion_mensual(
    incluir_fantasmas: bool = Query(True),
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.obtener_evolucion_mensual(conexion, incluir_fantasmas, propietario_scope)


@router.get("/sbu")
async def breakdown_sbu(
    incluir_fantasmas: bool = Query(True),
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.obtener_breakdown_sbu(conexion, incluir_fantasmas, propietario_scope)
