"""
Router del módulo Coaching.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.coaching import servicio

router = APIRouter(prefix="/coaching", tags=["coaching"])


@router.post("/analizar-notas/{cuenta_id}")
async def analizar_notas(
    cuenta_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    if usuario.es_comercial:
        tiene_acceso = await conexion.fetchval(
            """
            SELECT 1
            FROM oportunidades
            WHERE cuenta_id = $1
              AND propietario_id = $2
              AND eliminado_en IS NULL
            LIMIT 1
            """,
            cuenta_id,
            UUID(usuario.usuario_id),
        )
        if not tiene_acceso:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a esta cuenta.")

    return await servicio.analizar_notas_cuenta(conexion, cuenta_id, UUID(usuario.usuario_id))


@router.get("/recomendaciones/{usuario_id}")
async def recomendaciones_usuario(
    usuario_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    if usuario.es_comercial and UUID(usuario.usuario_id) != usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes ver tus recomendaciones.")
    return await servicio.generar_plan_mejora(conexion, usuario_id)


@router.get("/equipo")
async def ver_coaching_equipo(
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.coaching_equipo(conexion)


@router.get("/historial/{usuario_id}")
async def historial(
    usuario_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    if usuario.es_comercial and UUID(usuario.usuario_id) != usuario_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes ver tu historial.")
    return await servicio.historial_usuario(conexion, usuario_id)
