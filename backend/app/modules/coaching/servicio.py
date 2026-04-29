"""
Lógica de negocio del módulo Coaching.
"""

import json
from uuid import UUID

import asyncpg

from app.modules.ia.servicio import ConfigIA, llamar_ia


async def analizar_notas_cuenta(conexion: asyncpg.Connection, cuenta_id: UUID, usuario_id: UUID) -> dict:
    notas = await conexion.fetch(
        """
        SELECT n.transcripcion
        FROM notas_voz n
        JOIN oportunidades o ON o.id = n.oportunidad_id
        WHERE o.cuenta_id = $1
          AND o.eliminado_en IS NULL
        ORDER BY n.creado_en DESC
        LIMIT 10
        """,
        cuenta_id,
    )

    texto_notas = "\n\n".join(f"- {n['transcripcion']}" for n in notas if n["transcripcion"])
    if not texto_notas:
        resultado = {
            "objeciones": [],
            "riesgos": [],
            "mejoras_pitch": [],
            "mensaje": "Sin notas recientes para analizar.",
        }
    else:
        prompt = (
            "Analiza estas notas comerciales y devuelve SOLO JSON válido con "
            "{\"objeciones\":[], \"riesgos\":[], \"mejoras_pitch\":[]}.\n\n"
            f"Notas:\n{texto_notas}"
        )
        respuesta = await llamar_ia(
            mensajes=[{"role": "user", "content": prompt}],
            system="Responde en español de España. Sé directo. No incluyas PII.",
            config=ConfigIA(proveedor="ollama", ollama_modelo="qwen2.5:14b"),
            max_tokens=900,
        )
        texto = respuesta.replace("```json", "").replace("```", "").strip()
        try:
            data = json.loads(texto)
            resultado = {
                "objeciones": list(data.get("objeciones", [])),
                "riesgos": list(data.get("riesgos", [])),
                "mejoras_pitch": list(data.get("mejoras_pitch", [])),
            }
        except json.JSONDecodeError:
            resultado = {
                "objeciones": [],
                "riesgos": [],
                "mejoras_pitch": [],
                "mensaje": "No se pudo parsear la respuesta del modelo.",
            }

    fila = await conexion.fetchrow(
        """
        INSERT INTO coaching_sesiones (usuario_id, cuenta_id, tipo, resultado)
        VALUES ($1, $2, 'analisis_notas', $3::jsonb)
        RETURNING id, usuario_id, cuenta_id, tipo::text AS tipo, resultado, creado_en
        """,
        usuario_id,
        cuenta_id,
        json.dumps(resultado),
    )
    return dict(fila)


async def generar_plan_mejora(conexion: asyncpg.Connection, usuario_id: UUID) -> dict:
    metricas = await conexion.fetchrow(
        """
        SELECT
            COALESCE(
                ROUND(
                    COUNT(*) FILTER (WHERE etapa = 'closed_won')::numeric
                    / NULLIF(COUNT(*) FILTER (WHERE etapa IN ('closed_won', 'closed_lost')), 0) * 100, 1
                ), 0
            ) AS win_rate,
            COUNT(*) FILTER (
                WHERE etapa = 'closed_lost'
                  AND fecha_creacion >= (CURRENT_DATE - INTERVAL '3 months')
            ) AS perdidas_trimestre,
            COUNT(*) FILTER (
                WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
            ) AS activas
        FROM oportunidades
        WHERE propietario_id = $1
          AND eliminado_en IS NULL
        """,
        usuario_id,
    )

    coaching_prev = await conexion.fetch(
        """
        SELECT resultado
        FROM coaching_sesiones
        WHERE usuario_id = $1
        ORDER BY creado_en DESC
        LIMIT 5
        """,
        usuario_id,
    )

    prompt = (
        "Genera un plan de mejora semanal para un comercial y devuelve SOLO JSON válido con "
        "{\"focos_semana\":[], \"acciones\":[], \"metricas_objetivo\":{}}.\n"
        f"Métricas actuales: {json.dumps(dict(metricas or {}), ensure_ascii=False)}\n"
        f"Coaching previo: {json.dumps([c['resultado'] for c in coaching_prev], ensure_ascii=False)}"
    )

    respuesta = await llamar_ia(
        mensajes=[{"role": "user", "content": prompt}],
        system="Responde en español de España. Enfoca acciones concretas de ventas B2B.",
        config=ConfigIA(proveedor="ollama", ollama_modelo="qwen2.5:14b"),
        max_tokens=900,
    )

    texto = respuesta.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(texto)
        resultado = {
            "focos_semana": list(data.get("focos_semana", [])),
            "acciones": list(data.get("acciones", [])),
            "metricas_objetivo": dict(data.get("metricas_objetivo", {})),
        }
    except json.JSONDecodeError:
        resultado = {
            "focos_semana": [],
            "acciones": [],
            "metricas_objetivo": {},
            "mensaje": "No se pudo parsear la respuesta del modelo.",
        }

    await conexion.execute(
        """
        INSERT INTO coaching_sesiones (usuario_id, tipo, resultado)
        VALUES ($1, 'plan_mejora', $2::jsonb)
        """,
        usuario_id,
        json.dumps(resultado),
    )

    return resultado


async def coaching_equipo(conexion: asyncpg.Connection) -> list[dict]:
    filas = await conexion.fetch(
        """
        SELECT
            u.id AS usuario_id,
            u.nombre_completo,
            COUNT(cs.id) AS total_sesiones,
            MAX(cs.creado_en) AS ultima_sesion
        FROM usuarios u
        LEFT JOIN coaching_sesiones cs ON cs.usuario_id = u.id
        WHERE u.eliminado_en IS NULL
          AND u.rol IN ('comercial', 'manager')
        GROUP BY u.id, u.nombre_completo
        ORDER BY total_sesiones DESC, u.nombre_completo ASC
        """
    )
    return [dict(f) for f in filas]


async def historial_usuario(conexion: asyncpg.Connection, usuario_id: UUID) -> list[dict]:
    filas = await conexion.fetch(
        """
        SELECT id, usuario_id, cuenta_id, tipo::text AS tipo, resultado, creado_en
        FROM coaching_sesiones
        WHERE usuario_id = $1
        ORDER BY creado_en DESC
        """,
        usuario_id,
    )
    return [dict(f) for f in filas]
