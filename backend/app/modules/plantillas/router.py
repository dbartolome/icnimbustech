"""
Endpoints del módulo Plantillas de documentación.
Solo admin puede crear/editar/eliminar. Todos los autenticados pueden listar.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.plantillas import servicio

router = APIRouter(prefix="/plantillas", tags=["plantillas"])


class PlantillaCrear(BaseModel):
    nombre: str
    tipo: str  # pdf | pptx | investigacion | propuesta | briefing | informe
    contenido: dict = {}


class PlantillaActualizar(BaseModel):
    nombre: str | None = None
    contenido: dict | None = None
    activa: bool | None = None


@router.get("")
async def listar(
    tipo: str | None = Query(default=None),
    solo_activas: bool = Query(default=True),
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_plantillas(conexion, tipo=tipo, solo_activas=solo_activas)


@router.get("/{plantilla_id}")
async def obtener(
    plantilla_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    plantilla = await servicio.obtener_plantilla(conexion, plantilla_id)
    if not plantilla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
    return plantilla


@router.get("/{plantilla_id}/variables")
async def variables_disponibles(
    plantilla_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    plantilla = await servicio.obtener_plantilla(conexion, plantilla_id)
    if not plantilla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
    return {
        "tipo": plantilla["tipo"],
        "variables": servicio.variables_disponibles(plantilla["tipo"]),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def crear(
    datos: PlantillaCrear,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    tipos_validos = {"pdf", "pptx", "investigacion", "propuesta", "briefing", "informe"}
    if datos.tipo not in tipos_validos:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tipo no válido. Opciones: {tipos_validos}",
        )
    return await servicio.crear_plantilla(
        conexion,
        nombre=datos.nombre,
        tipo=datos.tipo,
        contenido=datos.contenido,
        creado_por=UUID(usuario.usuario_id),
    )


@router.put("/{plantilla_id}")
async def actualizar(
    plantilla_id: UUID,
    datos: PlantillaActualizar,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    plantilla = await servicio.actualizar_plantilla(
        conexion,
        plantilla_id=plantilla_id,
        nombre=datos.nombre,
        contenido=datos.contenido,
        activa=datos.activa,
    )
    if not plantilla:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
    return plantilla


@router.delete("/{plantilla_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    plantilla_id: UUID,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    eliminado = await servicio.eliminar_plantilla(conexion, plantilla_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada.")
