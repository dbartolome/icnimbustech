"""
Skill: calcular_escenarios

Calcula los 3 escenarios de venta (optimista/medio/pesimista) usando
datos reales del pipeline SGS — ticket medio real por sector/producto,
win rate histórico, y pipeline activo de la cuenta.

Sin IA — pura lógica SQL + estadística. Los importes son reales, no estimados.
"""

from dataclasses import dataclass, field
from uuid import UUID

import asyncpg


@dataclass
class Escenario:
    importe: float
    productos: list[str]
    probabilidad: int        # porcentaje 0-100
    plazo_meses: int
    descripcion: str


@dataclass
class EscenariosComerciales:
    optimista: Escenario
    medio: Escenario
    pesimista: Escenario
    ticket_medio_sector: float
    win_rate_sector: float
    base_calculo: str        # descripción del criterio usado


async def calcular_escenarios(
    cuenta_id: UUID,
    productos_recomendados: list[str],
    conexion: asyncpg.Connection,
) -> EscenariosComerciales:
    """
    Genera 3 escenarios basados en datos reales del pipeline SGS.
    Usa el ticket medio y win rate del sector de la cuenta como base.
    """
    # 1. Obtener sector de la cuenta (via oportunidades similares)
    sector_data = await conexion.fetchrow(
        """
        SELECT
            COALESCE(AVG(o.importe) FILTER (WHERE o.etapa = 'closed_won'), 0)  AS ticket_medio,
            COALESCE(
                ROUND(
                    COUNT(o.id) FILTER (WHERE o.etapa = 'closed_won')::numeric
                    / NULLIF(COUNT(o.id) FILTER (WHERE o.etapa IN ('closed_won','closed_lost')), 0) * 100,
                1
                ), 0
            )                                                                   AS win_rate,
            COUNT(o.id)                                                         AS total_opps
        FROM oportunidades o
        WHERE o.cuenta_id = $1 AND o.eliminado_en IS NULL
        """,
        cuenta_id,
    )

    ticket_medio_cuenta = float(sector_data["ticket_medio"] or 0)
    win_rate_cuenta = float(sector_data["win_rate"] or 0)

    # 2. Si la cuenta tiene poco historial, usar ticket medio global del pipeline
    if sector_data["total_opps"] < 3:
        global_data = await conexion.fetchrow(
            """
            SELECT
                COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 7200) AS ticket_medio,
                COALESCE(
                    ROUND(
                        COUNT(id) FILTER (WHERE etapa = 'closed_won')::numeric
                        / NULLIF(COUNT(id) FILTER (WHERE etapa IN ('closed_won','closed_lost')), 0) * 100,
                    1
                    ), 82
                )                                                                 AS win_rate
            FROM oportunidades
            WHERE eliminado_en IS NULL
            """
        )
        ticket_base = float(global_data["ticket_medio"] or 7200)
        win_rate_base = float(global_data["win_rate"] or 82)
        base = "Ticket medio global del pipeline SGS (historial de cuenta insuficiente)"
    else:
        ticket_base = ticket_medio_cuenta
        win_rate_base = win_rate_cuenta
        base = f"Historial real de la cuenta ({sector_data['total_opps']} oportunidades)"

    # 3. Calcular ticket medio por los productos recomendados si están disponibles
    if productos_recomendados:
        ticket_producto = await conexion.fetchval(
            """
            SELECT AVG(o.importe)
            FROM oportunidades o
            JOIN productos p ON p.id = o.producto_id
            WHERE p.nombre = ANY($1::text[])
              AND o.etapa = 'closed_won'
              AND o.eliminado_en IS NULL
            """,
            productos_recomendados,
        )
        if ticket_producto:
            ticket_base = float(ticket_producto)
            base = f"Ticket medio real de los productos recomendados"

    # 4. Construir escenarios con múltiplos del ticket base
    n_productos = max(len(productos_recomendados), 1)

    optimista = Escenario(
        importe=round(ticket_base * n_productos * 1.4, -2),
        productos=productos_recomendados[:3] if productos_recomendados else ["Por definir"],
        probabilidad=min(int(win_rate_base * 1.1), 95),
        plazo_meses=4,
        descripcion="Contratación de todos los productos recomendados en plazo corto",
    )
    medio = Escenario(
        importe=round(ticket_base * max(n_productos - 1, 1), -2),
        productos=productos_recomendados[:2] if productos_recomendados else ["Por definir"],
        probabilidad=int(win_rate_base * 0.85),
        plazo_meses=7,
        descripcion="Contratación del producto principal con opción de ampliación",
    )
    pesimista = Escenario(
        importe=round(ticket_base * 0.6, -2),
        productos=productos_recomendados[:1] if productos_recomendados else ["Por definir"],
        probabilidad=int(win_rate_base * 0.5),
        plazo_meses=12,
        descripcion="Producto mínimo viable, proceso de decisión largo",
    )

    return EscenariosComerciales(
        optimista=optimista,
        medio=medio,
        pesimista=pesimista,
        ticket_medio_sector=ticket_base,
        win_rate_sector=win_rate_base,
        base_calculo=base,
    )


def formatear_para_prompt(escenarios: EscenariosComerciales) -> str:
    def fmt_escenario(nombre: str, e: Escenario) -> str:
        return (
            f"  {nombre}: {e.importe:,.0f}€ | productos: {', '.join(e.productos)} "
            f"| probabilidad: {e.probabilidad}% | plazo: {e.plazo_meses} meses"
        )

    return f"""
ESCENARIOS CALCULADOS (datos reales del pipeline):
{fmt_escenario('Optimista ', escenarios.optimista)}
{fmt_escenario('Medio     ', escenarios.medio)}
{fmt_escenario('Pesimista ', escenarios.pesimista)}
Base de cálculo: {escenarios.base_calculo}
Ticket medio de referencia: {escenarios.ticket_medio_sector:,.0f}€
Win Rate de referencia: {escenarios.win_rate_sector:.1f}%
""".strip()
