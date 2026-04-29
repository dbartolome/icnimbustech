"""
Endpoints del módulo de artefactos IA unificados.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.artefactos import servicio
from app.modules.artefactos.schemas import (
    ArtefactoDetalleRead,
    ArtefactoRead,
    ArtefactoVersionRead,
    VersionArtefactoCrear,
)

router = APIRouter(prefix="/artefactos", tags=["artefactos"])


@router.get("")
async def listar(
    tipo: str | None = Query(default=None),
    subtipo: str | None = Query(default=None),
    entidad_tipo: str | None = Query(default=None),
    entidad_id: UUID | None = Query(default=None),
    cuenta_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    propietario_id: UUID | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=200),
    sort_by: str = Query(default="actualizado_en"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_artefactos(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
        tipo=tipo,
        subtipo=subtipo,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        cuenta_id=cuenta_id,
        texto=q,
        propietario_id=propietario_id,
        pagina=pagina,
        por_pagina=por_pagina,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/contexto")
async def contexto(
    entidad_tipo: str | None = Query(default=None),
    entidad_id: UUID | None = Query(default=None),
    cuenta_id: UUID | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=100),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.obtener_contexto_relevante(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        cuenta_id=cuenta_id,
        limit=limit,
    )


@router.get("/repositorio")
async def repositorio(
    tipo: str | None = Query(default=None),
    subtipo: str | None = Query(default=None),
    entidad_tipo: str | None = Query(default=None),
    entidad_id: UUID | None = Query(default=None),
    cuenta_id: UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    propietario_id: UUID | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=200),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_repositorio_agrupado(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
        tipo=tipo,
        subtipo=subtipo,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        cuenta_id=cuenta_id,
        q=q,
        propietario_id=propietario_id,
        pagina=pagina,
        por_pagina=por_pagina,
    )


@router.get("/{artefacto_id}", response_model=ArtefactoDetalleRead)
async def detalle(
    artefacto_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await servicio.obtener_artefacto(
        conexion=conexion,
        artefacto_id=artefacto_id,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
    )
    if not fila:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto no encontrado.")
    return fila


@router.get("/{artefacto_id}/versiones", response_model=list[ArtefactoVersionRead])
async def versiones(
    artefacto_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    filas = await servicio.listar_versiones(
        conexion=conexion,
        artefacto_id=artefacto_id,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
    )
    if not filas:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto no encontrado.")
    return filas


@router.post("/{artefacto_id}/versiones", response_model=ArtefactoDetalleRead)
async def crear_version(
    artefacto_id: UUID,
    payload: VersionArtefactoCrear,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await servicio.crear_version_manual(
        conexion=conexion,
        artefacto_id=artefacto_id,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
        payload=payload.model_dump(),
    )
    if not fila:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto no encontrado.")
    return fila


@router.patch("/{artefacto_id}/versiones/{version_num}/actual")
async def marcar_actual(
    artefacto_id: UUID,
    version_num: int,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ok = await servicio.marcar_version_actual(
        conexion=conexion,
        artefacto_id=artefacto_id,
        version_num=version_num,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto/versión no encontrado.")
    return {"ok": True}


@router.delete("/{artefacto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar(
    artefacto_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ok = await servicio.eliminar_artefacto(
        conexion=conexion,
        artefacto_id=artefacto_id,
        usuario_id=UUID(usuario.usuario_id),
        es_admin=not usuario.es_comercial,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto no encontrado.")


@router.get("/{artefacto_id}/blob")
async def blob(
    artefacto_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    try:
        contenido, mime, nombre = await servicio.obtener_blob_artefacto(
            conexion=conexion,
            artefacto_id=artefacto_id,
            usuario_id=UUID(usuario.usuario_id),
            es_admin=not usuario.es_comercial,
        )
    except ValueError as exc:
        if str(exc) in {"artefacto_no_encontrado", "origen_no_encontrado"}:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artefacto no encontrado.")
        if str(exc) == "sin_contenido_previsualizable":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El artefacto no tiene contenido previsualizable.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No se pudo cargar el artefacto.")

    return Response(
        content=contenido,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )
