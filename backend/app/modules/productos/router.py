"""
Endpoints del módulo Productos.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.productos import servicio

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("/analisis")
async def analisis(
    sort_by: str = Query(default="win_rate"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else None
    return await servicio.obtener_analisis(
        conexion,
        propietario_scope,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{producto_id}/oportunidades")
async def oportunidades_producto(
    producto_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else None
    return await servicio.obtener_oportunidades_producto(conexion, producto_id, limit, propietario_scope)
