"""
Lógica de negocio del Pipeline — CRUD de oportunidades y funnel.
"""

from uuid import UUID

import asyncpg

from app.modules.scoring import servicio as scoring_servicio
from app.shared.modelos import OportunidadActualizar, OportunidadCrear


async def listar_oportunidades(
    conexion: asyncpg.Connection,
    propietario_id: UUID | None,
    etapa: str | None,
    pagina: int,
    por_pagina: int,
    sort_by: str = "fecha_creacion",
    sort_dir: str = "desc",
) -> dict:
    condiciones = ["eliminado_en IS NULL"]
    params: list = []
    n = 1

    if propietario_id:
        condiciones.append(f"propietario_id = ${n}")
        params.append(propietario_id)
        n += 1
    if etapa:
        condiciones.append(f"etapa = ${n}")
        params.append(etapa)
        n += 1

    where = "WHERE " + " AND ".join(condiciones)
    offset = (pagina - 1) * por_pagina
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    ordenes_validos = {
        "nombre": "nombre",
        "importe": "importe",
        "etapa": "etapa",
        "fecha_creacion": "fecha_creacion",
        "fecha_decision": "fecha_decision",
    }
    campo_orden = ordenes_validos.get(sort_by.lower(), "fecha_creacion")

    total = await conexion.fetchval(
        f"SELECT COUNT(*) FROM oportunidades {where}", *params
    )
    filas = await conexion.fetch(
        f"""
        SELECT id, nombre, importe, etapa, fecha_creacion, fecha_decision
        FROM oportunidades {where}
        ORDER BY {campo_orden} {direccion} NULLS LAST, id DESC
        LIMIT ${n} OFFSET ${n+1}
        """,
        *params, por_pagina, offset,
    )
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [dict(f) for f in filas],
    }


async def obtener_funnel(
    conexion: asyncpg.Connection,
    propietario_id: UUID | None = None,
) -> list[dict]:
    if propietario_id is None:
        filas = await conexion.fetch("SELECT * FROM mv_pipeline_por_etapa")
        return [dict(f) for f in filas]

    filas = await conexion.fetch(
        """
        SELECT
            etapa,
            COUNT(*)                 AS num_oportunidades,
            COALESCE(SUM(importe), 0) AS importe_total,
            COALESCE(AVG(importe), 0) AS importe_medio
        FROM oportunidades
        WHERE eliminado_en IS NULL
          AND propietario_id = $1
          AND etapa NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
        GROUP BY etapa
        ORDER BY importe_total DESC
        """,
        propietario_id,
    )
    return [dict(f) for f in filas]


async def obtener_oportunidad(
    conexion: asyncpg.Connection,
    oportunidad_id: UUID,
    propietario_id_scope: UUID | None = None,
) -> dict | None:
    condicion_propietario = ""
    params: list = [oportunidad_id]
    if propietario_id_scope:
        condicion_propietario = " AND o.propietario_id = $2"
        params.append(propietario_id_scope)

    fila = await conexion.fetchrow(f"""
        SELECT
            o.id, o.external_id, o.nombre, o.importe, o.etapa, o.tipo,
            o.cuenta_id, o.producto_id,
            o.linea_negocio, o.canal_venta,
            o.fecha_creacion::TEXT AS fecha_creacion,
            o.fecha_decision::TEXT AS fecha_decision,
            o.creado_en::TEXT AS creado_en,
            o.actualizado_en::TEXT AS actualizado_en,
            c.nombre AS cuenta_nombre,
            u.nombre_completo AS propietario_nombre,
            s.nombre AS sbu_nombre,
            p.nombre AS producto_nombre
        FROM oportunidades o
        LEFT JOIN cuentas c   ON c.id = o.cuenta_id
        LEFT JOIN usuarios u  ON u.id = o.propietario_id
        LEFT JOIN sbu s       ON s.id = o.sbu_id
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.id = $1 AND o.eliminado_en IS NULL {condicion_propietario}
    """, *params)
    return dict(fila) if fila else None


async def crear_oportunidad(
    conexion: asyncpg.Connection,
    datos: OportunidadCrear,
    propietario_id: UUID,
) -> dict:
    fila = await conexion.fetchrow(
        """
        INSERT INTO oportunidades
            (nombre, importe, etapa, fecha_creacion, fecha_decision,
             linea_negocio, canal_venta, tipo,
             cuenta_id, propietario_id, sbu_id, producto_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING *
        """,
        datos.nombre, datos.importe, datos.etapa, datos.fecha_creacion,
        datos.fecha_decision, datos.linea_negocio, datos.canal_venta, datos.tipo,
        datos.cuenta_id, datos.propietario_id or propietario_id,
        datos.sbu_id, datos.producto_id,
    )
    return dict(fila)


async def actualizar_oportunidad(
    conexion: asyncpg.Connection,
    oportunidad_id: UUID,
    datos: OportunidadActualizar,
) -> dict | None:
    campos = datos.model_dump(exclude_none=True)
    if not campos:
        return await obtener_oportunidad(conexion, oportunidad_id)

    recalcular_score = "etapa" in campos or "importe" in campos
    asignaciones = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(campos))
    valores = list(campos.values())

    fila = await conexion.fetchrow(
        f"UPDATE oportunidades SET {asignaciones} WHERE id = $1 AND eliminado_en IS NULL RETURNING *",
        oportunidad_id, *valores,
    )
    if not fila:
        return None

    if recalcular_score:
        await scoring_servicio.recalcular_oportunidad(conexion, oportunidad_id)

    return dict(fila)


async def eliminar_oportunidad(conexion: asyncpg.Connection, oportunidad_id: UUID) -> bool:
    resultado = await conexion.execute(
        "UPDATE oportunidades SET eliminado_en = NOW() WHERE id = $1 AND eliminado_en IS NULL",
        oportunidad_id,
    )
    return resultado == "UPDATE 1"
