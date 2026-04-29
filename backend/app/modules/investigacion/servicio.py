"""
Lógica de negocio del módulo investigacion.
Coordina entre el router y el Orchestrator/InvestigadorWeb.
"""

import json
from uuid import UUID

import asyncpg
from fastapi import BackgroundTasks

from app.agents.orchestrator import ejecutar_investigacion_background


async def iniciar_investigacion(
    cuenta_id: UUID,
    forzar: bool,
    conexion: asyncpg.Connection,
    background: BackgroundTasks,
) -> dict:
    """
    Comprueba si hay investigación reciente. Si no, lanza en background.
    Devuelve el estado actual y el investigacion_id si existe.
    """
    # Verificar que la cuenta existe
    existe = await conexion.fetchval(
        "SELECT id FROM cuentas WHERE id = $1 AND eliminado_en IS NULL",
        cuenta_id,
    )
    if not existe:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    if not forzar:
        reciente = await conexion.fetchrow(
            """
            SELECT id, estado, completado_en
            FROM investigaciones_empresa
            WHERE cuenta_id = $1
              AND estado = 'completada'
              AND completado_en > now() - INTERVAL '30 days'
            ORDER BY completado_en DESC
            LIMIT 1
            """,
            cuenta_id,
        )
        if reciente:
            return {
                "investigacion_id": str(reciente["id"]),
                "estado": "completada",
                "mensaje": "Investigación reciente reutilizada (< 30 días)",
                "completado_en": reciente["completado_en"].isoformat(),
                "lanzado": False,
            }

    # Lanzar investigación en background
    background.add_task(ejecutar_investigacion_background, cuenta_id)

    return {
        "investigacion_id": None,
        "estado": "pendiente",
        "mensaje": "Investigación lanzada en background",
        "lanzado": True,
    }


async def obtener_investigacion(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> dict | None:
    """
    Devuelve la mejor investigación disponible de una cuenta.
    Prioridad: completada reciente > procesando > error más reciente.
    """
    fila = await conexion.fetchrow(
        """
        SELECT
            id, estado, sector, num_empleados, facturacion_estimada,
            certificaciones_actuales, noticias_relevantes, pain_points,
            oportunidades_detectadas, presencia_web, fuentes,
            error_msg, modelo_usado, iniciado_en, completado_en, creado_en
        FROM investigaciones_empresa
        WHERE cuenta_id = $1
        ORDER BY
            CASE estado
                WHEN 'completada'  THEN 1
                WHEN 'procesando'  THEN 2
                WHEN 'pendiente'   THEN 3
                ELSE 4
            END,
            creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        return None

    def _lista(val) -> list:
        if val is None:
            return []
        if isinstance(val, list):
            return val
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    return {
        "id": str(fila["id"]),
        "estado": fila["estado"],
        "sector": fila["sector"],
        "num_empleados": fila["num_empleados"],
        "facturacion_estimada": fila["facturacion_estimada"],
        "certificaciones_actuales": _lista(fila["certificaciones_actuales"]),
        "noticias_relevantes": _lista(fila["noticias_relevantes"]),
        "pain_points": _lista(fila["pain_points"]),
        "oportunidades_detectadas": _lista(fila["oportunidades_detectadas"]),
        "presencia_web": fila["presencia_web"],
        "fuentes": _lista(fila["fuentes"]),
        "error_msg": fila["error_msg"],
        "modelo_usado": fila["modelo_usado"],
        "iniciado_en": fila["iniciado_en"].isoformat() if fila["iniciado_en"] else None,
        "completado_en": fila["completado_en"].isoformat() if fila["completado_en"] else None,
    }


async def listar_investigaciones(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> list[dict]:
    filas = await conexion.fetch(
        """
        SELECT id, estado, sector, error_msg, modelo_usado, creado_en, completado_en
        FROM investigaciones_empresa
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC
        """,
        cuenta_id,
    )
    return [
        {
            "id": str(f["id"]),
            "estado": f["estado"],
            "sector": f["sector"],
            "error_msg": f["error_msg"],
            "modelo_usado": f["modelo_usado"],
            "creado_en": f["creado_en"].isoformat(),
            "completado_en": f["completado_en"].isoformat() if f["completado_en"] else None,
        }
        for f in filas
    ]
