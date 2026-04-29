"""Router del módulo de objetivos comerciales."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.objetivos import servicio
from app.modules.objetivos.schemas import (
    ObjetivoComercialCreate,
    ObjetivoComercialRead,
    ObjetivoComercialUpdate,
    ObjetivoDetalleRead,
    ObjetivoSugerenciaRead,
)

router = APIRouter(prefix="/objetivos", tags=["objetivos"])


@router.get("")
async def listar_objetivos(
    estado: str | None = Query(default=None),
    cuenta_id: UUID | None = Query(default=None),
    oportunidad_id: UUID | None = Query(default=None),
    propietario_id: UUID | None = Query(default=None),
    busqueda: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=200),
    sort_by: str = Query(default="score_impacto"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.listar_objetivos(
        conexion,
        usuario_id=UUID(usuario.usuario_id),
        es_manager=usuario.es_manager,
        estado=estado,
        cuenta_id=cuenta_id,
        oportunidad_id=oportunidad_id,
        propietario_id=propietario_id,
        busqueda=busqueda,
        pagina=pagina,
        por_pagina=por_pagina,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.post("", response_model=ObjetivoDetalleRead, status_code=status.HTTP_201_CREATED)
async def crear_objetivo(
    payload: ObjetivoComercialCreate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await servicio.crear_objetivo(
        conexion,
        usuario_id=UUID(usuario.usuario_id),
        payload=payload,
    )


@router.get("/{objetivo_id}", response_model=ObjetivoDetalleRead)
async def detalle_objetivo(
    objetivo_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await servicio.obtener_objetivo(
        conexion,
        objetivo_id=objetivo_id,
        usuario_id=UUID(usuario.usuario_id),
        es_manager=usuario.es_manager,
    )
    if not fila:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo no encontrado.")
    return fila


@router.patch("/{objetivo_id}", response_model=ObjetivoDetalleRead)
async def actualizar_objetivo(
    objetivo_id: UUID,
    payload: ObjetivoComercialUpdate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await servicio.actualizar_objetivo(
        conexion,
        objetivo_id=objetivo_id,
        usuario_id=UUID(usuario.usuario_id),
        es_manager=usuario.es_manager,
        payload=payload,
    )
    if not fila:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo no encontrado.")
    return fila


@router.delete("/{objetivo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_objetivo(
    objetivo_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ok = await servicio.eliminar_objetivo(
        conexion,
        objetivo_id=objetivo_id,
        usuario_id=UUID(usuario.usuario_id),
        es_manager=usuario.es_manager,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo no encontrado.")


@router.post("/sugerir", response_model=list[ObjetivoSugerenciaRead])
async def sugerir_objetivos(
    limite: int = Query(default=20, ge=1, le=100),
    guardar: bool = Query(default=True),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    # La sugerencia es personal: siempre en alcance del usuario autenticado.
    return await servicio.sugerir_objetivos(
        conexion,
        usuario_id=UUID(usuario.usuario_id),
        limite=limite,
        guardar=guardar,
    )


@router.post("/{objetivo_id}/artefactos/{artefacto_id}")
async def vincular_artefacto(
    objetivo_id: UUID,
    artefacto_id: UUID,
    tipo_relacion: str = Query(default="generado"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ok = await servicio.vincular_artefacto(
        conexion,
        objetivo_id=objetivo_id,
        artefacto_id=artefacto_id,
        usuario_id=UUID(usuario.usuario_id),
        es_manager=usuario.es_manager,
        tipo_relacion=tipo_relacion,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo no encontrado.")
    return {"ok": True}
