"""
Lógica de negocio del módulo Equipo — rankings y estadísticas de comerciales.
"""

from uuid import UUID

import asyncpg


async def obtener_ranking(conexion: asyncpg.Connection) -> list[dict]:
    filas = await conexion.fetch("""
        SELECT
            u.id                                                          AS propietario_id,
            u.nombre_completo,
            COUNT(o.id)                                                   AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')            AS oportunidades_ganadas,
            COUNT(o.id) FILTER (WHERE o.etapa IN ('closed_won','closed_lost')) AS cerradas,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa = 'closed_won'
            ), 0)                                                         AS importe_ganado,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
            ), 0)                                                         AS pipeline_abierto,
            calcular_win_rate(p_propietario_id => u.id)                  AS win_rate
        FROM usuarios u
        LEFT JOIN oportunidades o ON o.propietario_id = u.id AND o.eliminado_en IS NULL
        WHERE u.eliminado_en IS NULL AND u.rol = 'comercial'
        GROUP BY u.id, u.nombre_completo
        ORDER BY importe_ganado DESC
    """)
    return [dict(f) for f in filas]


async def obtener_estadisticas(
    conexion: asyncpg.Connection,
    propietario_id: UUID,
) -> dict | None:
    fila = await conexion.fetchrow("""
        SELECT
            u.id,
            u.nombre_completo,
            u.email,
            COUNT(o.id)                                                   AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')            AS oportunidades_ganadas,
            COUNT(o.id) FILTER (WHERE o.etapa = 'closed_lost')           AS oportunidades_perdidas,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa = 'closed_won'
            ), 0)                                                         AS importe_ganado,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
            ), 0)                                                         AS pipeline_abierto,
            calcular_win_rate(p_propietario_id => u.id)                  AS win_rate
        FROM usuarios u
        LEFT JOIN oportunidades o ON o.propietario_id = u.id AND o.eliminado_en IS NULL
        WHERE u.id = $1 AND u.eliminado_en IS NULL
        GROUP BY u.id, u.nombre_completo, u.email
    """, propietario_id)
    return dict(fila) if fila else None


async def obtener_pipeline_comercial(
    conexion: asyncpg.Connection,
    propietario_id: UUID,
) -> list[dict]:
    filas = await conexion.fetch("""
        SELECT id, nombre, importe, etapa, fecha_creacion, fecha_decision
        FROM oportunidades
        WHERE propietario_id = $1
          AND eliminado_en IS NULL
          AND etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
        ORDER BY importe DESC
        LIMIT 50
    """, propietario_id)
    return [dict(f) for f in filas]
