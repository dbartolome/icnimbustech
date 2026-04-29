"""
Lógica de negocio del módulo Seguimientos.
"""

from datetime import date
from uuid import UUID

import asyncpg

from app.modules.seguimientos.schemas import SeguimientoActualizar, SeguimientoCrear

_ETAPAS_ACTIVAS = ("estimation_sent", "technically_approved", "in_progress", "discover", "contract_offer_sent", "propose", "estimation_accepted", "negotiate")


async def listar_seguimientos(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    es_comercial: bool,
    oportunidad_id: UUID | None = None,
    cuenta_id: UUID | None = None,
    estado: str | None = None,
) -> list[dict]:
    condiciones = ["1=1"]
    params: list = []
    n = 1

    if oportunidad_id:
        condiciones.append(f"s.oportunidad_id = ${n}")
        params.append(oportunidad_id)
        n += 1
    if cuenta_id:
        condiciones.append(f"s.cuenta_id = ${n}")
        params.append(cuenta_id)
        n += 1
    if estado:
        condiciones.append(f"s.estado = ${n}")
        params.append(estado)
        n += 1
    if es_comercial:
        condiciones.append(f"s.usuario_id = ${n}")
        params.append(usuario_id)

    filas = await conexion.fetch(
        f"""
        SELECT
            s.id, s.oportunidad_id, s.cuenta_id, s.usuario_id, s.creado_por, s.tipo, s.titulo,
            s.descripcion, s.fecha_vencimiento, s.estado, s.completado_en, s.creado_en, s.actualizado_en
        FROM seguimientos s
        WHERE {' AND '.join(condiciones)}
        ORDER BY s.fecha_vencimiento ASC, s.creado_en DESC
        """,
        *params,
    )
    return [dict(fila) for fila in filas]


async def crear_seguimiento(
    conexion: asyncpg.Connection,
    datos: SeguimientoCrear,
    creado_por: UUID,
    es_comercial: bool,
) -> dict:
    usuario_destino = creado_por if es_comercial else (datos.usuario_id or creado_por)

    fila = await conexion.fetchrow(
        """
        INSERT INTO seguimientos (
            oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion, fecha_vencimiento
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        RETURNING
            id, oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion,
            fecha_vencimiento, estado, completado_en, creado_en, actualizado_en
        """,
        datos.oportunidad_id,
        datos.cuenta_id,
        usuario_destino,
        creado_por,
        datos.tipo,
        datos.titulo,
        datos.descripcion,
        datos.fecha_vencimiento,
    )
    return dict(fila)


async def actualizar_seguimiento(
    conexion: asyncpg.Connection,
    seguimiento_id: UUID,
    usuario_id: UUID,
    es_comercial: bool,
    datos: SeguimientoActualizar,
) -> dict | None:
    campos = datos.model_dump(exclude_none=True)
    if not campos:
        return await obtener_seguimiento(conexion, seguimiento_id, usuario_id, es_comercial)

    asignaciones = ", ".join(f"{campo} = ${idx + 2}" for idx, campo in enumerate(campos))
    valores = list(campos.values())

    sql = f"UPDATE seguimientos SET {asignaciones} WHERE id = $1"
    if es_comercial:
        sql += f" AND usuario_id = ${len(valores) + 2}"
        valores.append(usuario_id)
    sql += """
        RETURNING
            id, oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion,
            fecha_vencimiento, estado, completado_en, creado_en, actualizado_en
    """

    fila = await conexion.fetchrow(sql, seguimiento_id, *valores)
    return dict(fila) if fila else None


async def completar_seguimiento(
    conexion: asyncpg.Connection,
    seguimiento_id: UUID,
    usuario_id: UUID,
    es_comercial: bool,
) -> bool:
    sql = """
        UPDATE seguimientos
        SET estado = 'completado', completado_en = NOW()
        WHERE id = $1 AND estado <> 'completado'
    """
    params: list = [seguimiento_id]
    if es_comercial:
        sql += " AND usuario_id = $2"
        params.append(usuario_id)

    resultado = await conexion.execute(sql, *params)
    return resultado == "UPDATE 1"


async def eliminar_seguimiento(
    conexion: asyncpg.Connection,
    seguimiento_id: UUID,
    usuario_id: UUID,
    es_comercial: bool,
) -> bool:
    sql = "DELETE FROM seguimientos WHERE id = $1"
    params: list = [seguimiento_id]
    if es_comercial:
        sql += " AND usuario_id = $2"
        params.append(usuario_id)

    resultado = await conexion.execute(sql, *params)
    return resultado == "DELETE 1"


