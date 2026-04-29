"""Router del módulo Forecast + Cola Cross-sell."""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.database import obtener_conexion
from app.modules.forecast import servicio
from app.modules.forecast.schemas import (
    CrossSellQueueItem,
    ForecastEquipo,
    ForecastResult,
    ForecastSnapshot,
    RealUpdate,
)

router = APIRouter(prefix="/forecast", tags=["forecast"])


# =============================================================================
# Forecast personal
# =============================================================================

@router.get("/me", response_model=ForecastResult)
async def mi_forecast(
    recalcular: bool = Query(default=False),
    propietario_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Forecast a 3 meses del comercial logueado.
    Usa caché de 7 días salvo que recalcular=true.
    """
    uid = UUID(usuario.usuario_id) if usuario.es_comercial else (propietario_id or UUID(usuario.usuario_id))

    if not recalcular:
        cached = await servicio.obtener_snapshot_reciente(conexion, uid)
        if cached:
            return ForecastResult(
                usuario_id=str(cached["usuario_id"]),
                usuario_nombre=cached["usuario_nombre"],
                mes_1=cached["mes_1"],
                mes_2=cached["mes_2"],
                mes_3=cached["mes_3"],
                pipeline_total=float(cached["pipeline_total"]),
                pipeline_maduro=float(cached["pipeline_maduro"]),
                baseline_mediana=float(cached["baseline_mediana"]),
                sbu_dominante=cached["sbu_dominante"],
                wr_sbu=float(cached["wr_sbu"]),
                pesimista={"m1": float(cached["pesimista_m1"]), "m2": float(cached["pesimista_m2"]), "m3": float(cached["pesimista_m3"]), "total": float(cached["pesimista_total"])},
                base={"m1": float(cached["base_m1"]), "m2": float(cached["base_m2"]), "m3": float(cached["base_m3"]), "total": float(cached["base_total"])},
                optimista={"m1": float(cached["optimista_m1"]), "m2": float(cached["optimista_m2"]), "m3": float(cached["optimista_m3"]), "total": float(cached["optimista_total"])},
            )

    forecast = await servicio.calcular_forecast(conexion, uid)
    await servicio.guardar_snapshot(conexion, forecast)
    return ForecastResult(**forecast)


@router.get("/me/historial", response_model=list[ForecastSnapshot])
async def historial_forecast(
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    snapshots = await servicio.listar_snapshots(conexion, UUID(usuario.usuario_id))
    return [ForecastSnapshot(**s) for s in snapshots]


@router.put("/snapshots/{snapshot_id}/real", status_code=status.HTTP_200_OK)
async def registrar_real(
    snapshot_id: UUID,
    datos: RealUpdate,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Registra el importe real cerrado a fin de mes para medir accuracy."""
    actualizado = await servicio.actualizar_real(
        conexion, snapshot_id, UUID(usuario.usuario_id), datos.mes, datos.importe
    )
    if not actualizado:
        raise HTTPException(status_code=404, detail="Snapshot no encontrado.")
    return {"ok": True}


# =============================================================================
# Forecast de equipo (admin / manager)
# =============================================================================

@router.get("/equipo", response_model=ForecastEquipo)
async def forecast_equipo(
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Forecast consolidado del equipo. Admin ve todos; manager/supervisor ven su SBU."""
    if usuario.es_admin:
        # Todos los comerciales activos con oportunidades
        filas = await conexion.fetch("""
            SELECT DISTINCT o.propietario_id AS uid
            FROM oportunidades o
            WHERE o.eliminado_en IS NULL AND o.propietario_id IS NOT NULL
        """)
    else:
        # Solo comerciales de las SBUs asignadas al manager
        filas = await conexion.fetch("""
            SELECT DISTINCT o.propietario_id AS uid
            FROM oportunidades o
            JOIN sbu s ON s.id = o.sbu_id
            JOIN manager_sbus ms ON ms.sbu_id = s.id
            WHERE o.eliminado_en IS NULL
              AND o.propietario_id IS NOT NULL
              AND ms.manager_id = $1
        """, UUID(usuario.usuario_id))

    uids = [f["uid"] for f in filas if f["uid"]]
    resultado = await servicio.calcular_forecast_equipo(conexion, uids)
    return ForecastEquipo(**resultado)


# =============================================================================
# Cola de cross-sell
# =============================================================================

@router.get("/cross-sell-queue", response_model=list[CrossSellQueueItem])
async def mi_cola_cross_sell(
    limit: int = Query(default=10, ge=1, le=50),
    recalcular: bool = Query(default=False),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Cuentas con mayor potencial de cross-sell para el comercial logueado.
    Usa caché semanal; recalcular=true fuerza regeneración.
    """
    uid = UUID(usuario.usuario_id)

    if not recalcular:
        cached = await servicio.obtener_queue_semana(conexion, uid, limit)
        if cached:
            return [CrossSellQueueItem(**c) for c in cached]

    queue = await servicio.build_cross_sell_queue(conexion, uid)

    usuario_row = await conexion.fetchrow(
        "SELECT nombre_completo FROM usuarios WHERE id = $1", uid
    )
    usuario_nombre = usuario_row["nombre_completo"] if usuario_row else ""

    await servicio.guardar_queue(conexion, uid, usuario_nombre, queue)
    return [CrossSellQueueItem(**item) for item in queue[:limit]]
