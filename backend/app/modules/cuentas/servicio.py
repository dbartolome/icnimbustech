"""
Lógica de negocio del módulo Mis Cuentas.
"""

from uuid import UUID

import asyncpg

from app.modules.cuentas.schemas import (
    CuentaDetalle, CuentaResumen, ListaCuentas,
    ClienteDetalle, ClienteResumen, ListaClientes, OportunidadEnCliente,
)

_ETAPAS_CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")
_ETAPAS_GANADA = ("closed_won",)
_ETAPAS_PERDIDA_CERRADA = ("closed_won", "closed_lost")


def _resolver_orden(sort_by: str, sort_dir: str) -> tuple[str, str]:
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    campos_validos = {
        "nombre": "c.nombre",
        "total_oportunidades": "total_oportunidades",
        "oportunidades_activas": "oportunidades_activas",
        "pipeline_activo": "pipeline_activo",
        "importe_ganado": "importe_ganado",
        "win_rate": "win_rate",
        "ultima_actividad": "ultima_actividad",
    }
    campo = campos_validos.get(sort_by.lower(), "pipeline_activo")
    return campo, direccion


async def listar_cuentas(
    conexion: asyncpg.Connection,
    propietario_id: UUID | None,
    busqueda: str | None,
    pagina: int,
    por_pagina: int,
    sort_by: str = "pipeline_activo",
    sort_dir: str = "desc",
) -> ListaCuentas:
    condicion_busqueda = ""
    params: list = []
    n = 1
    condicion_propietario = ""
    if propietario_id:
        params.append(str(propietario_id))
        condicion_propietario = "AND o.propietario_id = $1"
        n = 2

    if busqueda:
        condicion_busqueda = f"AND c.nombre ILIKE ${n}"
        params.append(f"%{busqueda}%")
        n += 1

    base_sql = f"""
        FROM cuentas c
        INNER JOIN oportunidades o ON o.cuenta_id = c.id
        WHERE 1=1
          {condicion_propietario}
          AND o.eliminado_en IS NULL
          AND c.eliminado_en IS NULL
          {condicion_busqueda}
        GROUP BY c.id, c.nombre
    """

    total = await conexion.fetchval(
        f"SELECT COUNT(*) FROM (SELECT c.id {base_sql}) sub",
        *params,
    )

    offset = (pagina - 1) * por_pagina
    campo_orden, direccion_orden = _resolver_orden(sort_by, sort_dir)
    filas = await conexion.fetch(
        f"""
        SELECT
            c.id,
            c.nombre,
            COUNT(o.id)                                                              AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS})             AS oportunidades_activas,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS}), 0) AS pipeline_activo,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)        AS importe_ganado,
            CASE
                WHEN COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) > 0
                THEN ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::NUMERIC
                    / COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) * 100, 1
                )
                ELSE 0
            END AS win_rate,
            MAX(o.fecha_creacion)::TEXT AS ultima_actividad
        {base_sql}
        ORDER BY {campo_orden} {direccion_orden} NULLS LAST, c.nombre ASC
        LIMIT ${n} OFFSET ${n + 1}
        """,
        *params, por_pagina, offset,
    )

    datos = [
        CuentaResumen(
            id=f["id"],
            nombre=f["nombre"],
            total_oportunidades=f["total_oportunidades"],
            oportunidades_activas=f["oportunidades_activas"],
            pipeline_activo=f["pipeline_activo"],
            importe_ganado=f["importe_ganado"],
            win_rate=f["win_rate"],
            ultima_actividad=f["ultima_actividad"],
        )
        for f in filas
    ]

    return ListaCuentas(total=total, pagina=pagina, por_pagina=por_pagina, datos=datos)


