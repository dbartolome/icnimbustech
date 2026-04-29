"""
Router del módulo Scoring.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.scoring import servicio
from app.modules.scoring.schemas import (
    ScoringCriticoItem,
    ScoringFeedbackCrear,
    ScoringFeedbackRespuesta,
    ScoringRespuesta,
)

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.post("/recalcular")
async def recalcular_todo(
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.recalcular_scores_pipeline(conexion)


@router.get("/criticos", response_model=list[ScoringCriticoItem])
async def listar_criticos(
    umbral: int = Query(default=40, ge=0, le=100),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_scores_criticos(
        conexion=conexion,
        umbral=umbral,
        usuario_id=UUID(usuario.usuario_id),
        es_comercial=usuario.es_comercial,
    )


@router.post("/{oportunidad_id}/feedback", response_model=ScoringFeedbackRespuesta)
async def feedback_score(
    oportunidad_id: UUID,
    payload: ScoringFeedbackCrear,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    resultado = await servicio.registrar_feedback_score(
        conexion=conexion,
        oportunidad_id=oportunidad_id,
        usuario_id=UUID(usuario.usuario_id),
        util=payload.util,
        nota=payload.nota,
    )
    if not resultado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score no encontrado para la oportunidad.")
    return resultado


@router.get("/{oportunidad_id}", response_model=ScoringRespuesta)
async def obtener_score(
    oportunidad_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    score = await servicio.obtener_score(conexion, oportunidad_id)
    if not score:
        recalculado = await servicio.recalcular_oportunidad(conexion, oportunidad_id)
        if not recalculado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Oportunidad no encontrada.")
        return recalculado
    return score
