"""
Lógica de negocio del módulo Productos — win rate y volumen por norma.
"""

from uuid import UUID

import asyncpg


def _resolver_orden(sort_by: str, sort_dir: str) -> tuple[str, str]:
    direccion = "ASC" if (sort_dir or "").lower() == "asc" else "DESC"
    campos = {
        "nombre": "p.nombre",
        "total_oportunidades": "total_oportunidades",
        "oportunidades_ganadas": "oportunidades_ganadas",
        "importe_ganado": "importe_ganado",
        "ticket_medio": "ticket_medio",
        "win_rate": "win_rate",
    }
    return campos.get((sort_by or "").lower(), "win_rate"), direccion


async def obtener_analisis(
    conexion: asyncpg.Connection,
    propietario_id: UUID | None = None,
    sort_by: str = "win_rate",
    sort_dir: str = "desc",
) -> list[dict]:
    campo_orden, direccion_orden = _resolver_orden(sort_by, sort_dir)
    if propietario_id is None:
        filas = await conexion.fetch(f"""
            SELECT
                p.id,
                p.nombre,
                COUNT(o.id)                                              AS total_oportunidades,
                COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')       AS oportunidades_ganadas,
                COALESCE(SUM(o.importe) FILTER (
                    WHERE o.etapa = 'closed_won'
                ), 0)                                                    AS importe_ganado,
                COALESCE(AVG(o.importe) FILTER (
                    WHERE o.etapa = 'closed_won'
                ), 0)                                                    AS ticket_medio,
                calcular_win_rate(p_producto_id => p.id)                AS win_rate
            FROM productos p
            LEFT JOIN oportunidades o ON o.producto_id = p.id AND o.eliminado_en IS NULL
            WHERE p.activo = TRUE
            GROUP BY p.id, p.nombre
            ORDER BY {campo_orden} {direccion_orden} NULLS LAST, p.nombre ASC
        """)
        return [dict(f) for f in filas]

    filas = await conexion.fetch(f"""
        SELECT
            p.id,
            p.nombre,
            COUNT(o.id)                                              AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')       AS oportunidades_ganadas,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa = 'closed_won'
            ), 0)                                                    AS importe_ganado,
            COALESCE(AVG(o.importe) FILTER (
                WHERE o.etapa = 'closed_won'
            ), 0)                                                    AS ticket_medio,
            calcular_win_rate(p_producto_id => p.id, p_propietario_id => $1) AS win_rate
        FROM productos p
        LEFT JOIN oportunidades o
          ON o.producto_id = p.id
         AND o.eliminado_en IS NULL
         AND o.propietario_id = $1
        WHERE p.activo = TRUE
        GROUP BY p.id, p.nombre
        ORDER BY {campo_orden} {direccion_orden} NULLS LAST, p.nombre ASC
    """, propietario_id)
    return [dict(f) for f in filas]


async def obtener_oportunidades_producto(
    conexion: asyncpg.Connection,
    producto_id: UUID,
    limit: int = 20,
    propietario_id: UUID | None = None,
) -> list[dict]:
    filtro_prop = " AND o.propietario_id = $3" if propietario_id else ""
    params: list = [producto_id, limit]
    if propietario_id:
        params.append(propietario_id)

    filas = await conexion.fetch(f"""
        SELECT
            o.id, o.nombre, o.importe, o.etapa,
            o.fecha_creacion::TEXT AS fecha_creacion,
            o.fecha_decision::TEXT AS fecha_decision,
            c.id::TEXT AS cuenta_id,
            c.nombre AS cuenta_nombre,
            u.nombre_completo AS propietario_nombre
        FROM oportunidades o
        LEFT JOIN cuentas c  ON c.id = o.cuenta_id
        LEFT JOIN usuarios u ON u.id = o.propietario_id
        WHERE o.producto_id = $1 AND o.eliminado_en IS NULL
        {filtro_prop}
        ORDER BY o.importe DESC
        LIMIT $2
    """, *params)
    return [dict(f) for f in filas]