async def obtener_cuenta(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    propietario_id: UUID | None,
) -> CuentaDetalle | None:
    condicion_propietario = "AND o.propietario_id = $2" if propietario_id else ""
    args_detalle = [cuenta_id, propietario_id] if propietario_id else [cuenta_id]
    fila = await conexion.fetchrow(
        f"""
        SELECT
            c.id,
            c.nombre,
            COUNT(o.id)                                                              AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS})             AS oportunidades_activas,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS}), 0) AS pipeline_activo,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)        AS importe_ganado,
            CASE
                WHEN COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) > 0
                THEN ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::NUMERIC
                    / COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) * 100, 1
                )
                ELSE 0
            END AS win_rate
        FROM cuentas c
        INNER JOIN oportunidades o ON o.cuenta_id = c.id
        WHERE c.id = $1
          {condicion_propietario}
          AND o.eliminado_en IS NULL
          AND c.eliminado_en IS NULL
        GROUP BY c.id, c.nombre
        """,
        *args_detalle,
    )

    if not fila:
        return None

    condicion_propietario_ops = "AND propietario_id = $2" if propietario_id else ""
    args_ops = [cuenta_id, propietario_id] if propietario_id else [cuenta_id]
    oportunidades = await conexion.fetch(
        f"""
        SELECT id, nombre, importe, etapa::TEXT, fecha_creacion::TEXT, fecha_decision::TEXT
        FROM oportunidades
        WHERE cuenta_id = $1
          {condicion_propietario_ops}
          AND eliminado_en IS NULL
        ORDER BY fecha_creacion DESC
        """,
        *args_ops,
    )

    return CuentaDetalle(
        id=fila["id"],
        nombre=fila["nombre"],
        total_oportunidades=fila["total_oportunidades"],
        oportunidades_activas=fila["oportunidades_activas"],
        pipeline_activo=fila["pipeline_activo"],
        importe_ganado=fila["importe_ganado"],
        win_rate=fila["win_rate"],
        oportunidades=[dict(o) for o in oportunidades],
    )


# ── Vista global (manager / admin) ───────────────────────────────────────────

async def listar_clientes_global(
    conexion: asyncpg.Connection,
    busqueda: str | None,
    propietario_id: UUID | None,
    pagina: int,
    por_pagina: int,
    sort_by: str = "pipeline_activo",
    sort_dir: str = "desc",
) -> ListaClientes:
    params: list = []
    condicion_busqueda = ""
    n = 1

    condicion_propietario = ""
    if propietario_id:
        condicion_propietario = f"AND o.propietario_id = ${n}"
        params.append(propietario_id)
        n += 1

    if busqueda:
        condicion_busqueda = f"AND c.nombre ILIKE ${n}"
        params.append(f"%{busqueda}%")
        n += 1

    base_sql = f"""
        FROM cuentas c
        INNER JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
        WHERE c.eliminado_en IS NULL
          {condicion_propietario}
          {condicion_busqueda}
        GROUP BY c.id, c.nombre
    """

    count_params = params[:]
    total = await conexion.fetchval(
        f"SELECT COUNT(*) FROM (SELECT c.id {base_sql}) sub",
        *count_params,
    )

    offset = (pagina - 1) * por_pagina
    list_params = params + [por_pagina, offset]
    campo_orden, direccion_orden = _resolver_orden(sort_by, sort_dir)

    filas = await conexion.fetch(
        f"""
        SELECT
            c.id,
            c.nombre,
            COUNT(o.id)                                                                  AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS})                 AS oportunidades_activas,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS}), 0) AS pipeline_activo,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)            AS importe_ganado,
            CASE
                WHEN COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) > 0
                THEN ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::NUMERIC
                    / COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) * 100, 1
                )
                ELSE 0
            END                                                                          AS win_rate,
            MAX(o.fecha_creacion)::TEXT                                                  AS ultima_actividad,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT u.nombre_completo), NULL)                   AS comerciales,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT s.nombre), NULL)                            AS sbus
        FROM cuentas c
        INNER JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
        LEFT JOIN usuarios u ON u.id = o.propietario_id
        LEFT JOIN sbu s ON s.id = o.sbu_id
        WHERE c.eliminado_en IS NULL
          {condicion_propietario}
          {condicion_busqueda}
        GROUP BY c.id, c.nombre
        ORDER BY {campo_orden} {direccion_orden} NULLS LAST, c.nombre ASC
        LIMIT ${n} OFFSET ${n + 1}
        """,
        *list_params,
    )

    datos = [
        ClienteResumen(
            id=f["id"],
            nombre=f["nombre"],
            total_oportunidades=f["total_oportunidades"],
            oportunidades_activas=f["oportunidades_activas"],
            pipeline_activo=f["pipeline_activo"],
            importe_ganado=f["importe_ganado"],
            win_rate=f["win_rate"],
            ultima_actividad=f["ultima_actividad"],
            comerciales=list(f["comerciales"] or []),
            sbus=list(f["sbus"] or []),
        )
        for f in filas
    ]

    return ListaClientes(total=total, pagina=pagina, por_pagina=por_pagina, datos=datos)


