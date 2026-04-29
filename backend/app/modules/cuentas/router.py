"""
Router del módulo Mis Cuentas.
Endpoints: listar cuentas propias + detalle de cuenta.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.cuentas import servicio
from app.modules.cuentas.schemas import CuentaDetalle, ListaCuentas, ClienteDetalle, ListaClientes

router = APIRouter(prefix="/cuentas", tags=["cuentas"])


@router.get("", response_model=ListaCuentas)
async def listar_mis_cuentas(
    busqueda: str | None = Query(default=None, max_length=100),
    propietario_id: UUID | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="pipeline_activo"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    return await servicio.listar_cuentas(
        conexion=conexion,
        propietario_id=propietario_scope,
        busqueda=busqueda,
        pagina=pagina,
        por_pagina=por_pagina,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/catalogo", tags=["cuentas"])
async def catalogo_cuentas(
    busqueda: str | None = Query(default=None, max_length=100),
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Lista todos los nombres de cuentas (sin filtro por propietario) para selectores."""
    filtro = f"%{busqueda}%" if busqueda else "%"
    filas = await conexion.fetch(
        """SELECT DISTINCT ON (c.nombre) c.id, c.nombre
           FROM cuentas c
           JOIN oportunidades o ON o.cuenta_id = c.id
           WHERE c.nombre ILIKE $1 AND o.eliminado_en IS NULL
           ORDER BY c.nombre
           LIMIT 300""",
        filtro,
    )
    return [{"id": str(r["id"]), "nombre": r["nombre"]} for r in filas]


@router.get("/global", response_model=ListaClientes, tags=["clientes"])
async def listar_clientes_global(
    busqueda: str | None = Query(default=None, max_length=100),
    propietario_id: UUID | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="pipeline_activo"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Vista global de clientes — solo accesible por supervisor, manager y admin."""
    if usuario.rol not in ("admin", "manager", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo supervisores, managers y administradores pueden ver la lista global de clientes.",
        )
    return await servicio.listar_clientes_global(
        conexion=conexion,
        busqueda=busqueda,
        propietario_id=propietario_id,
        pagina=pagina,
        por_pagina=por_pagina,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/global/{cuenta_id}", response_model=ClienteDetalle, tags=["clientes"])
async def obtener_cliente_global(
    cuenta_id: UUID,
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Detalle completo de un cliente — solo accesible por supervisor, manager y admin."""
    if usuario.rol not in ("admin", "manager", "supervisor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo supervisores, managers y administradores pueden ver el detalle global de clientes.",
        )
    cliente = await servicio.obtener_cliente_global(
        conexion=conexion,
        cuenta_id=cuenta_id,
        propietario_id=propietario_id,
    )
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )
    return cliente


@router.get("/{cuenta_id}", response_model=CuentaDetalle)
async def obtener_detalle_cuenta(
    cuenta_id: UUID,
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    propietario_scope = UUID(usuario.usuario_id) if usuario.es_comercial else propietario_id
    cuenta = await servicio.obtener_cuenta(
        conexion=conexion,
        cuenta_id=cuenta_id,
        propietario_id=propietario_scope,
    )
    if not cuenta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuenta no encontrada o sin oportunidades asignadas.",
        )
    return cuenta
