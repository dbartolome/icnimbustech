"""
Lógica de negocio del módulo Reuniones.
"""

import json
from uuid import UUID

import asyncpg

from app.modules.ia.servicio import ConfigIA, llamar_ia


def _parse_jsonb(valor, default):
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (json.JSONDecodeError, ValueError):
            pass
    return default

_ETAPAS_CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")


async def construir_ficha_reunion(conexion: asyncpg.Connection, cuenta_id: UUID) -> dict | None:
    cuenta = await conexion.fetchrow(
        """
        SELECT id, nombre
        FROM cuentas
        WHERE id = $1 AND eliminado_en IS NULL
        """,
        cuenta_id,
    )
    if not cuenta:
        return None

    investigacion = await conexion.fetchrow(
        """
        SELECT
            sector,
            num_empleados,
            pain_points,
            certificaciones_actuales,
            noticias_relevantes
        FROM investigaciones_empresa
        WHERE cuenta_id = $1
          AND estado = 'completada'
        ORDER BY completado_en DESC NULLS LAST, creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )

    propuesta = await conexion.fetchrow(
        """
        SELECT
            productos_recomendados,
            escenario_medio
        FROM propuestas_comerciales
        WHERE cuenta_id = $1
          AND estado = 'completada'
        ORDER BY completado_en DESC NULLS LAST, creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )

    pipeline = await conexion.fetchrow(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE etapa NOT IN {_ETAPAS_CERRADAS}) AS activas,
            COALESCE(SUM(importe) FILTER (WHERE etapa NOT IN {_ETAPAS_CERRADAS}), 0) AS importe_total,
            (
                SELECT o2.etapa::text
                FROM oportunidades o2
                WHERE o2.cuenta_id = $1
                  AND o2.eliminado_en IS NULL
                  AND o2.etapa NOT IN {_ETAPAS_CERRADAS}
                ORDER BY o2.fecha_decision ASC NULLS LAST, o2.creado_en DESC
                LIMIT 1
            ) AS etapa_critica
        FROM oportunidades
        WHERE cuenta_id = $1
          AND eliminado_en IS NULL
        """,
        cuenta_id,
    )

    seguimientos = await conexion.fetch(
        """
        SELECT
            id, tipo::text AS tipo, titulo, descripcion,
            fecha_vencimiento::text AS fecha_vencimiento, estado::text AS estado
        FROM seguimientos
        WHERE cuenta_id = $1
          AND estado = 'pendiente'
        ORDER BY fecha_vencimiento ASC
        """,
        cuenta_id,
    )

    score_medio = await conexion.fetchval(
        """
        SELECT COALESCE(ROUND(AVG(ls.score)), 0)
        FROM lead_scores ls
        JOIN oportunidades o ON o.id = ls.oportunidad_id
        WHERE o.cuenta_id = $1
          AND o.eliminado_en IS NULL
        """,
        cuenta_id,
    )

    # Como no hay trazabilidad directa por cuenta para deck/pdf/briefing en el schema actual,
    # se usa disponibilidad funcional basada en propuesta/investigación completadas.
    tiene_propuesta = propuesta is not None
    tiene_investigacion = investigacion is not None

    return {
        "cuenta": {
            "nombre": cuenta["nombre"],
            "sector": investigacion["sector"] if investigacion else None,
            "num_empleados": investigacion["num_empleados"] if investigacion else None,
        },
        "investigacion": {
            "pain_points": _parse_jsonb(investigacion["pain_points"], []) if investigacion else [],
            "certificaciones_actuales": _parse_jsonb(investigacion["certificaciones_actuales"], []) if investigacion else [],
            "noticias_relevantes": _parse_jsonb(investigacion["noticias_relevantes"], []) if investigacion else [],
        },
        "propuesta": {
            "productos_recomendados": _parse_jsonb(propuesta["productos_recomendados"], []) if propuesta else [],
            "escenario_medio": _parse_jsonb(propuesta["escenario_medio"], {}) if propuesta else {},
        },
        "pipeline": {
            "activas": int((pipeline["activas"] or 0) if pipeline else 0),
            "importe_total": float((pipeline["importe_total"] or 0) if pipeline else 0),
            "etapa_critica": pipeline["etapa_critica"] if pipeline else None,
        },
        "seguimientos": [dict(s) for s in seguimientos],
        "score_medio": int(score_medio or 0),
        "materiales": {
            "deck_disponible": tiene_propuesta,
            "pdf_disponible": tiene_propuesta,
            "briefing_disponible": tiene_investigacion,
        },
    }


async def generar_preguntas_recomendadas(conexion: asyncpg.Connection, cuenta_id: UUID) -> list[str]:
    ficha = await construir_ficha_reunion(conexion, cuenta_id)
    if not ficha:
        raise ValueError("Cuenta no encontrada.")

    prompt = (
        "Genera 5 preguntas de calificación comercial para preparar una reunión con esta cuenta. "
        "Devuelve SOLO JSON válido con estructura {\"preguntas\": [\"...\", \"...\"]}. "
        f"Contexto: {json.dumps(ficha, ensure_ascii=False)}"
    )

    respuesta = await llamar_ia(
        mensajes=[{"role": "user", "content": prompt}],
        system="Responde en español de España. Sé específico y accionable.",
        config=ConfigIA(proveedor="ollama"),
        max_tokens=500,
    )

    texto = respuesta.strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(texto)
        preguntas = data.get("preguntas", [])
        if isinstance(preguntas, list):
            return [str(p).strip() for p in preguntas if str(p).strip()][:5]
    except json.JSONDecodeError:
        pass

    # Fallback por si el modelo no devuelve JSON estricto
    lineas = [linea.strip("-• ").strip() for linea in texto.splitlines() if linea.strip()]
    return lineas[:5]
