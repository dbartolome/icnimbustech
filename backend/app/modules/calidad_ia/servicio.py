"""
Lógica determinista de validación de calidad para entregables.
"""

import json
from decimal import Decimal
from uuid import UUID

import asyncpg


def _nivel_desde_checks(checks: list[dict]) -> str:
    if any((not c["ok"]) and c.get("bloquea", False) for c in checks):
        return "error"
    if any(not c["ok"] for c in checks):
        return "warning"
    return "ok"


async def validar_entregable(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    tipo_entregable: str,
    usuario_id: UUID | None = None,
) -> dict:
    checks: list[dict] = []
    catalogo_disponible = True

    investigacion_ok = await conexion.fetchval(
        """
        SELECT EXISTS(
            SELECT 1
            FROM investigaciones_empresa
            WHERE cuenta_id = $1
              AND estado = 'completada'
        )
        """,
        cuenta_id,
    )
    checks.append({
        "ok": bool(investigacion_ok),
        "msg": "Existe investigación completada." if investigacion_ok else "No hay investigación completada.",
        "bloquea": False,
    })

    propuesta = await conexion.fetchrow(
        """
        SELECT productos_recomendados, escenario_medio
        FROM propuestas_comerciales
        WHERE cuenta_id = $1
          AND estado = 'completada'
        ORDER BY completado_en DESC NULLS LAST, creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    propuesta_ok = propuesta is not None
    checks.append({
        "ok": propuesta_ok,
        "msg": "Existe propuesta completada." if propuesta_ok else "No hay propuesta completada.",
        "bloquea": True,
    })

    productos_validos = True
    if propuesta_ok:
        productos = list(propuesta["productos_recomendados"] or [])
        for prod in productos:
            nombre_producto = str(prod.get("producto", "")).strip()
            if not nombre_producto:
                continue
            try:
                existe = await conexion.fetchval(
                    """
                    SELECT EXISTS(
                        SELECT 1
                        FROM catalogo_servicios
                        WHERE servicio ILIKE $1
                           OR normas_clave ILIKE $1
                    )
                    """,
                    f"%{nombre_producto}%",
                )
            except asyncpg.UndefinedTableError:
                catalogo_disponible = False
                existe = True
            if not existe:
                productos_validos = False
                break

    checks.append({
        "ok": productos_validos,
        "msg": (
            "Catálogo SGS no disponible; validación de catálogo omitida."
            if not catalogo_disponible
            else "Productos de propuesta alineados con catálogo."
            if productos_validos
            else "Hay productos fuera de catálogo SGS."
        ),
        "bloquea": False,
    })

    outlier_importe = False
    if propuesta_ok and propuesta["escenario_medio"]:
        escenario = dict(propuesta["escenario_medio"] or {})
        importe_escenario = Decimal(str(escenario.get("importe", "0")))
        estadistica = await conexion.fetchrow(
            """
            SELECT
                COALESCE(AVG(importe), 0) AS media,
                COALESCE(STDDEV_POP(importe), 0) AS sigma
            FROM oportunidades
            WHERE cuenta_id = $1
              AND eliminado_en IS NULL
            """,
            cuenta_id,
        )
        media = Decimal(str(estadistica["media"] or 0))
        sigma = Decimal(str(estadistica["sigma"] or 0))
        if sigma > 0:
            limite_inf = media - (sigma * 3)
            limite_sup = media + (sigma * 3)
            outlier_importe = not (limite_inf <= importe_escenario <= limite_sup)

    checks.append({
        "ok": not outlier_importe,
        "msg": "Importe del escenario medio dentro de rango esperado." if not outlier_importe else "Importe del escenario medio fuera de ±3σ del histórico de la cuenta.",
        "bloquea": False,
    })

    seguimientos_vencidos = await conexion.fetchval(
        """
        SELECT EXISTS(
            SELECT 1
            FROM seguimientos
            WHERE cuenta_id = $1
              AND estado = 'pendiente'
              AND fecha_vencimiento < CURRENT_DATE
        )
        """,
        cuenta_id,
    )
    checks.append({
        "ok": not bool(seguimientos_vencidos),
        "msg": "No hay seguimientos vencidos pendientes." if not seguimientos_vencidos else "Hay seguimientos vencidos sin resolver.",
        "bloquea": False,
    })

    nivel = _nivel_desde_checks(checks)
    valido = nivel != "error"

    await conexion.execute(
        """
        INSERT INTO validaciones_calidad (cuenta_id, tipo_entregable, valido, nivel, checks, usuario_id)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
        """,
        cuenta_id,
        tipo_entregable,
        valido,
        nivel,
        json.dumps(checks),
        usuario_id,
    )

    return {
        "cuenta_id": cuenta_id,
        "tipo_entregable": tipo_entregable,
        "valido": valido,
        "nivel": nivel,
        "checks": checks,
    }


async def historial_validaciones(conexion: asyncpg.Connection, cuenta_id: UUID) -> list[dict]:
    filas = await conexion.fetch(
        """
        SELECT id, cuenta_id, tipo_entregable, valido, nivel, checks, usuario_id, forzado, creado_en
        FROM validaciones_calidad
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC
        """,
        cuenta_id,
    )
    return [dict(f) for f in filas]


async def registrar_forzado(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    tipo_entregable: str,
    usuario_id: UUID,
    motivo: str | None,
) -> dict:
    checks = [{
        "ok": False,
        "msg": f"Exportación forzada por usuario. Motivo: {motivo or 'No especificado'}",
        "bloquea": False,
    }]
    fila = await conexion.fetchrow(
        """
        INSERT INTO validaciones_calidad (
            cuenta_id, tipo_entregable, valido, nivel, checks, usuario_id, forzado
        )
        VALUES ($1, $2, TRUE, 'warning', $3::jsonb, $4, TRUE)
        RETURNING id, cuenta_id, tipo_entregable, valido, nivel, checks, usuario_id, forzado, creado_en
        """,
        cuenta_id,
        tipo_entregable,
        json.dumps(checks),
        usuario_id,
    )
    return dict(fila)
