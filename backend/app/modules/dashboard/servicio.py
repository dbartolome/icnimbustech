"""
Lógica de negocio del Dashboard — KPIs, evolución mensual y breakdown por SBU.
"""

import asyncpg
from uuid import UUID


async def obtener_kpis(
    conexion: asyncpg.Connection,
    incluir_fantasmas: bool = True,
    propietario_id: UUID | None = None,
) -> dict:
    """KPIs globales. Sin fantasmas usa v_kpis_clean (importe > 0)."""
    if propietario_id is None and incluir_fantasmas:
        fila = await conexion.fetchrow("SELECT * FROM mv_kpis_pipeline")
    elif propietario_id is None:
        fila = await conexion.fetchrow("SELECT * FROM v_kpis_clean")
    else:
        filtro_importe = "" if incluir_fantasmas else "AND importe > 0"
        fila = await conexion.fetchrow(
            f"""
            SELECT
                COUNT(*)                                                        AS total_oportunidades,
                COUNT(*) FILTER (WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn'))
                                                                                AS oportunidades_activas,
                COUNT(*) FILTER (WHERE etapa = 'closed_won')                    AS oportunidades_ganadas,
                COUNT(*) FILTER (WHERE etapa = 'closed_lost')                   AS oportunidades_perdidas,
                COALESCE(SUM(importe), 0)                                       AS pipeline_total,
                COALESCE(SUM(importe) FILTER (
                    WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                ), 0)                                                           AS pipeline_activo,
                COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_won'), 0)   AS importe_ganado,
                COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_lost'), 0)  AS importe_perdido,
                ROUND(
                    COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 0), 2
                )                                                               AS ticket_medio_ganado,
                CASE
                    WHEN COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) > 0
                    THEN ROUND(
                        COUNT(*) FILTER (WHERE etapa = 'closed_won')::NUMERIC
                        / COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) * 100, 1
                    )
                    ELSE 0
                END                                                             AS win_rate_global,
                NOW()                                                           AS calculado_en
            FROM oportunidades
            WHERE eliminado_en IS NULL
              AND propietario_id = $1
              {filtro_importe}
            """,
            propietario_id,
        )
    if not fila:
        return {}
    resultado = dict(fila)
    resultado["modo"] = "con_fantasmas" if incluir_fantasmas else "sin_fantasmas"
    return resultado


async def obtener_evolucion_mensual(
    conexion: asyncpg.Connection,
    incluir_fantasmas: bool = True,
    propietario_id: UUID | None = None,
) -> list[dict]:
    """Oportunidades creadas vs ganadas agrupadas por mes."""
    if propietario_id is None:
        tabla = "oportunidades WHERE eliminado_en IS NULL" if incluir_fantasmas else "ops_clean"
        filas = await conexion.fetch(f"""
            SELECT
                TO_CHAR(fecha_creacion, 'YYYY-MM') AS mes,
                COUNT(*)                           AS total_creadas,
                COUNT(*) FILTER (WHERE etapa = 'closed_won') AS ganadas
            FROM {tabla}
            GROUP BY mes
            ORDER BY mes
        """)
    else:
        filtro_importe = "" if incluir_fantasmas else "AND importe > 0"
        filas = await conexion.fetch(
            f"""
            SELECT
                TO_CHAR(fecha_creacion, 'YYYY-MM') AS mes,
                COUNT(*)                           AS total_creadas,
                COUNT(*) FILTER (WHERE etapa = 'closed_won') AS ganadas
            FROM oportunidades
            WHERE eliminado_en IS NULL
              AND propietario_id = $1
              {filtro_importe}
            GROUP BY mes
            ORDER BY mes
            """,
            propietario_id,
        )
    return [dict(f) for f in filas]


async def obtener_breakdown_sbu(
    conexion: asyncpg.Connection,
    incluir_fantasmas: bool = True,
    propietario_id: UUID | None = None,
) -> list[dict]:
    """Pipeline activo, ganado y win rate agrupados por SBU."""
    if propietario_id is None:
        join_cond = (
            "o.sbu_id = s.id AND o.eliminado_en IS NULL"
            if incluir_fantasmas
            else "o.sbu_id = s.id"
        )
        tabla = "oportunidades o" if incluir_fantasmas else "ops_clean o"
        filas = await conexion.fetch(f"""
            SELECT
                s.nombre                                              AS sbu,
                COUNT(o.id)                                          AS total_oportunidades,
                COUNT(o.id) FILTER (
                    WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                )                                                    AS oportunidades_activas,
                COALESCE(SUM(o.importe) FILTER (
                    WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                ), 0)                                                AS pipeline_activo,
                COALESCE(SUM(o.importe) FILTER (
                    WHERE o.etapa = 'closed_won'
                ), 0)                                                AS importe_ganado,
                calcular_win_rate(p_sbu_id => s.id)                  AS win_rate
            FROM sbu s
            LEFT JOIN {tabla} ON {join_cond}
            GROUP BY s.id, s.nombre
            ORDER BY pipeline_activo DESC
        """)
    else:
        filtro_importe = "" if incluir_fantasmas else "AND o.importe > 0"
        filas = await conexion.fetch(
            f"""
            SELECT
                s.nombre                                              AS sbu,
                COUNT(o.id)                                          AS total_oportunidades,
                COUNT(o.id) FILTER (
                    WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                )                                                    AS oportunidades_activas,
                COALESCE(SUM(o.importe) FILTER (
                    WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                ), 0)                                                AS pipeline_activo,
                COALESCE(SUM(o.importe) FILTER (
                    WHERE o.etapa = 'closed_won'
                ), 0)                                                AS importe_ganado,
                calcular_win_rate(p_sbu_id => s.id, p_propietario_id => $1) AS win_rate
            FROM sbu s
            LEFT JOIN oportunidades o
              ON o.sbu_id = s.id
             AND o.eliminado_en IS NULL
             AND o.propietario_id = $1
             {filtro_importe}
            GROUP BY s.id, s.nombre
            ORDER BY pipeline_activo DESC
            """,
            propietario_id,
        )
    return [dict(f) for f in filas]
