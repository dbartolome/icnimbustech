"""
Lógica de negocio del módulo Scoring.
"""

import json
from datetime import date
from decimal import Decimal
from uuid import UUID

import asyncpg

_ETAPAS_ALTAS = {"propose", "negotiate", "estimation_accepted"}
_ETAPAS_ACTIVAS = (
    "estimation_sent",
    "technically_approved",
    "in_progress",
    "discover",
    "contract_offer_sent",
    "propose",
    "estimation_accepted",
    "negotiate",
)


def _normalizar_factores_jsonb(factores_raw: object) -> dict:
    """
    Normaliza un campo JSONB de PostgreSQL que puede venir como dict, str JSON o None.
    """
    if isinstance(factores_raw, dict):
        return factores_raw
    if isinstance(factores_raw, str):
        try:
            parsed = json.loads(factores_raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def calcular_score(oportunidad: dict, ticket_medio_global: Decimal) -> dict:
    """
    Función pura: calcula score + factores para una oportunidad.
    """
    factores: dict[str, int] = {}

    if oportunidad["etapa"] in _ETAPAS_ALTAS:
        factores["etapa"] = 30
    if Decimal(oportunidad["importe"]) > ticket_medio_global:
        factores["importe"] = 20
    if oportunidad["fecha_decision"]:
        dias_decision = (oportunidad["fecha_decision"] - date.today()).days
        if 0 <= dias_decision <= 60:
            factores["fecha_decision"] = 15
    if oportunidad["tiene_propuesta"]:
        factores["propuesta_ia"] = 15
    if oportunidad["tipo"] == "renovacion":
        factores["tipo"] = 10
    if not oportunidad["tiene_seguimiento_pendiente"]:
        factores["sin_seguimiento"] = -20

    score = max(0, min(100, sum(factores.values())))
    return {"score": score, "factores": factores}


async def obtener_score(conexion: asyncpg.Connection, oportunidad_id: UUID) -> dict | None:
    fila = await conexion.fetchrow(
        """
        SELECT oportunidad_id, score, factores, calculado_en
        FROM lead_scores
        WHERE oportunidad_id = $1
        """,
        oportunidad_id,
    )
    if not fila:
        return None
    resultado = dict(fila)
    resultado["factores"] = _normalizar_factores_jsonb(resultado.get("factores"))
    return resultado


async def recalcular_oportunidad(conexion: asyncpg.Connection, oportunidad_id: UUID) -> dict | None:
    ticket_medio = await conexion.fetchval(
        """
        SELECT COALESCE(AVG(importe), 0)
        FROM oportunidades
        WHERE eliminado_en IS NULL
          AND etapa = 'closed_won'
        """
    )
    ticket_medio_global = Decimal(ticket_medio or 0)

    fila = await conexion.fetchrow(
        """
        SELECT
            o.id,
            o.etapa::text AS etapa,
            o.importe,
            o.fecha_decision,
            o.tipo::text AS tipo,
            o.cuenta_id,
            EXISTS(
                SELECT 1
                FROM propuestas_comerciales p
                WHERE p.cuenta_id = o.cuenta_id
                  AND p.estado = 'completada'
            ) AS tiene_propuesta,
            EXISTS(
                SELECT 1
                FROM seguimientos s
                WHERE s.oportunidad_id = o.id
                  AND s.estado = 'pendiente'
            ) AS tiene_seguimiento_pendiente
        FROM oportunidades o
        WHERE o.id = $1
          AND o.eliminado_en IS NULL
        """,
        oportunidad_id,
    )
    if not fila:
        return None

    oportunidad = dict(fila)
    resultado = calcular_score(oportunidad, ticket_medio_global)
    score_actual = await conexion.fetchval(
        "SELECT score FROM lead_scores WHERE oportunidad_id = $1",
        oportunidad_id,
    )
    score_anterior = int(score_actual) if score_actual is not None else None

    factores = {**resultado["factores"], "ticket_medio_global": str(ticket_medio_global)}
    if score_anterior is not None:
        factores["score_anterior"] = score_anterior

    await conexion.execute(
        """
        INSERT INTO lead_scores (oportunidad_id, score, factores, calculado_en)
        VALUES ($1, $2, $3::jsonb, NOW())
        ON CONFLICT (oportunidad_id)
        DO UPDATE SET
            score = EXCLUDED.score,
            factores = EXCLUDED.factores,
            calculado_en = NOW()
        """,
        oportunidad_id,
        resultado["score"],
        json.dumps(factores),
    )

    return await obtener_score(conexion, oportunidad_id)


async def recalcular_scores_pipeline(
    conexion: asyncpg.Connection,
    propietario_id: UUID | None = None,
) -> dict:
    where_prop = ""
    params: list = []
    if propietario_id:
        where_prop = "AND o.propietario_id = $1"
        params.append(propietario_id)

    filas = await conexion.fetch(
        f"""
        SELECT o.id
        FROM oportunidades o
        WHERE o.eliminado_en IS NULL
          AND o.etapa = ANY($1::etapa_oportunidad[])
          {where_prop}
        """,
        list(_ETAPAS_ACTIVAS),
        *params,
    )

    recalculadas = 0
    for fila in filas:
        score = await recalcular_oportunidad(conexion, fila["id"])
        if score:
            recalculadas += 1

    return {"total_oportunidades": len(filas), "recalculadas": recalculadas}


async def listar_scores_criticos(
    conexion: asyncpg.Connection,
    umbral: int,
    usuario_id: UUID,
    es_comercial: bool,
) -> list[dict]:
    where_prop = "AND o.propietario_id = $2" if es_comercial else ""
    params: list = [umbral]
    if es_comercial:
        params.append(usuario_id)

    filas = await conexion.fetch(
        f"""
        SELECT
            s.oportunidad_id,
            o.nombre,
            c.nombre AS cuenta_nombre,
            s.score,
            o.etapa::text AS etapa,
            o.importe::float8 AS importe
        FROM lead_scores s
        JOIN oportunidades o ON o.id = s.oportunidad_id
        LEFT JOIN cuentas c ON c.id = o.cuenta_id
        WHERE s.score < $1
          AND o.eliminado_en IS NULL
          {where_prop}
        ORDER BY s.score ASC, o.importe DESC
        """,
        *params,
    )
    return [dict(f) for f in filas]


async def detectar_caida_score(conexion: asyncpg.Connection) -> dict:
    filas = await conexion.fetch(
        """
        SELECT
            ls.oportunidad_id,
            ls.score,
            ls.factores,
            o.propietario_id
        FROM lead_scores ls
        JOIN oportunidades o ON o.id = ls.oportunidad_id
        WHERE o.eliminado_en IS NULL
        """
    )

    insertadas = 0
    for fila in filas:
        factores = _normalizar_factores_jsonb(fila["factores"])
        score_anterior = factores.get("score_anterior")
        if score_anterior is None:
            continue
        if int(score_anterior) > 60 and int(fila["score"]) < 40:
            resultado = await conexion.execute(
                """
                INSERT INTO alertas (titulo, descripcion, nivel, oportunidad_id, usuario_id)
                SELECT
                    'Caída crítica de score',
                    'El score de la oportunidad cayó de >60 a <40.',
                    'critico',
                    $1,
                    $2
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM alertas a
                    WHERE a.oportunidad_id = $1
                      AND a.titulo = 'Caída crítica de score'
                      AND a.resuelta = FALSE
                )
                """,
                fila["oportunidad_id"],
                fila["propietario_id"],
            )
            if resultado == "INSERT 0 1":
                insertadas += 1

    return {"alertas_insertadas": insertadas}


async def registrar_feedback_score(
    conexion: asyncpg.Connection,
    oportunidad_id: UUID,
    usuario_id: UUID,
    util: bool,
    nota: str | None,
) -> dict | None:
    fila = await conexion.fetchrow(
        """
        SELECT factores
        FROM lead_scores
        WHERE oportunidad_id = $1
        """,
        oportunidad_id,
    )
    if not fila:
        return None

    factores = _normalizar_factores_jsonb(fila["factores"])
    factores["feedback"] = {
        "util": util,
        "nota": nota,
        "usuario_id": str(usuario_id),
        "registrado_en": date.today().isoformat(),
    }

    await conexion.execute(
        """
        UPDATE lead_scores
        SET factores = $2::jsonb, calculado_en = calculado_en
        WHERE oportunidad_id = $1
        """,
        oportunidad_id,
        json.dumps(factores),
    )

    return {"oportunidad_id": oportunidad_id, "feedback": factores["feedback"]}
