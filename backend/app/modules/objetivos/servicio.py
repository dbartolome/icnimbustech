"""Lógica de negocio del módulo objetivos comerciales."""

import json
from uuid import UUID

import asyncpg

from app.modules.objetivos.schemas import ObjetivoComercialCreate, ObjetivoComercialUpdate

_ETAPAS_CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")


def _normalizar_metadatos(valor) -> dict:
    """Garantiza dict para respuesta API aunque BD devuelva JSON serializado como texto."""
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            convertido = json.loads(valor)
            return convertido if isinstance(convertido, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _orden_seguro(sort_by: str, sort_dir: str) -> tuple[str, str]:
    campos = {
        "creado_en": "o.creado_en",
        "actualizado_en": "o.actualizado_en",
        "prioridad": "o.prioridad",
        "estado": "o.estado",
        "score_impacto": "o.score_impacto",
        "score_confianza": "o.score_confianza",
        "fecha_objetivo": "o.fecha_objetivo",
        "titulo": "o.titulo",
        "artefactos_total": "COALESCE(oa.total, 0)",
    }
    campo = campos.get((sort_by or "").lower(), "o.score_impacto")
    direccion = "ASC" if (sort_dir or "").lower() == "asc" else "DESC"
    return campo, direccion


async def listar_objetivos(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    es_manager: bool,
    estado: str | None,
    cuenta_id: UUID | None,
    oportunidad_id: UUID | None,
    propietario_id: UUID | None,
    busqueda: str | None,
    pagina: int,
    por_pagina: int,
    sort_by: str,
    sort_dir: str,
) -> dict:
    condiciones = ["o.eliminado_en IS NULL"]
    args: list = []

    if not es_manager:
        args.append(usuario_id)
        condiciones.append(f"o.usuario_id = ${len(args)}")
    elif propietario_id:
        args.append(propietario_id)
        condiciones.append(f"o.usuario_id = ${len(args)}")

    if estado:
        args.append(estado)
        condiciones.append(f"o.estado = ${len(args)}")
    if cuenta_id:
        args.append(cuenta_id)
        condiciones.append(f"o.cuenta_id = ${len(args)}")
    if oportunidad_id:
        args.append(oportunidad_id)
        condiciones.append(f"o.oportunidad_id = ${len(args)}")
    if busqueda:
        args.append(f"%{busqueda}%")
        condiciones.append(f"(o.titulo ILIKE ${len(args)} OR o.descripcion ILIKE ${len(args)})")

    where = "WHERE " + " AND ".join(condiciones)
    campo, direccion = _orden_seguro(sort_by, sort_dir)
    offset = (pagina - 1) * por_pagina

    total = await conexion.fetchval(f"SELECT COUNT(*) FROM objetivos_comerciales o {where}", *args)

    filas = await conexion.fetch(
        f"""
        SELECT
            o.id, o.usuario_id, o.cuenta_id, c.nombre AS cuenta_nombre,
            o.oportunidad_id, op.nombre AS oportunidad_nombre,
            o.tipo_objetivo, o.origen, o.titulo, o.descripcion,
            o.prioridad, o.estado, o.fecha_objetivo,
            o.score_impacto, o.score_confianza, o.cross_sell_ref, o.metadatos,
            COALESCE(oa.total, 0) AS artefactos_total,
            o.creado_en::TEXT AS creado_en,
            o.actualizado_en::TEXT AS actualizado_en
        FROM objetivos_comerciales o
        LEFT JOIN cuentas c ON c.id = o.cuenta_id
        LEFT JOIN oportunidades op ON op.id = o.oportunidad_id
        LEFT JOIN LATERAL (
            SELECT COUNT(*)::INT AS total
            FROM objetivo_artefactos_ia oi
            JOIN ia_artefactos ia ON ia.id = oi.artefacto_id AND ia.eliminado_en IS NULL
            WHERE oi.objetivo_id = o.id
        ) oa ON TRUE
        {where}
        ORDER BY {campo} {direccion} NULLS LAST, o.id DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        por_pagina,
        offset,
    )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [
            {
                **dict(f),
                "metadatos": _normalizar_metadatos(f["metadatos"]),
            }
            for f in filas
        ],
    }


async def _resolver_cuenta_por_oportunidad(
    conexion: asyncpg.Connection,
    oportunidad_id: UUID,
) -> UUID | None:
    return await conexion.fetchval(
        "SELECT cuenta_id FROM oportunidades WHERE id = $1 AND eliminado_en IS NULL",
        oportunidad_id,
    )


async def crear_objetivo(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    payload: ObjetivoComercialCreate,
) -> dict:
    cuenta_id = payload.cuenta_id
    if not cuenta_id and payload.oportunidad_id:
        cuenta_id = await _resolver_cuenta_por_oportunidad(conexion, payload.oportunidad_id)

    fila = await conexion.fetchrow(
        """
        INSERT INTO objetivos_comerciales
            (usuario_id, cuenta_id, oportunidad_id, tipo_objetivo, origen, titulo,
             descripcion, prioridad, estado, fecha_objetivo)
        VALUES ($1, $2, $3, $4, 'manual', $5, $6, $7, 'abierto', $8)
        RETURNING id
        """,
        usuario_id,
        cuenta_id,
        payload.oportunidad_id,
        payload.tipo_objetivo,
        payload.titulo,
        payload.descripcion,
        payload.prioridad,
        payload.fecha_objetivo,
    )
    return await obtener_objetivo(conexion, objetivo_id=fila["id"], usuario_id=usuario_id, es_manager=True)


async def actualizar_objetivo(
    conexion: asyncpg.Connection,
    *,
    objetivo_id: UUID,
    usuario_id: UUID,
    es_manager: bool,
    payload: ObjetivoComercialUpdate,
) -> dict | None:
    campos = []
    valores: list = []
    idx = 1
    for campo in ("titulo", "descripcion", "prioridad", "estado", "fecha_objetivo", "score_impacto", "score_confianza"):
        valor = getattr(payload, campo)
        if valor is not None:
            campos.append(f"{campo} = ${idx}")
            valores.append(valor)
            idx += 1

    if not campos:
        return await obtener_objetivo(conexion, objetivo_id=objetivo_id, usuario_id=usuario_id, es_manager=es_manager)

    scope_sql = "" if es_manager else f" AND usuario_id = ${idx + 1}"
    valores.extend([objetivo_id, usuario_id] if not es_manager else [objetivo_id])

    res = await conexion.execute(
        f"""
        UPDATE objetivos_comerciales
        SET {', '.join(campos)}
        WHERE id = ${idx} AND eliminado_en IS NULL{scope_sql}
        """,
        *valores,
    )
    if res == "UPDATE 0":
        return None
    return await obtener_objetivo(conexion, objetivo_id=objetivo_id, usuario_id=usuario_id, es_manager=es_manager)


async def eliminar_objetivo(
    conexion: asyncpg.Connection,
    *,
    objetivo_id: UUID,
    usuario_id: UUID,
    es_manager: bool,
) -> bool:
    scope_sql = "" if es_manager else " AND usuario_id = $3"
    args = [objetivo_id, "descartado"] if es_manager else [objetivo_id, "descartado", usuario_id]
    res = await conexion.execute(
        f"""
        UPDATE objetivos_comerciales
        SET estado = $2, eliminado_en = NOW()
        WHERE id = $1 AND eliminado_en IS NULL{scope_sql}
        """,
        *args,
    )
    return res == "UPDATE 1"


async def obtener_objetivo(
    conexion: asyncpg.Connection,
    *,
    objetivo_id: UUID,
    usuario_id: UUID,
    es_manager: bool,
) -> dict | None:
    scope_sql = "" if es_manager else " AND o.usuario_id = $2"
    args = [objetivo_id] if es_manager else [objetivo_id, usuario_id]

    fila = await conexion.fetchrow(
        f"""
        SELECT
            o.id, o.usuario_id, o.cuenta_id, c.nombre AS cuenta_nombre,
            o.oportunidad_id, op.nombre AS oportunidad_nombre,
            o.tipo_objetivo, o.origen, o.titulo, o.descripcion,
            o.prioridad, o.estado, o.fecha_objetivo,
            o.score_impacto, o.score_confianza, o.cross_sell_ref, o.metadatos,
            o.creado_en::TEXT AS creado_en,
            o.actualizado_en::TEXT AS actualizado_en
        FROM objetivos_comerciales o
        LEFT JOIN cuentas c ON c.id = o.cuenta_id
        LEFT JOIN oportunidades op ON op.id = o.oportunidad_id
        WHERE o.id = $1 AND o.eliminado_en IS NULL{scope_sql}
        """,
        *args,
    )
    if not fila:
        return None

    artefactos = await conexion.fetch(
        """
        SELECT
            a.id,
            a.tipo,
            a.subtipo,
            a.titulo,
            a.actualizado_en::TEXT AS actualizado_en,
            oa.tipo_relacion
        FROM objetivo_artefactos_ia oa
        JOIN ia_artefactos a ON a.id = oa.artefacto_id AND a.eliminado_en IS NULL
        WHERE oa.objetivo_id = $1
        ORDER BY a.actualizado_en DESC
        """,
        objetivo_id,
    )

    return {
        "objetivo": {
            **dict(fila),
            "metadatos": _normalizar_metadatos(fila["metadatos"]),
        },
        "artefactos": [dict(a) for a in artefactos],
    }


def _score_prioridad(etapa: str, importe: float, ranking: int | None, confianza: str | None) -> tuple[float, float, int]:
    etapa_factor = {
        "discover": 0.45,
        "propose": 0.70,
        "negotiate": 0.92,
        "in_progress": 0.60,
        "estimation_sent": 0.68,
        "technically_approved": 0.76,
        "contract_offer_sent": 0.85,
        "estimation_accepted": 0.95,
    }.get(etapa, 0.55)

    confianza_map = {
        "Alta": 0.95,
        "Media-Alta": 0.82,
        "Media": 0.68,
        "Media-Baja": 0.54,
        "Baja": 0.40,
    }
    conf = confianza_map.get(confianza or "", 0.55)
    ranking_bonus = 1.0
    if ranking is not None and ranking > 0:
        ranking_bonus = max(0.70, min(1.30, (11 - min(ranking, 10)) / 10 + 0.2))

    impacto_bruto = round((importe or 0) * etapa_factor * ranking_bonus, 2)
    # score_impacto se almacena en NUMERIC(6,2), máximo 9999.99
    impacto = round(min(9999.99, max(0.0, impacto_bruto / 10.0)), 2)
    score_confianza = round(conf * 100, 2)

    prioridad = 3
    if impacto_bruto >= 150000:
        prioridad = 1
    elif impacto_bruto >= 70000:
        prioridad = 2
    elif impacto_bruto >= 25000:
        prioridad = 3
    elif impacto_bruto >= 10000:
        prioridad = 4
    else:
        prioridad = 5

    return impacto, score_confianza, prioridad


async def sugerir_objetivos(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    limite: int,
    guardar: bool,
) -> list[dict]:
    filas = await conexion.fetch(
        """
        SELECT
            o.id AS oportunidad_id,
            o.nombre AS oportunidad_nombre,
            o.importe,
            o.etapa::TEXT AS etapa,
            c.id AS cuenta_id,
            c.nombre AS cuenta_nombre,
            xsi.ranking_accionable,
            xsi.confianza,
            xsi.trigger_activador,
            xsi.mensaje_comercial
        FROM oportunidades o
        LEFT JOIN cuentas c ON c.id = o.cuenta_id
        LEFT JOIN cross_selling_intelligence xsi
          ON LOWER(xsi.account_name) = LOWER(c.nombre)
        WHERE o.propietario_id = $1
          AND o.eliminado_en IS NULL
          AND o.etapa::TEXT NOT IN ('closed_won', 'closed_lost', 'closed_withdrawn')
        ORDER BY o.importe DESC NULLS LAST, o.fecha_decision ASC NULLS LAST
        LIMIT $2
        """,
        usuario_id,
        max(5, min(limite, 100)),
    )

    sugerencias: list[dict] = []
    for f in filas:
        impacto, confianza, prioridad = _score_prioridad(
            etapa=f["etapa"],
            importe=float(f["importe"] or 0),
            ranking=f["ranking_accionable"],
            confianza=f["confianza"],
        )
        tipo_objetivo = "cross_sell" if f["ranking_accionable"] else "cierre"
        titulo = f"{('Cross-sell' if tipo_objetivo == 'cross_sell' else 'Consolidar')} · {f['oportunidad_nombre']}"
        descripcion = (
            f"Cuenta: {f['cuenta_nombre'] or 'N/D'}. "
            f"Etapa actual: {f['etapa']}. "
            f"{(f['trigger_activador'] or 'Sin trigger específico')}. "
            f"{(f['mensaje_comercial'] or '')}"
        ).strip()

        item = {
            "oportunidad_id": f["oportunidad_id"],
            "oportunidad_nombre": f["oportunidad_nombre"],
            "cuenta_id": f["cuenta_id"],
            "cuenta_nombre": f["cuenta_nombre"],
            "tipo_objetivo": tipo_objetivo,
            "titulo": titulo,
            "descripcion": descripcion,
            "prioridad": prioridad,
            "score_impacto": impacto,
            "score_confianza": confianza,
            "cross_sell_ref": f"ranking:{f['ranking_accionable']}" if f["ranking_accionable"] else None,
        }
        sugerencias.append(item)

    if guardar and sugerencias:
        for s in sugerencias:
            existe = await conexion.fetchval(
                """
                SELECT 1
                FROM objetivos_comerciales
                WHERE usuario_id = $1
                  AND oportunidad_id = $2
                  AND tipo_objetivo = $3
                  AND eliminado_en IS NULL
                  AND estado IN ('abierto', 'en_progreso', 'bloqueado')
                LIMIT 1
                """,
                usuario_id,
                s["oportunidad_id"],
                s["tipo_objetivo"],
            )
            if existe:
                continue
            await conexion.execute(
                """
                INSERT INTO objetivos_comerciales
                    (usuario_id, cuenta_id, oportunidad_id, tipo_objetivo, origen, titulo,
                     descripcion, prioridad, estado, score_impacto, score_confianza, cross_sell_ref)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'abierto', $9, $10, $11)
                """,
                usuario_id,
                s["cuenta_id"],
                s["oportunidad_id"],
                s["tipo_objetivo"],
                "cross_selling" if s["tipo_objetivo"] == "cross_sell" else "sugerido_ia",
                s["titulo"],
                s["descripcion"],
                s["prioridad"],
                s["score_impacto"],
                s["score_confianza"],
                s["cross_sell_ref"],
            )

    return sugerencias


async def vincular_artefacto(
    conexion: asyncpg.Connection,
    *,
    objetivo_id: UUID,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_manager: bool,
    tipo_relacion: str = "generado",
) -> bool:
    scope_sql = "" if es_manager else " AND usuario_id = $2"
    permitido = await conexion.fetchval(
        f"SELECT 1 FROM objetivos_comerciales WHERE id = $1 AND eliminado_en IS NULL{scope_sql}",
        objetivo_id,
        *([] if es_manager else [usuario_id]),
    )
    if not permitido:
        return False

    await conexion.execute(
        """
        INSERT INTO objetivo_artefactos_ia (objetivo_id, artefacto_id, tipo_relacion)
        VALUES ($1, $2, $3)
        ON CONFLICT (objetivo_id, artefacto_id) DO UPDATE SET tipo_relacion = EXCLUDED.tipo_relacion
        """,
        objetivo_id,
        artefacto_id,
        tipo_relacion,
    )
    return True
