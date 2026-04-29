"""
Endpoints del módulo Alertas.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.alertas import servicio

router = APIRouter(prefix="/alertas", tags=["alertas"])


class AlertaCrear(BaseModel):
    titulo: str
    descripcion: str | None = None
    nivel: str = "seguimiento"   # critico | seguimiento | oportunidad


@router.get("")
async def listar(
    incluir_resueltas: bool = Query(default=False),
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion=Depends(obtener_conexion),
):
    return await servicio.listar_alertas(conexion, incluir_resueltas)


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear(
    datos: AlertaCrear,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion=Depends(obtener_conexion),
):
    return await servicio.crear_alerta(
        conexion,
        UUID(usuario.usuario_id),
        datos.titulo,
        datos.descripcion,
        datos.nivel,
    )


@router.put("/{alerta_id}/resolver", status_code=status.HTTP_204_NO_CONTENT)
async def resolver(
    alerta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion=Depends(obtener_conexion),
):
    resuelta = await servicio.resolver_alerta(conexion, alerta_id)
    if not resuelta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada o ya resuelta.")


@router.delete("/{alerta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    alerta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion=Depends(obtener_conexion),
):
    eliminado = await servicio.eliminar_alerta(conexion, alerta_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alerta no encontrada.")
