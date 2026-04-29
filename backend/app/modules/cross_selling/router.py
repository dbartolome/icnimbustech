from __future__ import annotations
from typing import Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.cross_selling import servicio
from app.modules.cross_selling.schemas import CrossSellingItem, CrossSellingListado

router = APIRouter(prefix="/cross-selling", tags=["cross-selling"])


@router.get("", response_model=CrossSellingListado)
async def listar_cuentas(
    busqueda: Optional[str] = Query(None),
    sbu: Optional[str] = Query(None),
    confianza: Optional[str] = Query(None),
    solo_ranking: bool = Query(False),
    _usuario=Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    datos = await servicio.listar_cuentas(
        conexion=conexion,
        busqueda=busqueda,
        sbu=sbu,
        confianza=confianza,
        solo_ranking=solo_ranking,
    )
    return CrossSellingListado(total=len(datos), datos=datos)


@router.get("/{account_name}", response_model=CrossSellingItem)
async def obtener_cuenta(
    account_name: str,
    _usuario=Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    cuenta = await servicio.obtener_cuenta(conexion=conexion, account_name=account_name)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    return cuenta
