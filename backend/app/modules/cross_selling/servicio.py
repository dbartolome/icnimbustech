from __future__ import annotations
from typing import Optional

import asyncpg


async def listar_cuentas(
    conexion: asyncpg.Connection,
    busqueda: Optional[str] = None,
    sbu: Optional[str] = None,
    confianza: Optional[str] = None,
    solo_ranking: bool = False,
) -> list[dict]:
    filtros = []
    params: list = []

    if busqueda:
        params.append(f"%{busqueda}%")
        filtros.append(f"account_name ILIKE ${len(params)}")

    if sbu:
        params.append(sbu)
        filtros.append(f"sbu = ${len(params)}")

    if confianza:
        params.append(confianza)
        filtros.append(f"confianza = ${len(params)}")

    if solo_ranking:
        filtros.append("ranking_accionable IS NOT NULL")

    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    order = "ORDER BY ranking_accionable NULLS LAST, ops_abiertas DESC NULLS LAST"

    rows = await conexion.fetch(
        f"""
        SELECT id, account_name, sbu, servicio_actual, ops_abiertas,
               oportunidades_top, sector_osint, trigger_activador, confianza,
               ranking_accionable, mensaje_comercial, preguntas_discovery, creado_en
        FROM cross_selling_intelligence
        {where}
        {order}
        """,
        *params,
    )
    return [dict(r) for r in rows]


async def obtener_cuenta(
    conexion: asyncpg.Connection,
    account_name: str,
) -> Optional[dict]:
    _SELECT = """
        SELECT id, account_name, sbu, servicio_actual, ops_abiertas,
               oportunidades_top, sector_osint, trigger_activador, confianza,
               ranking_accionable, mensaje_comercial, preguntas_discovery, creado_en
        FROM cross_selling_intelligence
    """

    # 1. Coincidencia exacta (case-insensitive)
    row = await conexion.fetchrow(
        f"{_SELECT} WHERE account_name ILIKE $1 LIMIT 1",
        account_name,
    )
    if row:
        return dict(row)

    # 2. Coincidencia por primera palabra significativa (≥ 4 chars) — cubre variaciones de forma jurídica
    palabras = [p for p in account_name.split() if len(p) >= 4]
    if palabras:
        row = await conexion.fetchrow(
            f"{_SELECT} WHERE account_name ILIKE $1 LIMIT 1",
            f"%{palabras[0]}%",
        )
        if row:
            return dict(row)

    # 3. Similitud trigram (pg_trgm), con fallback si la función no está disponible.
    try:
        row = await conexion.fetchrow(
            f"""
            {_SELECT}
            WHERE similarity(LOWER(account_name), LOWER($1)) > 0.5
            ORDER BY similarity(LOWER(account_name), LOWER($1)) DESC
            LIMIT 1
            """,
            account_name,
        )
        if row:
            return dict(row)
    except asyncpg.UndefinedFunctionError:
        # Fallback robusto sin pg_trgm: compara por tokens y prioriza nombres más cercanos.
        tokens = [t for t in account_name.lower().split() if len(t) >= 3]
        if tokens:
            patrones = [f"%{t}%" for t in tokens[:3]]
            row = await conexion.fetchrow(
                f"""
                {_SELECT}
                WHERE LOWER(account_name) LIKE ANY($1::text[])
                ORDER BY LENGTH(account_name) ASC
                LIMIT 1
                """,
                patrones,
            )
            if row:
                return dict(row)

    return None