async def obtener_seguimiento(
    conexion: asyncpg.Connection,
    seguimiento_id: UUID,
    usuario_id: UUID,
    es_comercial: bool,
) -> dict | None:
    sql = """
        SELECT
            id, oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion,
            fecha_vencimiento, estado, completado_en, creado_en, actualizado_en
        FROM seguimientos
        WHERE id = $1
    """
    params: list = [seguimiento_id]
    if es_comercial:
        sql += " AND usuario_id = $2"
        params.append(usuario_id)

    fila = await conexion.fetchrow(sql, *params)
    return dict(fila) if fila else None


async def motor_recordatorios(conexion: asyncpg.Connection) -> dict:
    fecha_hoy = date.today()

    creados_propuesta = await conexion.execute(
        """
        INSERT INTO seguimientos (
            oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion, fecha_vencimiento
        )
        SELECT
            o.id,
            o.cuenta_id,
            o.propietario_id,
            o.propietario_id,
            'proximo_paso',
            'Hacer seguimiento propuesta',
            'Recordatorio automático por oportunidad en etapa propose.',
            CURRENT_DATE + INTERVAL '3 day'
        FROM oportunidades o
        WHERE o.etapa = 'propose'
          AND o.eliminado_en IS NULL
          AND NOT EXISTS (
            SELECT 1
            FROM seguimientos s
            WHERE s.oportunidad_id = o.id
              AND s.estado = 'pendiente'
          )
        """
    )

    creados_negociacion = await conexion.execute(
        """
        INSERT INTO seguimientos (
            oportunidad_id, cuenta_id, usuario_id, creado_por, tipo, titulo, descripcion, fecha_vencimiento
        )
        SELECT
            o.id,
            o.cuenta_id,
            o.propietario_id,
            o.propietario_id,
            'proximo_paso',
            'Confirmar condiciones',
            'Recordatorio automático por oportunidad en negociación.',
            CURRENT_DATE + INTERVAL '2 day'
        FROM oportunidades o
        WHERE o.etapa = 'negotiate'
          AND o.eliminado_en IS NULL
          AND NOT EXISTS (
            SELECT 1
            FROM seguimientos s
            WHERE s.oportunidad_id = o.id
              AND s.estado = 'pendiente'
          )
        """
    )

    alertas_criticas = await conexion.execute(
        """
        INSERT INTO alertas (titulo, descripcion, nivel, oportunidad_id, usuario_id)
        SELECT
            'Fecha de decisión vencida',
            'La oportunidad superó su fecha de decisión y sigue activa.',
            'critico',
            o.id,
            o.propietario_id
        FROM oportunidades o
        WHERE o.fecha_decision < $1
          AND o.etapa = ANY($2::etapa_oportunidad[])
          AND o.eliminado_en IS NULL
          AND NOT EXISTS (
            SELECT 1
            FROM alertas a
            WHERE a.oportunidad_id = o.id
              AND a.titulo = 'Fecha de decisión vencida'
              AND a.resuelta = FALSE
          )
        """,
        fecha_hoy,
        list(_ETAPAS_ACTIVAS),
    )

    alertas_inactividad = await conexion.execute(
        """
        INSERT INTO alertas (titulo, descripcion, nivel, usuario_id)
        SELECT DISTINCT
            'Cuenta sin contacto reciente',
            'No hay actividad de seguimientos en los últimos 30 días.',
            'seguimiento',
            o.propietario_id
        FROM oportunidades o
        WHERE o.eliminado_en IS NULL
          AND o.etapa = ANY($1::etapa_oportunidad[])
          AND NOT EXISTS (
            SELECT 1
            FROM seguimientos s
            WHERE s.cuenta_id = o.cuenta_id
              AND s.creado_en >= NOW() - INTERVAL '30 day'
          )
          AND NOT EXISTS (
            SELECT 1
            FROM alertas a
            WHERE a.usuario_id = o.propietario_id
              AND a.titulo = 'Cuenta sin contacto reciente'
              AND a.resuelta = FALSE
          )
        """,
        list(_ETAPAS_ACTIVAS),
    )

    return {
        "seguimientos_propuesta": creados_propuesta,
        "seguimientos_negociacion": creados_negociacion,
        "alertas_criticas": alertas_criticas,
        "alertas_inactividad": alertas_inactividad,
    }
