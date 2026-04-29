"""
Orchestrator — coordina el pipeline de agentes.

No contiene lógica de negocio ni llama a IA directamente.
Decide qué agente ejecutar, en qué orden, y gestiona el estado global del pipeline.
"""

import asyncio
import logging
import traceback
from uuid import UUID

import asyncpg

from app.agents.base import ResultadoAgente
from app.database import obtener_pool

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Pipeline completo: InvestigadorWeb → AnalistaPipeline.
    Cada agente se importa lazy para evitar ciclos de importación.
    """

    async def pipeline_completo(
        self,
        cuenta_id: UUID,
        conexion: asyncpg.Connection,
        forzar_reinvestigacion: bool = False,
    ) -> ResultadoAgente:
        """
        Ejecuta el pipeline completo para una cuenta.
        Si ya existe investigación reciente (< 30 días), la reutiliza.
        """
        from app.agents.investigador_web import InvestigadorWeb
        from app.agents.analista_pipeline import AnalistaPipeline

        # Paso 1 — Investigación (saltable si hay datos recientes)
        investigacion_id = None

        if not forzar_reinvestigacion:
            investigacion_id = await self._investigacion_reciente(cuenta_id, conexion)

        if not investigacion_id:
            agente_inv = InvestigadorWeb()
            resultado_inv = await agente_inv.run(
                {"cuenta_id": str(cuenta_id)},
                conexion,
            )
            if not resultado_inv.exito:
                return resultado_inv
            investigacion_id = resultado_inv.datos["investigacion_id"]

        # Paso 2 — Análisis (siempre con Ollama local)
        agente_analista = AnalistaPipeline()
        return await agente_analista.run(
            {
                "cuenta_id": str(cuenta_id),
                "investigacion_id": investigacion_id,
            },
            conexion,
        )

    async def solo_investigacion(
        self,
        cuenta_id: UUID,
        conexion: asyncpg.Connection,
    ) -> ResultadoAgente:
        """Ejecuta solo el Agente 1 (InvestigadorWeb)."""
        from app.agents.investigador_web import InvestigadorWeb
        return await InvestigadorWeb().run({"cuenta_id": str(cuenta_id)}, conexion)

    async def solo_propuesta(
        self,
        cuenta_id: UUID,
        investigacion_id: str,
        conexion: asyncpg.Connection,
    ) -> ResultadoAgente:
        """Ejecuta solo el Agente 2 (AnalistaPipeline) con investigación existente."""
        from app.agents.analista_pipeline import AnalistaPipeline
        return await AnalistaPipeline().run(
            {"cuenta_id": str(cuenta_id), "investigacion_id": investigacion_id},
            conexion,
        )

    async def _investigacion_reciente(
        self,
        cuenta_id: UUID,
        conexion: asyncpg.Connection,
    ) -> str | None:
        """Devuelve el ID de la investigación más reciente si tiene < 30 días y está completada."""
        fila = await conexion.fetchrow(
            """
            SELECT id FROM investigaciones_empresa
            WHERE cuenta_id = $1
              AND estado = 'completada'
              AND completado_en > now() - INTERVAL '30 days'
            ORDER BY completado_en DESC
            LIMIT 1
            """,
            cuenta_id,
        )
        return str(fila["id"]) if fila else None


# =============================================================================
# Funciones para BackgroundTasks (FastAPI)
# BackgroundTasks no mantiene la conexión del request — abrimos conexión propia.
# =============================================================================

async def ejecutar_pipeline_background(
    cuenta_id: UUID,
    forzar_reinvestigacion: bool = False,
) -> None:
    """
    Función para usar con FastAPI BackgroundTasks.
    Abre su propia conexión desde el pool.
    """
    async with (await obtener_pool()).acquire() as conexion:
        orquestador = Orchestrator()
        await orquestador.pipeline_completo(cuenta_id, conexion, forzar_reinvestigacion)


async def ejecutar_investigacion_background(cuenta_id: UUID) -> None:
    async with (await obtener_pool()).acquire() as conexion:
        orquestador = Orchestrator()
        await orquestador.solo_investigacion(cuenta_id, conexion)


async def ejecutar_propuesta_background(cuenta_id: UUID, investigacion_id: str) -> None:
    try:
        async with (await obtener_pool()).acquire() as conexion:
            orquestador = Orchestrator()
            await orquestador.solo_propuesta(cuenta_id, investigacion_id, conexion)
    except Exception:
        logger.error("Background propuesta FALLÓ:\n%s", traceback.format_exc())
