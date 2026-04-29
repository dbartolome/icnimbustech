"""
Jobs asíncronos para generación de documentos de cuenta:
PDF, PPTX, Briefing de voz y Estudio IA cross-selling.

Patrón idéntico al de informes: BackgroundTask + dict en memoria + polling.
"""

from __future__ import annotations

import asyncio
import json
import traceback
import uuid
from typing import Any
from uuid import UUID

import structlog

from app.config import configuracion

logger = structlog.get_logger()

# Estado en memoria — suficiente para el MVP (proceso único)
_jobs: dict[str, dict[str, Any]] = {}


def crear_job(tipo: str, titulo: str) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "tipo": tipo,
        "titulo": titulo,
        "estado": "pendiente",
        "progreso": 0,
        "paso_actual": "Iniciando…",
        "url_descarga": None,
        "error": None,
    }
    return job_id


def estado_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _upd(job_id: str, **kwargs: Any) -> None:
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)


async def _buscar_artefacto_por_documento(
    conn: Any,
    doc_id: UUID | None,
) -> str | None:
    if not doc_id:
        return None
    artefacto_id = await conn.fetchval(
        """
        SELECT id::TEXT
        FROM ia_artefactos
        WHERE origen_tabla = 'historial_documentos'
          AND origen_id = $1
          AND eliminado_en IS NULL
        ORDER BY actualizado_en DESC, creado_en DESC
        LIMIT 1
        """,
        str(doc_id),
    )
    return artefacto_id


# ── Tarea: Investigación de empresa ──────────────────────────────────────────

async def tarea_investigacion(
    job_id: str,
    cuenta_id: UUID,
    db_url: str,
) -> None:
    import asyncpg

    conn = None
    try:
        _upd(job_id, estado="investigando", progreso=5, paso_actual="Conectando…")
        conn = await asyncpg.connect(db_url.replace("+asyncpg", ""))

        nombre = await conn.fetchval(
            "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
        )
        if not nombre:
            raise ValueError(f"Cuenta {cuenta_id} no encontrada")

        _upd(job_id, progreso=15, paso_actual=f"Buscando información pública de {nombre}…",
             titulo=f"Investigación · {nombre}")

        from app.agents.investigador_web import InvestigadorWeb
        agente = InvestigadorWeb()
        resultado = await agente.run({"cuenta_id": str(cuenta_id)}, conn)

        if not resultado.exito:
            raise Exception(resultado.error or "Investigación fallida")

        investigacion_id = resultado.datos.get("investigacion_id")
        _upd(job_id, estado="completado", progreso=100,
             paso_actual="Investigación completada",
             resultado={"investigacion_id": investigacion_id})

    except BaseException as e:
        msg = str(e) or repr(e) or type(e).__name__
        logger.error("tarea_investigacion error", cuenta_id=str(cuenta_id), tipo=type(e).__name__, error=msg)
        _upd(job_id, estado="error", paso_actual=f"{type(e).__name__}: {msg}", error=msg)
    finally:
        if conn:
            await conn.close()


# ── Helper: asegurar propuesta disponible ────────────────────────────────────

def _normalizar_estrategia_ia(estrategia_ia: str) -> str:
    estrategia = (estrategia_ia or "").strip().lower()
    if estrategia not in {"rapida", "completa"}:
        return "rapida"
    return estrategia