async def obtener_cliente_global(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    propietario_id: UUID | None = None,
) -> ClienteDetalle | None:
    condicion_propietario = "AND o.propietario_id = $2" if propietario_id else ""
    args = [cuenta_id, propietario_id] if propietario_id else [cuenta_id]
    fila = await conexion.fetchrow(
        f"""
        SELECT
            c.id,
            c.nombre,
            COUNT(o.id)                                                                  AS total_oportunidades,
            COUNT(o.id) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS})                 AS oportunidades_activas,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN {_ETAPAS_CERRADAS}), 0) AS pipeline_activo,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)            AS importe_ganado,
            CASE
                WHEN COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) > 0
                THEN ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::NUMERIC
                    / COUNT(o.id) FILTER (WHERE o.etapa IN {_ETAPAS_PERDIDA_CERRADA}) * 100, 1
                )
                ELSE 0
            END                                                                          AS win_rate,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT u.nombre_completo), NULL)                   AS comerciales,
            ARRAY_REMOVE(ARRAY_AGG(DISTINCT s.nombre), NULL)                            AS sbus
        FROM cuentas c
        INNER JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
        LEFT JOIN usuarios u ON u.id = o.propietario_id
        LEFT JOIN sbu s ON s.id = o.sbu_id
        WHERE c.id = $1
          {condicion_propietario}
          AND c.eliminado_en IS NULL
        GROUP BY c.id, c.nombre
        """,
        *args,
    )

    if not fila:
        return None

    condicion_propietario_ops = "AND o.propietario_id = $2" if propietario_id else ""
    args_ops = [cuenta_id, propietario_id] if propietario_id else [cuenta_id]
    oportunidades = await conexion.fetch(
        """
        SELECT
            o.id, o.nombre, o.importe, o.etapa::TEXT,
            o.fecha_creacion::TEXT, o.fecha_decision::TEXT,
            u.nombre_completo AS propietario_nombre,
            s.nombre          AS sbu_nombre,
            p.nombre          AS producto_nombre
        FROM oportunidades o
        LEFT JOIN usuarios u ON u.id = o.propietario_id
        LEFT JOIN sbu s      ON s.id = o.sbu_id
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.cuenta_id = $1
          AND o.eliminado_en IS NULL
          """ + condicion_propietario_ops + """
        ORDER BY o.fecha_creacion DESC
        """,
        *args_ops,
    )

    return ClienteDetalle(
        id=fila["id"],
        nombre=fila["nombre"],
        total_oportunidades=fila["total_oportunidades"],
        oportunidades_activas=fila["oportunidades_activas"],
        pipeline_activo=fila["pipeline_activo"],
        importe_ganado=fila["importe_ganado"],
        win_rate=fila["win_rate"],
        comerciales=list(fila["comerciales"] or []),
        sbus=list(fila["sbus"] or []),
        oportunidades=[
            OportunidadEnCliente(
                id=o["id"],
                nombre=o["nombre"],
                importe=o["importe"],
                etapa=o["etapa"],
                fecha_creacion=o["fecha_creacion"],
                fecha_decision=o["fecha_decision"],
                propietario_nombre=o["propietario_nombre"],
                sbu_nombre=o["sbu_nombre"],
                producto_nombre=o["producto_nombre"],
            )
            for o in oportunidades
        ],
    )
