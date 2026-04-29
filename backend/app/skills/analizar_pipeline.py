"""
Skill: analizar_pipeline

Lee métricas reales del pipeline SGS para una cuenta específica.
Sin IA — solo queries SQL. Devuelve datos estructurados listos para
ser consumidos por el AnalistaPipeline (Ollama).

Esta skill es la fuente de verdad de datos internos.
NUNCA se pasa su output a Claude online — solo a Ollama local.
"""

from dataclasses import dataclass, field
from uuid import UUID

import asyncpg


@dataclass
class MetricasCuenta:
    cuenta_id: str
    nombre_cuenta: str
    total_oportunidades: int
    oportunidades_activas: int
    pipeline_activo: float
    importe_ganado: float
    win_rate: float
    ticket_medio: float
    productos_contratados: list[dict] = field(default_factory=list)
    etapas_activas: list[dict] = field(default_factory=list)
    historico_anual: list[dict] = field(default_factory=list)


async def analizar_pipeline(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
) -> MetricasCuenta:
    """
    Devuelve métricas completas del pipeline para una cuenta.
    Usa SQL real — sin estimaciones ni datos hardcodeados.
    """
    _CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")
    _GANADA = ("closed_won",)

    # Métricas generales de la cuenta
    fila = await conexion.fetchrow(
        f"""
        SELECT
            c.nombre,
            COUNT(o.id)                                                                   AS total,
            COUNT(o.id) FILTER (WHERE o.etapa NOT IN {_CERRADAS})                         AS activas,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN {_CERRADAS}), 0)         AS pipeline,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)             AS ganado,
            COALESCE(
                ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::numeric
                    / NULLIF(COUNT(o.id) FILTER (WHERE o.etapa IN ('closed_won','closed_lost')), 0) * 100,
                    1
                ), 0
            )                                                                              AS win_rate,
            COALESCE(AVG(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)             AS ticket_medio
        FROM cuentas c
        LEFT JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
        WHERE c.id = $1
        GROUP BY c.nombre
        """,
        cuenta_id,
    )

    if not fila:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    # Productos/normas más frecuentes en esta cuenta
    productos = await conexion.fetch(
        """
        SELECT
            p.nombre,
            COUNT(o.id)   AS veces,
            COALESCE(SUM(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0) AS ganado
        FROM oportunidades o
        JOIN productos p ON p.id = o.producto_id
        WHERE o.cuenta_id = $1 AND o.eliminado_en IS NULL
        GROUP BY p.nombre
        ORDER BY veces DESC
        LIMIT 10
        """,
        cuenta_id,
    )

    # Etapas activas con importes
    etapas = await conexion.fetch(
        f"""
        SELECT etapa, COUNT(*) AS cantidad, COALESCE(SUM(importe), 0) AS importe_total
        FROM oportunidades
        WHERE cuenta_id = $1
          AND etapa NOT IN {_CERRADAS}
          AND eliminado_en IS NULL
        GROUP BY etapa
        ORDER BY importe_total DESC
        """,
        cuenta_id,
    )

    return MetricasCuenta(
        cuenta_id=str(cuenta_id),
        nombre_cuenta=fila["nombre"],
        total_oportunidades=fila["total"] or 0,
        oportunidades_activas=fila["activas"] or 0,
        pipeline_activo=float(fila["pipeline"] or 0),
        importe_ganado=float(fila["ganado"] or 0),
        win_rate=float(fila["win_rate"] or 0),
        ticket_medio=float(fila["ticket_medio"] or 0),
        productos_contratados=[
            {"nombre": r["nombre"], "veces": r["veces"], "ganado": float(r["ganado"])}
            for r in productos
        ],
        etapas_activas=[
            {"etapa": r["etapa"], "cantidad": r["cantidad"], "importe": float(r["importe_total"])}
            for r in etapas
        ],
    )


def formatear_para_prompt(metricas: MetricasCuenta) -> str:
    """
    Convierte las métricas a texto estructurado para incluir en el prompt de Ollama.
    Formato legible para el LLM.
    """
    productos_txt = "\n".join(
        f"  - {p['nombre']}: {p['veces']} oportunidades, {p['ganado']:,.0f}€ ganados"
        for p in metricas.productos_contratados
    ) or "  Sin historial de productos"

    etapas_txt = "\n".join(
        f"  - {e['etapa']}: {e['cantidad']} opps, {e['importe']:,.0f}€"
        for e in metricas.etapas_activas
    ) or "  Sin oportunidades activas"

    return f"""
DATOS PIPELINE SGS — {metricas.nombre_cuenta}
- Oportunidades totales: {metricas.total_oportunidades}
- Oportunidades activas: {metricas.oportunidades_activas}
- Pipeline activo: {metricas.pipeline_activo:,.0f}€
- Importe ganado histórico: {metricas.importe_ganado:,.0f}€
- Win Rate: {metricas.win_rate:.1f}%
- Ticket medio ganado: {metricas.ticket_medio:,.0f}€

Productos/normas en esta cuenta:
{productos_txt}

Etapas del pipeline activo:
{etapas_txt}
""".strip()
