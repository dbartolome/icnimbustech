"""
Agente 1 — InvestigadorWeb

Investiga empresas en internet usando Claude + Anthropic Web Search.
SOLO toca información pública. Nunca ve datos del pipeline SGS.
Persiste el resultado en investigaciones_empresa.
"""

import json
from typing import Any
from uuid import UUID

import asyncpg

from app.agents.base import AgentBase, ResultadoAgente
from app.skills.buscar_empresa import buscar_empresa


class InvestigadorWeb(AgentBase):
    nombre = "investigador_web"

    async def run(
        self,
        entrada: dict[str, Any],
        conexion: asyncpg.Connection,
    ) -> ResultadoAgente:
        """
        entrada esperada: {"cuenta_id": "uuid-string"}
        Devuelve: {"investigacion_id": "uuid-string"}
        """
        try:
            cuenta_id = UUID(entrada["cuenta_id"])
        except (KeyError, ValueError) as e:
            return ResultadoAgente(exito=False, error=f"cuenta_id inválido: {e}")

        # Obtener nombre de la empresa desde DB
        fila = await conexion.fetchrow(
            "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL",
            cuenta_id,
        )
        if not fila:
            return ResultadoAgente(exito=False, error=f"Cuenta {cuenta_id} no encontrada")

        nombre_empresa = fila["nombre"]

        # Crear registro de investigación en estado "procesando"
        investigacion_id = await conexion.fetchval(
            """
            INSERT INTO investigaciones_empresa
                (cuenta_id, estado, iniciado_en)
            VALUES ($1, 'procesando', now())
            RETURNING id
            """,
            cuenta_id,
        )

        try:
            # Ejecutar búsqueda — solo información pública
            ficha = await buscar_empresa(nombre_empresa)

            # Persistir resultado
            await conexion.execute(
                """
                UPDATE investigaciones_empresa SET
                    estado                   = 'completada',
                    sector                   = $2,
                    num_empleados            = $3,
                    facturacion_estimada     = $4,
                    certificaciones_actuales = $5,
                    noticias_relevantes      = $6,
                    pain_points              = $7,
                    oportunidades_detectadas = $8,
                    presencia_web            = $9,
                    fuentes                  = $10,
                    raw_research             = $11,
                    completado_en            = now()
                WHERE id = $1
                """,
                investigacion_id,
                ficha.sector,
                ficha.num_empleados,
                ficha.facturacion_estimada,
                json.dumps(ficha.certificaciones_actuales),
                json.dumps(ficha.noticias_relevantes),
                json.dumps(ficha.pain_points),
                json.dumps(ficha.oportunidades_detectadas),
                ficha.presencia_web,
                json.dumps(ficha.fuentes),
                ficha.raw_research,
            )

            return ResultadoAgente(
                exito=True,
                datos={"investigacion_id": str(investigacion_id)},
            )

        except BaseException as e:
            msg = str(e) or repr(e) or type(e).__name__
            await conexion.execute(
                "UPDATE investigaciones_empresa SET estado = 'error', error_msg = $2 WHERE id = $1",
                investigacion_id,
                msg,
            )
            return ResultadoAgente(exito=False, error=msg)
