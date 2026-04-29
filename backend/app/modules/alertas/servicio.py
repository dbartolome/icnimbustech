"""
Lógica de negocio del módulo Alertas.
"""

from uuid import UUID

import asyncpg


async def listar_alertas(conexion: asyncpg.Connection, incluir_resueltas: bool = False) -> list[dict]:
    where = "" if incluir_resueltas else "WHERE a.resuelta = FALSE"
    filas = await conexion.fetch(f"""
        SELECT
            a.id, a.titulo, a.descripcion, a.nivel, a.resuelta,
            a.creado_en::TEXT AS creado_en,
            u.nombre_completo AS usuario_nombre
        FROM alertas a
        LEFT JOIN usuarios u ON u.id = a.usuario_id
        {where}
        ORDER BY
            a.resuelta ASC,
            CASE a.nivel WHEN 'critico' THEN 1 WHEN 'seguimiento' THEN 2 ELSE 3 END,
            a.creado_en DESC
    """)
    return [dict(f) for f in filas]


async def crear_alerta(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    titulo: str,
    descripcion: str | None,
    nivel: str,
) -> dict:
    fila = await conexion.fetchrow("""
        INSERT INTO alertas (usuario_id, titulo, descripcion, nivel)
        VALUES ($1, $2, $3, $4)
        RETURNING id, titulo, descripcion, nivel, resuelta, creado_en::TEXT AS creado_en
    """, usuario_id, titulo, descripcion, nivel)
    return dict(fila)


async def eliminar_alerta(conexion: asyncpg.Connection, alerta_id: UUID) -> bool:
    resultado = await conexion.execute(
        "DELETE FROM alertas WHERE id = $1",
        alerta_id,
    )
    return resultado == "DELETE 1"


async def resolver_alerta(conexion: asyncpg.Connection, alerta_id: UUID) -> bool:
    resultado = await conexion.execute(
        "UPDATE alertas SET resuelta = TRUE, resuelta_en = NOW() WHERE id = $1 AND resuelta = FALSE",
        alerta_id,
    )
    return resultado == "UPDATE 1"