async def _generar_propuesta_ia(conn, cuenta_id: UUID, job_id: str) -> None:
    from app.agents.orchestrator import Orchestrator

    inv_id = await conn.fetchval(
        """
        SELECT id FROM investigaciones_empresa
        WHERE cuenta_id = $1 AND estado = 'completada'
        ORDER BY completado_en DESC NULLS LAST, creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )

    orquestador = Orchestrator()

    if inv_id:
        _upd(job_id, paso_actual="Generando propuesta comercial con IA…", progreso=20)
        resultado = await orquestador.solo_propuesta(cuenta_id, str(inv_id), conn)
    else:
        _upd(job_id, paso_actual="Investigando empresa con IA…", progreso=10)
        resultado = await orquestador.pipeline_completo(cuenta_id, conn, forzar_reinvestigacion=False)

    if not resultado.exito:
        raise ValueError(resultado.error or "No se pudo generar la propuesta")


async def _crear_propuesta_fallback(conn, cuenta_id: UUID, motivo: str) -> None:
    """
    Genera una propuesta mínima determinista para no bloquear la exportación.
    Se usa solo como degradación controlada del MVP.
    """
    existente = await conn.fetchval(
        "SELECT id FROM propuestas_comerciales WHERE cuenta_id = $1 AND estado = 'completada' LIMIT 1",
        cuenta_id,
    )
    if existente:
        return

    cuenta = await conn.fetchrow(
        """
        SELECT
            c.nombre,
            ie.id AS investigacion_id,
            COALESCE(ie.sector, 'Sin clasificar') AS sector,
            COALESCE(ie.pain_points, '[]'::jsonb) AS pain_points,
            COALESCE(SUM(o.importe) FILTER (
                WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
            ), 0) AS pipeline_activo,
            COUNT(o.id) FILTER (
                WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
            ) AS ops_activas
        FROM cuentas c
        LEFT JOIN LATERAL (
            SELECT id, sector, pain_points
            FROM investigaciones_empresa
            WHERE cuenta_id = c.id AND estado = 'completada'
            ORDER BY completado_en DESC NULLS LAST, creado_en DESC
            LIMIT 1
        ) ie ON TRUE
        LEFT JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
        WHERE c.id = $1 AND c.eliminado_en IS NULL
        GROUP BY c.nombre, ie.id, ie.sector, ie.pain_points
        """,
        cuenta_id,
    )
    if not cuenta:
        raise ValueError(f"Cuenta {cuenta_id} no encontrada")

    productos_rows = await conn.fetch(
        """
        SELECT COALESCE(p.nombre, o.linea_negocio, 'Servicio SGS') AS nombre_producto,
               COALESCE(SUM(o.importe), 0) AS importe_total
        FROM oportunidades o
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.cuenta_id = $1
          AND o.eliminado_en IS NULL
          AND o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
        GROUP BY COALESCE(p.nombre, o.linea_negocio, 'Servicio SGS')
        ORDER BY importe_total DESC, nombre_producto
        LIMIT 3
        """,
        cuenta_id,
    )

    productos_recomendados: list[dict[str, Any]] = []
    if productos_rows:
        base_score = 88
        for idx, row in enumerate(productos_rows):
            nombre_producto = row["nombre_producto"] or "Servicio SGS"
            score_fit = max(60, base_score - (idx * 10))
            productos_recomendados.append(
                {
                    "producto": nombre_producto,
                    "score_fit": score_fit,
                    "argumentario": f"Priorizar {nombre_producto} por encaje con el pipeline activo actual.",
                    "norma": nombre_producto,
                }
            )
    else:
        productos_recomendados = [
            {
                "producto": "ISO 9001:2015",
                "score_fit": 72,
                "argumentario": "Entrada recomendada para activar conversación de mejora continua.",
                "norma": "ISO 9001:2015",
            }
        ]

    pipeline_activo = float(cuenta["pipeline_activo"] or 0)
    ops_activas = int(cuenta["ops_activas"] or 0)
    base_importe = pipeline_activo if pipeline_activo > 0 else (20000.0 if ops_activas > 0 else 12000.0)

    escenario_optimista = {
        "importe": round(base_importe * 1.20, 2),
        "productos": [p["producto"] for p in productos_recomendados[:3]],
        "probabilidad": 45,
        "plazo_meses": 4,
        "descripcion": "Escenario de aceleración comercial con foco en cierre corto.",
    }
    escenario_medio = {
        "importe": round(base_importe * 0.85, 2),
        "productos": [p["producto"] for p in productos_recomendados[:2]],
        "probabilidad": 60,
        "plazo_meses": 6,
        "descripcion": "Escenario base recomendado para seguimiento operativo del comercial.",
    }
    escenario_pesimista = {
        "importe": round(base_importe * 0.55, 2),
        "productos": [p["producto"] for p in productos_recomendados[:1]],
        "probabilidad": 30,
        "plazo_meses": 8,
        "descripcion": "Escenario conservador ante ciclos de decisión más largos.",
    }

    plan_de_accion = [
        {"accion": "Validar decisor y alcance técnico en la próxima llamada.", "prioridad": 1, "tipo": "nuevo", "plazo_dias": 3},
        {"accion": "Presentar propuesta económica y calendario de implantación.", "prioridad": 2, "tipo": "nuevo", "plazo_dias": 7},
        {"accion": "Cerrar próximos pasos y fecha objetivo de decisión.", "prioridad": 3, "tipo": "upselling", "plazo_dias": 14},
    ]

    sector = cuenta["sector"] or "Sin clasificar"
    argumentario_general = (
        f"Propuesta generada en modo rápido para la cuenta {cuenta['nombre']} ({sector}). "
        f"Se recomienda centrar la reunión en impacto económico, riesgo operativo y plan de implantación por fases. "
        f"Motivo de fallback: {motivo}."
    )

    await conn.execute(
        """
        INSERT INTO propuestas_comerciales (
            cuenta_id,
            investigacion_id,
            estado,
            productos_recomendados,
            escenario_optimista,
            escenario_medio,
            escenario_pesimista,
            plan_de_accion,
            argumentario_general,
            modelo_usado,
            iniciado_en,
            completado_en
        )
        VALUES ($1, $2, 'completada', $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9, now(), now())
        """,
        cuenta_id,
        cuenta["investigacion_id"],
        json.dumps(productos_recomendados, ensure_ascii=False),
        json.dumps(escenario_optimista, ensure_ascii=False),
        json.dumps(escenario_medio, ensure_ascii=False),
        json.dumps(escenario_pesimista, ensure_ascii=False),
        json.dumps(plan_de_accion, ensure_ascii=False),
        argumentario_general,
        "fallback-mvp-v1",
    )


async def _asegurar_propuesta(conn, cuenta_id: UUID, job_id: str, estrategia_ia: str = "rapida") -> None:
    """
    Si no hay propuesta completada, genera una automáticamente antes de crear
    el documento. Usa investigación existente si la hay, si no ejecuta pipeline completo.
    """
    tiene_propuesta = await conn.fetchval(
        "SELECT id FROM propuestas_comerciales WHERE cuenta_id = $1 AND estado = 'completada' LIMIT 1",
        cuenta_id,
    )
    if tiene_propuesta:
        return  # Ya hay propuesta, nada que hacer

    estrategia = _normalizar_estrategia_ia(estrategia_ia)
    timeout_ia = 18 if estrategia == "rapida" else 90
    error_ia = ""

    try:
        await asyncio.wait_for(_generar_propuesta_ia(conn, cuenta_id, job_id), timeout=timeout_ia)
    except Exception as exc:
        error_ia = str(exc) or type(exc).__name__
        logger.warning(
            "documentos_jobs propuesta ia fallback",
            cuenta_id=str(cuenta_id),
            estrategia_ia=estrategia,
            error=error_ia,
        )
        _upd(job_id, progreso=28, paso_actual="IA lenta/no disponible. Aplicando modo rápido de propuesta…")
        await _crear_propuesta_fallback(conn, cuenta_id, motivo=error_ia[:220])

    tiene_propuesta = await conn.fetchval(
        "SELECT id FROM propuestas_comerciales WHERE cuenta_id = $1 AND estado = 'completada' LIMIT 1",
        cuenta_id,
    )
    if not tiene_propuesta:
        raise ValueError(f"No se pudo generar la propuesta: {error_ia or 'sin propuesta disponible'}")


async def _generar_briefing_fallback(conn, cuenta_id: UUID, motivo: str) -> str:
    """
    Briefing de degradación controlada cuando la IA no responde.
    Mantiene el flujo comercial operativo y evita jobs en error.
    """
    fila = await conn.fetchrow(
        """
        SELECT
            c.nombre AS nombre_cuenta,
            COALESCE(pc.escenario_medio, '{}'::jsonb) AS escenario_medio,
            COALESCE(pc.productos_recomendados, '[]'::jsonb) AS productos_recomendados,
            COALESCE(pc.plan_de_accion, '[]'::jsonb) AS plan_de_accion
        FROM cuentas c
        LEFT JOIN LATERAL (
            SELECT escenario_medio, productos_recomendados, plan_de_accion
            FROM propuestas_comerciales
            WHERE cuenta_id = c.id AND estado = 'completada'
            ORDER BY completado_en DESC NULLS LAST, creado_en DESC
            LIMIT 1
        ) pc ON TRUE
        WHERE c.id = $1 AND c.eliminado_en IS NULL
        """,
        cuenta_id,
    )
    if not fila:
        return (
            "Briefing rápido: prepara una apertura de valor, valida el decisor, "
            "confirma alcance y cierra próximos pasos con fecha."
        )

    def _to_json(valor, default):
        if isinstance(valor, (dict, list)):
            return valor
        if isinstance(valor, str):
            try:
                return json.loads(valor)
            except Exception:
                return default
        return default

    escenario = _to_json(fila["escenario_medio"], {})
    productos = _to_json(fila["productos_recomendados"], [])
    plan = _to_json(fila["plan_de_accion"], [])

    productos_txt = ", ".join(
        p.get("producto", "Servicio SGS")
        for p in productos[:2]
        if isinstance(p, dict)
    ) or "servicios SGS con mejor encaje"
    accion = (
        plan[0].get("accion", "cerrar próximos pasos de decisión")
        if plan and isinstance(plan[0], dict)
        else "cerrar próximos pasos de decisión"
    )
    importe = escenario.get("importe", 0)
    plazo = escenario.get("plazo_meses", 6)
    prob = escenario.get("probabilidad", 50)

    return (
        f"Tu próxima visita a {fila['nombre_cuenta']} debe centrarse en impacto y decisión. "
        f"Prioriza {productos_txt}. El escenario más probable es de {importe:,.0f} euros "
        f"en {plazo} meses con una probabilidad del {prob} por ciento. "
        f"Antes de salir, asegura {accion}. "
        f"Nota técnica: se aplicó modo de contingencia por timeout de IA ({motivo[:80]})."
    )


# ── Tarea: PDF ────────────────────────────────────────────────────────────────

async def tarea_pdf(
    job_id: str,
    cuenta_id: UUID,
    usuario_id: UUID,
    db_url: str,
    contexto: str | None = None,
    contexto_tipo: str = "cuenta",
    contexto_id: UUID | None = None,
    estrategia_ia: str = "rapida",
) -> None:
    import asyncpg
    from app.skills.generar_pdf import generar_pdf_cuenta
    from app.modules.historial import servicio as historial_servicio
    from app.modules.plantillas import servicio as plantillas_servicio

    conn = None
    try:
        _upd(job_id, estado="generando", progreso=5, paso_actual="Conectando a la base de datos…")
        conn = await asyncpg.connect(db_url.replace("+asyncpg", ""))

        await _asegurar_propuesta(conn, cuenta_id, job_id, estrategia_ia=estrategia_ia)

        _upd(job_id, progreso=50, paso_actual="Generando PDF…")
        contenido, nombre_fichero = await generar_pdf_cuenta(cuenta_id, conn)

        _upd(job_id, progreso=90, paso_actual="Registrando en historial…")
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conn, "pdf")
        metadatos: dict = {"foco": "cuenta"}
        if contexto:
            metadatos["contexto"] = contexto
        if plantilla_activa:
            metadatos["plantilla_id"] = str(plantilla_activa["id"])
            metadatos["plantilla_nombre"] = plantilla_activa["nombre"]
        registro_doc = await historial_servicio.registrar_documento(
            conn,
            cuenta_id=cuenta_id,
            usuario_id=usuario_id,
            tipo="pdf",
            nombre_fichero=nombre_fichero,
            contenido=contenido,
            contexto_tipo=contexto_tipo,
            contexto_id=contexto_id or cuenta_id,
            metadatos=metadatos,
        )
        doc_id = registro_doc.get("id") if isinstance(registro_doc, dict) else None

        artefacto_id = await _buscar_artefacto_por_documento(conn, doc_id)
        _upd(
            job_id,
            estado="completado",
            progreso=100,
            paso_actual="PDF listo",
            url_descarga=str(doc_id) if doc_id else None,
            artefacto_id=artefacto_id,
        )

    except Exception as e:
        msg = str(e) or repr(e) or type(e).__name__
        logger.error("tarea_pdf error", cuenta_id=str(cuenta_id), tipo=type(e).__name__, error=msg,
                     tb=traceback.format_exc())
        _upd(job_id, estado="error", paso_actual=f"Error: {msg}", error=msg)
    finally:
        if conn:
            await conn.close()


# ── Tarea: PPTX ───────────────────────────────────────────────────────────────

async def tarea_pptx(
    job_id: str,
    cuenta_id: UUID,
    usuario_id: UUID,
    db_url: str,
    contexto: str | None = None,
    contexto_tipo: str = "cuenta",
    contexto_id: UUID | None = None,
    estrategia_ia: str = "rapida",
) -> None:
    import asyncpg
    from app.skills.generar_pptx import generar_pptx_cuenta
    from app.modules.historial import servicio as historial_servicio
    from app.modules.plantillas import servicio as plantillas_servicio

    conn = None
    try:
        _upd(job_id, estado="generando", progreso=5, paso_actual="Conectando a la base de datos…")
        conn = await asyncpg.connect(db_url.replace("+asyncpg", ""))

        await _asegurar_propuesta(conn, cuenta_id, job_id, estrategia_ia=estrategia_ia)

        _upd(job_id, progreso=50, paso_actual="Generando presentación…")
        contenido, nombre_fichero = await generar_pptx_cuenta(cuenta_id, conn)

        _upd(job_id, progreso=90, paso_actual="Registrando en historial…")
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conn, "pptx")
        metadatos: dict = {"foco": "cuenta"}
        if contexto:
            metadatos["contexto"] = contexto
        if plantilla_activa:
            metadatos["plantilla_id"] = str(plantilla_activa["id"])
            metadatos["plantilla_nombre"] = plantilla_activa["nombre"]
        registro_doc = await historial_servicio.registrar_documento(
            conn,
            cuenta_id=cuenta_id,
            usuario_id=usuario_id,
            tipo="pptx",
            nombre_fichero=nombre_fichero,
            contenido=contenido,
            contexto_tipo=contexto_tipo,
            contexto_id=contexto_id or cuenta_id,
            metadatos=metadatos,
        )
        doc_id = registro_doc.get("id") if isinstance(registro_doc, dict) else None

        artefacto_id = await _buscar_artefacto_por_documento(conn, doc_id)
        _upd(
            job_id,
            estado="completado",
            progreso=100,
            paso_actual="Presentación lista",
            url_descarga=str(doc_id) if doc_id else None,
            artefacto_id=artefacto_id,
        )

    except Exception as e:
        msg = str(e) or repr(e) or type(e).__name__
        logger.error("tarea_pptx error", cuenta_id=str(cuenta_id), tipo=type(e).__name__, error=msg,
                     tb=traceback.format_exc())
        _upd(job_id, estado="error", paso_actual=f"Error: {msg}", error=msg)
    finally:
        if conn:
            await conn.close()


# ── Tarea: Briefing de voz ────────────────────────────────────────────────────

async def tarea_briefing(
    job_id: str,
    cuenta_id: UUID,
    usuario_id: UUID,
    db_url: str,
    contexto: str | None = None,
    contexto_tipo: str = "cuenta",
    contexto_id: UUID | None = None,
    estrategia_ia: str = "rapida",
) -> None:
    import asyncpg
    from datetime import date
    from app.skills.generar_audio import generar_audio_cuenta
    from app.modules.historial import servicio as historial_servicio
    from app.agents.base import ConfigAgente
    from app.modules.ia.proveedores import obtener_configs_operacionales
    from app.modules.plantillas import servicio as plantillas_servicio

    conn = None
    try:
        _upd(job_id, estado="generando", progreso=5, paso_actual="Conectando a la base de datos…")
        conn = await asyncpg.connect(db_url.replace("+asyncpg", ""))

        await _asegurar_propuesta(conn, cuenta_id, job_id, estrategia_ia=estrategia_ia)

        _upd(job_id, progreso=50, paso_actual="Generando script de voz con IA…")

        # Cargar config Ollama para voice desde el runtime (evitar defaults rotos)
        cfg_runtime = obtener_configs_operacionales().get("voice", {})
        config_agente = ConfigAgente(
            proveedor="ollama",
            ollama_url=cfg_runtime.get("ollama_url") or configuracion.OLLAMA_URL,
            ollama_modelo=cfg_runtime.get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT,
        )

        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conn, "briefing")
        instrucciones_extra = None
        if plantilla_activa and isinstance(plantilla_activa.get("contenido"), dict):
            instrucciones_extra = plantilla_activa["contenido"].get("prompt_base")

        timeout_briefing = 20 if _normalizar_estrategia_ia(estrategia_ia) == "rapida" else 60
        fallback_ia = False
        try:
            script = await asyncio.wait_for(
                generar_audio_cuenta(
                    cuenta_id,
                    conn,
                    config=config_agente,
                    instrucciones_extra=instrucciones_extra,
                ),
                timeout=timeout_briefing,
            )
            if not str(script).strip():
                raise ValueError("Respuesta vacía en briefing IA")
        except Exception as exc:
            fallback_ia = True
            motivo = str(exc) or type(exc).__name__
            logger.warning(
                "tarea_briefing fallback",
                cuenta_id=str(cuenta_id),
                tipo=type(exc).__name__,
                error=motivo,
            )
            _upd(
                job_id,
                progreso=70,
                paso_actual="IA lenta/no disponible. Generando briefing de contingencia…",
            )
            script = await _generar_briefing_fallback(conn, cuenta_id, motivo)

        _upd(job_id, progreso=90, paso_actual="Registrando en historial…")
        nombre_fichero = f"briefing_{str(cuenta_id)[:8]}_{date.today().isoformat()}.txt"
        metadatos_briefing: dict = {"foco": "cuenta"}
        if contexto:
            metadatos_briefing["contexto"] = contexto
        if plantilla_activa:
            metadatos_briefing["plantilla_id"] = str(plantilla_activa["id"])
            metadatos_briefing["plantilla_nombre"] = plantilla_activa["nombre"]
        if fallback_ia:
            metadatos_briefing["fallback_ia"] = True
        registro_doc = await historial_servicio.registrar_documento(
            conn,
            cuenta_id=cuenta_id,
            usuario_id=usuario_id,
            tipo="briefing",
            nombre_fichero=nombre_fichero,
            contenido=script.encode("utf-8"),
            contexto_tipo=contexto_tipo,
            contexto_id=contexto_id or cuenta_id,
            metadatos=metadatos_briefing,
        )
        doc_id = registro_doc.get("id") if isinstance(registro_doc, dict) else None

        artefacto_id = await _buscar_artefacto_por_documento(conn, doc_id)

        # Auto-generar MP3 del briefing (fallo silencioso — no bloquea el resultado)
        try:
            _upd(job_id, progreso=95, paso_actual="Generando audio MP3…")
            from app.config import configuracion as cfg

            if cfg.OPENAI_API_KEY:
                from openai import AsyncOpenAI
                cliente_openai = AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
                respuesta_tts = await cliente_openai.audio.speech.create(
                    model="tts-1", voice="onyx",
                    input=script, response_format="mp3",
                )
                audio_bytes = respuesta_tts.content
                metadatos_tts: dict = {"voz": "onyx", "motor": "openai-tts-1"}
            else:
                import tempfile, os
                import edge_tts
                voz = "es-ES-AlvaroNeural"
                communicate = edge_tts.Communicate(script, voz)
                tmp_path = tempfile.mktemp(suffix=".mp3")
                await communicate.save(tmp_path)
                with open(tmp_path, "rb") as f:
                    audio_bytes = f.read()
                os.unlink(tmp_path)
                metadatos_tts = {"voz": voz, "motor": "edge-tts"}

            nombre_mp3 = nombre_fichero.replace(".txt", "") + ".mp3"
            registro_audio = await historial_servicio.registrar_documento(
                conn,
                cuenta_id=cuenta_id,
                usuario_id=usuario_id,
                tipo="audio",
                nombre_fichero=nombre_mp3,
                contenido=audio_bytes,
                contexto_tipo=contexto_tipo,
                contexto_id=contexto_id or cuenta_id,
                metadatos={"audio_origen_id": str(doc_id), **metadatos_tts},
            )
            if doc_id and registro_audio.get("id"):
                await conn.execute(
                    "UPDATE historial_documentos SET audio_origen_id = $1 WHERE id = $2",
                    doc_id, registro_audio["id"],
                )
        except Exception as exc:
            logger.warning("tarea_briefing audio fallido", cuenta_id=str(cuenta_id), error=str(exc))

        _upd(
            job_id,
            estado="completado",
            progreso=100,
            paso_actual="Briefing y audio listos",
            url_descarga=str(doc_id) if doc_id else None,
            artefacto_id=artefacto_id,
        )

    except Exception as e:
        msg = str(e) or repr(e) or type(e).__name__
        logger.error("tarea_briefing error", cuenta_id=str(cuenta_id), tipo=type(e).__name__, error=msg)
        _upd(job_id, estado="error", paso_actual=f"Error: {msg}", error=msg)
    finally:
        if conn:
            await conn.close()


# ── Tarea: Estudio IA cross-selling ──────────────────────────────────────────

async def tarea_estudio_ia(
    job_id: str,
    cuenta_id: UUID,
    usuario_id: UUID,
    db_url: str,
) -> None:
    import asyncpg
    import json

    conn = None
    try:
        _upd(job_id, estado="analizando", progreso=5, paso_actual="Conectando a la base de datos…")
        conn = await asyncpg.connect(db_url.replace("+asyncpg", ""))

        _upd(job_id, progreso=10, paso_actual="Leyendo datos de la cuenta…")

        cuenta = await conn.fetchrow(
            """
            SELECT c.nombre,
                   COALESCE(ie.sector, 'Sin clasificar') AS sector,
                   COUNT(o.id) AS ops_abiertas,
                   COALESCE(SUM(o.importe) FILTER (
                       WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                   ), 0) AS pipeline_activo,
                   STRING_AGG(DISTINCT p.nombre, ', ') FILTER (WHERE p.nombre IS NOT NULL) AS productos_actuales
            FROM cuentas c
            LEFT JOIN investigaciones_empresa ie ON ie.cuenta_id = c.id
            LEFT JOIN oportunidades o ON o.cuenta_id = c.id AND o.eliminado_en IS NULL
            LEFT JOIN productos p ON p.id = o.producto_id
            WHERE c.id = $1
            GROUP BY c.nombre, ie.sector
            """,
            cuenta_id,
        )
        if not cuenta:
            raise ValueError(f"Cuenta {cuenta_id} no encontrada")

        nombre = cuenta["nombre"]
        sector = cuenta["sector"] or "Sin clasificar"
        ops = cuenta["ops_abiertas"] or 0
        pipeline = float(cuenta["pipeline_activo"] or 0)
        productos = cuenta["productos_actuales"] or "Sin datos"

        _upd(job_id, progreso=25, paso_actual="Consultando IA para análisis de oportunidades…")

        from app.modules.ia.servicio import ConfigIA, llamar_ia
        from app.modules.ia.proveedores import obtener_configs_operacionales
        cfg_runtime = obtener_configs_operacionales().get("cross_selling", {})
        config = ConfigIA(
            proveedor=cfg_runtime.get("proveedor", "ollama"),
            ollama_url=cfg_runtime.get("ollama_url") or configuracion.OLLAMA_URL,
            ollama_modelo=cfg_runtime.get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT,
        )

        prompt = f"""SGS España cross-selling. Responde SOLO con JSON sin texto extra.

CUENTA:{nombre} SECTOR:{sector} OPS:{ops} PIPELINE:{pipeline:,.0f}€ PRODUCTOS:{productos}

{{"resumen":"1 frase del potencial","oportunidades":[{{"producto":"...","urgencia":"alta|media|baja"}},{{"producto":"...","urgencia":"alta|media|baja"}}],"mensaje":"1 frase apertura comercial","confianza":"Alta|Media|Baja"}}"""

        _upd(job_id, progreso=30, paso_actual=f"IA analizando {nombre}…")
        respuesta = await llamar_ia(
            mensajes=[{"role": "user", "content": prompt}],
            system="",
            config=config,
            max_tokens=200,
        )

        _upd(job_id, progreso=70, paso_actual="Procesando análisis…")

        respuesta_limpia = respuesta.replace("```json", "").replace("```", "").strip()
        analisis = json.loads(respuesta_limpia)

        _upd(job_id, progreso=85, paso_actual="Guardando análisis…")

        await conn.execute(
            """
            INSERT INTO estudios_ia_cuentas (cuenta_id, usuario_id, analisis)
            VALUES ($1, $2, $3::jsonb)
            """,
            cuenta_id,
            usuario_id,
            json.dumps(analisis, ensure_ascii=False),
        )

        _upd(job_id, estado="completado", progreso=100,
             paso_actual="Estudio listo", resultado=analisis)

    except BaseException as e:
        msg = str(e) or repr(e) or type(e).__name__
        logger.error("tarea_estudio_ia error", cuenta_id=str(cuenta_id), tipo=type(e).__name__, error=msg)
        _upd(job_id, estado="error", paso_actual=f"{type(e).__name__}: {msg}", error=msg)
    finally:
        if conn:
            await conn.close()
