"""
Router del módulo Reuniones.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.reuniones import servicio
from app.modules.reuniones.schemas import FichaReunionRespuesta, PreguntasReunionRespuesta

router = APIRouter(prefix="/reuniones", tags=["reuniones"])


@router.get("/preparar/{cuenta_id}", response_model=FichaReunionRespuesta)
async def preparar_reunion(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ficha = await servicio.construir_ficha_reunion(conexion, cuenta_id)
    if not ficha:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada.")
    return ficha


@router.post("/preguntas/{cuenta_id}", response_model=PreguntasReunionRespuesta)
async def generar_preguntas(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        preguntas = await servicio.generar_preguntas_recomendadas(conexion, cuenta_id)
        return {"preguntas": preguntas}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
