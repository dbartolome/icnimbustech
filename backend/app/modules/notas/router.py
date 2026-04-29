"""
Router del módulo Notas de Voz.
Endpoints: listar, crear, eliminar notas de voz del usuario.
"""

from uuid import UUID

import asyncpg
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.notas import servicio
from app.modules.notas.schemas import NotaCreate, NotaRead

router = APIRouter(prefix="/notas", tags=["notas"])


@router.get("", response_model=dict)
async def listar_mis_notas(
    oportunidad_id: UUID | None = Query(default=None),
    busqueda: str | None = Query(default=None, max_length=200),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_notas(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        oportunidad_id=oportunidad_id,
        busqueda=busqueda,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.post("", response_model=NotaRead, status_code=status.HTTP_201_CREATED)
async def crear_nota(
    datos: NotaCreate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.crear_nota(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        datos=datos,
    )


@router.post("/transcribir-audio", response_model=NotaRead, status_code=status.HTTP_201_CREATED)
async def crear_nota_desde_audio(
    archivo: UploadFile = File(...),
    titulo: str | None = Form(default=None),
    oportunidad_id: UUID | None = Form(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    nombre = (archivo.filename or "audio").lower()
    permitido = (
        archivo.content_type.startswith("audio/")
        if archivo.content_type
        else any(nombre.endswith(ext) for ext in (".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mpeg"))
    )
    if not permitido:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Formato no soportado. Sube un archivo de audio.",
        )

    contenido = await archivo.read()
    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    try:
        transcripcion = await servicio.transcribir_audio_openai(
            contenido=contenido,
            nombre_fichero=archivo.filename or "audio",
            content_type=archivo.content_type,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    titulo_final = (titulo or "").strip() or f"Transcripción {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    datos = NotaCreate(
        titulo=titulo_final,
        transcripcion=transcripcion,
        oportunidad_id=oportunidad_id,
    )
    return await servicio.crear_nota(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        datos=datos,
    )


@router.delete("/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_nota(
    nota_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    eliminada = await servicio.eliminar_nota(
        conexion=conexion,
        nota_id=nota_id,
        usuario_id=UUID(usuario.usuario_id),
    )
    if not eliminada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada.",
        )
