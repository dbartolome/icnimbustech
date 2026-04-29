"""
Lógica de negocio del módulo propuesta.
"""

from uuid import UUID

import asyncpg
from fastapi import BackgroundTasks

from app.agents.orchestrator import ejecutar_propuesta_background, ejecutar_pipeline_background


async def iniciar_propuesta(
    cuenta_id: UUID,
    investigacion_id: str | None,
    conexion: asyncpg.Connection,
    background: BackgroundTasks,
) -> dict:
    # Verificar cuenta
    existe = await conexion.fetchval(
        "SELECT id FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not existe:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    # Resolver investigación a usar
    if investigacion_id:
        inv_fila = await conexion.fetchrow(
            "SELECT id, estado FROM investigaciones_empresa WHERE id = $1",
            investigacion_id,
        )
        if not inv_fila or inv_fila["estado"] != "completada":
            raise ValueError("La investigación indicada no existe o no está completada")
        inv_id = str(inv_fila["id"])
    else:
        inv_fila = await conexion.fetchrow(
            """
            SELECT id FROM investigaciones_empresa
            WHERE cuenta_id = $1 AND estado = 'completada'
            ORDER BY completado_en DESC LIMIT 1
            """,
            cuenta_id,
        )
        if not inv_fila:
            raise ValueError("No hay investigación completada para esta cuenta. Lanza primero /investigacion/{cuenta_id}")
        inv_id = str(inv_fila["id"])

    background.add_task(ejecutar_propuesta_background, cuenta_id, inv_id)

    return {
        "estado": "pendiente",
        "mensaje": "Propuesta generándose en background con Ollama local",
        "investigacion_id": inv_id,
        "lanzado": True,
    }


async def iniciar_pipeline_completo(
    cuenta_id: UUID,
    forzar_reinvestigacion: bool,
    conexion: asyncpg.Connection,
    background: BackgroundTasks,
) -> dict:
    existe = await conexion.fetchval(
        "SELECT id FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not existe:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    background.add_task(ejecutar_pipeline_background, cuenta_id, forzar_reinvestigacion)

    return {
        "estado": "pendiente",
        "mensaje": "Pipeline completo lanzado: Investigación → Propuesta",
        "forzar_reinvestigacion": forzar_reinvestigacion,
        "lanzado": True,
    }


async def obtener_propuesta(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> dict | None:
    fila = await conexion.fetchrow(
        """
        SELECT
            id, estado, investigacion_id, modelo_usado,
            productos_recomendados, escenario_optimista,
            escenario_medio, escenario_pesimista,
            plan_de_accion, argumentario_general,
            error_msg, iniciado_en, completado_en, creado_en
        FROM propuestas_comerciales
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        return None

    return {
        "id": str(fila["id"]),
        "estado": fila["estado"],
        "investigacion_id": str(fila["investigacion_id"]) if fila["investigacion_id"] else None,
        "modelo_usado": fila["modelo_usado"],
        "productos_recomendados": fila["productos_recomendados"] or [],
        "escenario_optimista": fila["escenario_optimista"],
        "escenario_medio": fila["escenario_medio"],
        "escenario_pesimista": fila["escenario_pesimista"],
        "plan_de_accion": fila["plan_de_accion"] or [],
        "argumentario_general": fila["argumentario_general"],
        "error_msg": fila["error_msg"],
        "iniciado_en": fila["iniciado_en"].isoformat() if fila["iniciado_en"] else None,
        "completado_en": fila["completado_en"].isoformat() if fila["completado_en"] else None,
    }


async def estado_propuesta(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> dict:
    fila = await conexion.fetchrow(
        """
        SELECT id, estado, error_msg, completado_en
        FROM propuestas_comerciales
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        return {"estado": "sin_propuesta", "propuesta_id": None}

    return {
        "propuesta_id": str(fila["id"]),
        "estado": fila["estado"],
        "error_msg": fila["error_msg"],
        "completado_en": fila["completado_en"].isoformat() if fila["completado_en"] else None,
    }
