"""
Lógica de negocio del módulo IA Copilot — REFACTORIZADO para Sprint 5.
KPIs en tiempo real desde DB, contexto de cuenta activa, historial persistido.
"""

import json
import logging
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import UUID

import anthropic
import asyncpg
import httpx

from app.config import configuracion
from app.modules.ia.proveedores import (
    PROVEEDOR_LOCAL,
    normalizar_ollama_url_operacional,
    obtener_api_key_externa,
)

logger = logging.getLogger(__name__)


# ── Compatibilidad con voice/servicio.py ──────────────────────────────────────
@dataclass
class ConfigIA:
    """Configuración de IA para voice/servicio.py (backward compatibility)."""
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT


async def obtener_kpis_pipeline(
    conexion: asyncpg.Connection,
    cuenta_id: UUID | None = None,
) -> dict:
    """Obtiene KPIs reales desde DB. Si cuenta_id, usa datos de esa cuenta."""
    _CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")

    if cuenta_id:
        # KPIs específicos de la cuenta
        fila = await conexion.fetchrow(
            f"""
            SELECT
                COUNT(*)                                                                      AS total,
                COUNT(*) FILTER (WHERE etapa NOT IN {_CERRADAS})                             AS activas,
                COALESCE(SUM(importe) FILTER (WHERE etapa NOT IN {_CERRADAS}), 0)            AS pipeline,
                COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_won'), 0)                AS ganado,
                COALESCE(
                    ROUND(
                        COUNT(*) FILTER (WHERE etapa = 'closed_won')::numeric
                        / NULLIF(COUNT(*) FILTER (WHERE etapa IN {_CERRADAS}), 0) * 100, 1
                    ), 0
                )                                                                              AS win_rate,
                COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 0)                AS ticket_medio
            FROM oportunidades
            WHERE cuenta_id = $1 AND eliminado_en IS NULL
            """,
            cuenta_id,
        )
    else:
        # KPIs globales del pipeline
        fila = await conexion.fetchrow(
            f"""
            SELECT
                COUNT(*)                                                                      AS total,
                COUNT(*) FILTER (WHERE etapa NOT IN {_CERRADAS})                             AS activas,
                COALESCE(SUM(importe) FILTER (WHERE etapa NOT IN {_CERRADAS}), 0)            AS pipeline,
                COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_won'), 0)                AS ganado,
                COALESCE(
                    ROUND(
                        COUNT(*) FILTER (WHERE etapa = 'closed_won')::numeric
                        / NULLIF(COUNT(*) FILTER (WHERE etapa IN {_CERRADAS}), 0) * 100, 1
                    ), 0
                )                                                                              AS win_rate,
                COALESCE(AVG(importe) FILTER (WHERE etapa = 'closed_won'), 0)                AS ticket_medio
            FROM oportunidades
            WHERE eliminado_en IS NULL
            """
        )

    return {
        "total_oportunidades": fila["total"] or 0,
        "activas": fila["activas"] or 0,
        "pipeline_activo": float(fila["pipeline"] or 0),
        "importe_ganado": float(fila["ganado"] or 0),
        "win_rate": float(fila["win_rate"] or 0),
        "ticket_medio": float(fila["ticket_medio"] or 0),
    }


async def construir_system_prompt(
    conexion: asyncpg.Connection,
    cuenta_id: UUID | None = None,
    contexto_comercial: str | None = None,
    modo_documento: bool = False,
) -> str:
    """
    Construye el system prompt dinámico con:
    - KPIs reales desde DB
    - Catálogo SGS
    - Matriz sectorial
    - Contexto de cuenta si existe
    """
    # 1. KPIs reales
    kpis = await obtener_kpis_pipeline(conexion, cuenta_id)

    # 2. Catálogo y matriz
    # En chat sobre documento priorizamos latencia: evitamos bloques largos.
    if modo_documento:
        catalogo_txt = "Modo documento: contexto comercial abreviado."
        matriz_txt = "Modo documento: foco en contenido adjunto."
    else:
        try:
            catalogo = await conexion.fetch(
                "SELECT linea, servicio, normas_clave FROM catalogo_servicios ORDER BY linea LIMIT 15"
            )
        except asyncpg.UndefinedTableError:
            logger.warning("Tabla catalogo_servicios no existe. Copilot sigue sin catálogo detallado.")
            catalogo = []
        catalogo_txt = "\n".join(
            f"• {r['linea']}: {r['servicio'][:100]} | Normas: {r['normas_clave'] or 'N/A'}"
            for r in catalogo
        ) if catalogo else "Catálogo no disponible"

        try:
            matriz = await conexion.fetch(
                "SELECT sector, certificaciones_tipo, pain_points FROM matriz_sectorial ORDER BY sector LIMIT 10"
            )
        except asyncpg.UndefinedTableError:
            logger.warning("Tabla matriz_sectorial no existe. Copilot sigue sin matriz sectorial.")
            matriz = []
        matriz_txt = "\n".join(
            f"• {r['sector']}: certs={r['certificaciones_tipo'][:80]} | pain points={r['pain_points'][:80]}"
            for r in matriz
        ) if matriz else "Matriz no disponible"

    # 3. Sistema base
    sistema = f"""Eres el Copilot de Inteligencia Comercial de SGS España.
Tienes acceso en tiempo real al pipeline comercial y datos de clientes.

DATOS DEL PIPELINE ACTUALES (en tiempo real):
- Total oportunidades: {kpis['total_oportunidades']:,}
- Oportunidades activas: {kpis['activas']:,}
- Pipeline activo: {kpis['pipeline_activo']:,.0f}€
- Importe ganado histórico: {kpis['importe_ganado']:,.0f}€
- Win Rate global: {kpis['win_rate']:.1f}%
- Ticket medio ganado: {kpis['ticket_medio']:,.0f}€

CATÁLOGO SGS ESPAÑA:
{catalogo_txt}

MATRIZ SECTORIAL (sector → certificaciones → pain points):
{matriz_txt}

INSTRUCCIONES:
- Responde siempre en español de España
- Sé conciso y directo, orientado a la toma de decisiones
- Usa datos reales del pipeline para contextualizar
- Cuando pregunten por un servicio, describe entregables y normas del catálogo
- Cuando pregunten por un sector, identifica certificaciones y pain points
- Si no tienes datos suficientes, indícalo claramente
- Sugiere acciones comerciales concretas basadas en los datos
"""

    # 4. Contexto de cuenta si existe
    if cuenta_id and contexto_comercial:
        sistema += f"\n\nCONTEXTO DE CUENTA ACTIVA:\n{contexto_comercial}"

    if modo_documento:
        sistema += (
            "\n\nMODO DOCUMENTO:\n"
            "- Prioriza responder usando el documento adjunto.\n"
            "- Si el dato no está en el documento, indícalo explícitamente.\n"
            "- Responde de forma breve y accionable."
        )

    return sistema


def _jsonb(valor, default):
    """Normaliza columnas JSONB que asyncpg puede devolver como str o como objeto Python."""
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (json.JSONDecodeError, ValueError):
            pass
    return default


async def obtener_contexto_cuenta(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
) -> str | None:
    """Obtiene el contexto comercial de una cuenta (propuesta + investigación)."""
    fila = await conexion.fetchrow(
        """
        SELECT
            c.nombre,
            pc.productos_recomendados, pc.escenario_medio,
            ie.sector, ie.certificaciones_actuales, ie.pain_points
        FROM cuentas c
        LEFT JOIN propuestas_comerciales pc ON pc.cuenta_id = c.id AND pc.estado = 'completada'
        LEFT JOIN investigaciones_empresa ie ON ie.id = pc.investigacion_id
        WHERE c.id = $1 AND c.eliminado_en IS NULL
        ORDER BY pc.creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        return None

    productos = _jsonb(fila["productos_recomendados"], [])
    productos_txt = ", ".join(
        p.get("producto", "") for p in productos[:3] if isinstance(p, dict)
    ) or "Por definir"
    esc_med = _jsonb(fila["escenario_medio"], {})
    certs = ", ".join(fila["certificaciones_actuales"] or []) or "Ninguna"
    pain_points = _jsonb(fila["pain_points"], [])
    pain = pain_points[0] if isinstance(pain_points, list) and pain_points else "No identificados"

    return f"""Empresa: {fila['nombre']}
Sector: {fila['sector'] or 'No identificado'}
Certificaciones actuales: {certs}
Principal pain point: {pain}
Propuesta activa: {productos_txt}
Escenario recomendado: {esc_med.get('importe', 0):,.0f}€ en {esc_med.get('plazo_meses', 0)} meses"""


async def guardar_conversacion(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    cuenta_id: UUID | None,
    rol_usuario: str,
    mensajes: list[dict],
    respuesta: str,
) -> UUID:
    """Persiste la conversación en DB para auditoría y aprendizaje."""
    fila = await conexion.fetchrow(
        """
        INSERT INTO conversaciones_ia
            (usuario_id, cuenta_id, rol_usuario, mensajes, respuesta, creado_en)
        VALUES ($1, $2, $3, $4::jsonb, $5, now())
        RETURNING id
        """,
        usuario_id,
        cuenta_id,
        rol_usuario,
        json.dumps(mensajes),
        respuesta,
    )
    conversacion_id: UUID = fila["id"]

    # Registrar como artefacto IA versionado (fallo silencioso para no romper chat).
    try:
        from app.modules.artefactos import servicio as artefactos_servicio

        clave = f"chat:{str(cuenta_id) if cuenta_id else 'global'}:{str(usuario_id)}"
        prompt_entrada = ""
        if mensajes:
            ultimo_usuario = next((m for m in reversed(mensajes) if m.get("role") == "user"), None)
            prompt_entrada = (ultimo_usuario or {}).get("content", "")

        await artefactos_servicio.registrar_version_artefacto(
            conexion,
            tipo="chat",
            subtipo="copilot",
            entidad_tipo="cuenta" if cuenta_id else "global",
            entidad_id=cuenta_id,
            cuenta_id=cuenta_id,
            usuario_id=usuario_id,
            titulo=f"Chat IA {'cuenta' if cuenta_id else 'global'}",
            prompt=prompt_entrada or None,
            resultado_texto=respuesta,
            resultado_json={"mensajes": mensajes[-8:]},
            storage_key=None,
            modelo=None,
            plantilla_id=None,
            metadatos={"clave_regeneracion": clave, "rol_usuario": rol_usuario},
            fuentes=[],
            origen_tabla="conversaciones_ia",
            origen_id=str(conversacion_id),
        )
    except Exception:
        pass

    return conversacion_id


async def chat_streaming(
    mensajes: list[dict],
    conexion: asyncpg.Connection,
    usuario_id: UUID | None = None,
    cuenta_id: UUID | None = None,
    rol_usuario: str = "comercial",
    proveedor: str = PROVEEDOR_LOCAL,
    ollama_url: str = configuracion.OLLAMA_URL,
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT,
    documento_texto: str | None = None,
) -> AsyncIterator[str]:
    """
    Chat con streaming. Sistema prompt dinámico con datos reales.
    Si documento_texto, añade el contenido al contexto para chat sobre el doc.
    Opcionalmente persiste en DB si usuario_id está presente.
    """
    # 1. Construir system prompt con datos reales
    sistema = await construir_system_prompt(
        conexion,
        cuenta_id,
        modo_documento=bool(documento_texto),
    )

    # 2. Inyectar contexto de cuenta si existe
    if cuenta_id:
        contexto = await obtener_contexto_cuenta(conexion, cuenta_id)
        if contexto:
            sistema += f"\n\nCONTEXTO DE CUENTA ACTIVA:\n{contexto}"

        # Añadir memoria IA relevante previa de la cuenta (si existe).
        try:
            from app.modules.artefactos import servicio as artefactos_servicio

            contexto_ia = await artefactos_servicio.obtener_contexto_relevante(
                conexion,
                usuario_id=usuario_id or UUID("00000000-0000-0000-0000-000000000000"),
                es_admin=True if usuario_id is None else (rol_usuario in {"admin", "manager"}),
                entidad_tipo="cuenta",
                entidad_id=cuenta_id,
                cuenta_id=cuenta_id,
                limit=6,
            )
            if contexto_ia:
                lineas = []
                for item in contexto_ia[:6]:
                    titulo = item.get("titulo", "Artefacto")
                    subtipo = item.get("subtipo", "")
                    resumen = (item.get("resultado_texto") or "")[:220]
                    lineas.append(f"- [{subtipo}] {titulo}: {resumen}")
                sistema += "\n\nMEMORIA IA RELEVANTE (contexto histórico):\n" + "\n".join(lineas)
        except Exception:
            pass

    # 3. Inyectar texto del documento si se proporciona
    if documento_texto:
        sistema += (
            "\n\nDOCUMENTO ADJUNTO (el usuario quiere hacer preguntas sobre este documento):\n"
            "--- INICIO DOCUMENTO ---\n"
            f"{documento_texto[:6000]}\n"
            "--- FIN DOCUMENTO ---\n"
            "Responde usando el contenido del documento y el contexto de la cuenta."
        )

    # 3. Llamar a IA con streaming
    if proveedor == "anthropic":
        api_key = obtener_api_key_externa("anthropic")
        cliente = anthropic.Anthropic(api_key=api_key)
        respuesta_completa = ""
        with cliente.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=sistema,
            messages=mensajes,
        ) as stream:
            for chunk in stream.text_stream:
                respuesta_completa += chunk
                yield chunk

        # 4. Persistir si usuario autenticado
        if usuario_id:
            await guardar_conversacion(
                conexion,
                usuario_id,
                cuenta_id,
                rol_usuario,
                mensajes,
                respuesta_completa,
            )
    elif proveedor == PROVEEDOR_LOCAL:
        # Usar URL/modelo del runtime config si el cliente no envía valores válidos
        from app.modules.ia.proveedores import obtener_configs_operacionales
        cfg_copilot = obtener_configs_operacionales().get("copilot", {})
        effective_url = normalizar_ollama_url_operacional(
            (ollama_url or "").strip() or cfg_copilot.get("ollama_url") or configuracion.OLLAMA_URL
        )
        effective_modelo = (ollama_modelo or "").strip() or cfg_copilot.get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT

        # Ollama local — con fallback entre endpoints
        base = effective_url.rstrip("/")
        msgs_payload = [{"role": "system", "content": sistema}, *mensajes]
        respuesta_completa = ""

        # Detectar qué endpoint soporta esta versión de Ollama
        # Probamos /v1/chat/completions (OpenAI-compat) → /api/chat (nativo)
        endpoint_detectado = None
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=5.0)) as probe:
            for ep in ["/v1/chat/completions", "/api/chat"]:
                try:
                    r = await probe.post(base + ep, json={"model": effective_modelo, "stream": False,
                        "messages": msgs_payload[:1], "max_tokens": 1, "options": {"num_predict": 1}})
                    if r.status_code != 404:
                        endpoint_detectado = ep
                        break
                except Exception:
                    continue
        if not endpoint_detectado:
            endpoint_detectado = "/api/generate"

        # read=120s: VPS sin GPU puede tardar 60-90s en generar el primer token
        timeout_stream = httpx.Timeout(connect=10.0, read=120.0, write=20.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout_stream) as cliente:
            if endpoint_detectado == "/v1/chat/completions":
                payload = {"model": effective_modelo, "stream": True, "messages": msgs_payload}
                async with cliente.stream("POST", base + endpoint_detectado, json=payload) as response:
                    response.raise_for_status()
                    async for linea in response.aiter_lines():
                        if not linea or linea == "data: [DONE]":
                            continue
                        texto = linea.removeprefix("data: ").strip()
                        if not texto:
                            continue
                        try:
                            dato = json.loads(texto)
                            delta = dato.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                respuesta_completa += delta
                                yield delta
                        except json.JSONDecodeError:
                            continue

            elif endpoint_detectado == "/api/chat":
                payload = {"model": effective_modelo, "stream": True, "messages": msgs_payload}
                async with cliente.stream("POST", base + endpoint_detectado, json=payload) as response:
                    response.raise_for_status()
                    async for linea in response.aiter_lines():
                        if not linea:
                            continue
                        linea = linea.removeprefix("data: ").strip()
                        if not linea:
                            continue
                        try:
                            dato = json.loads(linea)
                            delta = dato.get("message", {}).get("content", "")
                            if delta:
                                respuesta_completa += delta
                                yield delta
                        except json.JSONDecodeError:
                            continue

            else:  # /api/generate
                system_txt = next((m["content"] for m in msgs_payload if m["role"] == "system"), "")
                user_txt = " ".join(m["content"] for m in msgs_payload if m["role"] != "system")
                payload = {"model": effective_modelo, "stream": True, "system": system_txt, "prompt": user_txt}
                async with cliente.stream("POST", base + endpoint_detectado, json=payload) as response:
                    response.raise_for_status()
                    async for linea in response.aiter_lines():
                        if not linea:
                            continue
                        try:
                            dato = json.loads(linea)
                            delta = dato.get("response", "")
                            if delta:
                                respuesta_completa += delta
                                yield delta
                        except json.JSONDecodeError:
                            continue

        if usuario_id and respuesta_completa.strip():
            await guardar_conversacion(
                conexion,
                usuario_id,
                cuenta_id,
                rol_usuario,
                mensajes,
                respuesta_completa,
            )
    else:
        raise ValueError(
            f"Proveedor no soportado para chat operativo: {proveedor}. "
            f"Usa '{PROVEEDOR_LOCAL}' o 'anthropic'."
        )


async def respuesta_fallback_operativa(
    conexion: asyncpg.Connection,
    *,
    mensajes: list[dict],
    cuenta_id: UUID | None = None,
    documento_texto: str | None = None,
) -> str:
    """
    Respuesta de contingencia cuando el proveedor IA no está disponible.
    Evita romper UX en MVP y mantiene una salida útil/contextual.
    """
    pregunta = ""
    for m in reversed(mensajes):
        if m.get("role") == "user":
            pregunta = str(m.get("content") or "").strip()
            break

    kpis = await obtener_kpis_pipeline(conexion, cuenta_id)
    bloques = [
        "El motor IA no está disponible en este momento. Te doy un resumen operativo inmediato con datos reales:",
        (
            f"- Oportunidades activas: {kpis['activas']:,}\n"
            f"- Pipeline activo: {kpis['pipeline_activo']:,.0f}€\n"
            f"- Win rate: {kpis['win_rate']:.1f}%"
        ),
    ]

    if pregunta:
        bloques.append(f"Pregunta detectada: {pregunta}")

    if documento_texto:
        extracto = documento_texto[:900].strip()
        if extracto:
            bloques.append("Extracto del documento cargado:")
            bloques.append(extracto)
            bloques.append("Siguiente paso recomendado: vuelve a lanzar la consulta cuando IA esté operativa para un análisis completo.")

    return "\n\n".join(bloques)


# ── Función legacy para voice/servicio.py ────────────────────────────────────
async def llamar_ia(
    mensajes: list[dict],
    system: str,
    config: ConfigIA,
    max_tokens: int = 800,
    timeout_segundos: int = 180,
) -> str:
    """
    Llamada asíncrona a IA para voice/servicio.py.
    NO usa la DB, solo el config de proveedor.
    """
    if config.proveedor == "anthropic":
        api_key = obtener_api_key_externa("anthropic")
        cliente = anthropic.Anthropic(api_key=api_key)
        respuesta = cliente.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=mensajes,
        )
        return respuesta.content[0].text

    elif config.proveedor == PROVEEDOR_LOCAL:  # ollama
        base = normalizar_ollama_url_operacional(config.ollama_url).rstrip("/")
        msgs = [{"role": "system", "content": system}, *mensajes]
        timeout = httpx.Timeout(float(timeout_segundos), connect=10.0)
        errores: list[str] = []

        async with httpx.AsyncClient(timeout=timeout) as cliente:
            # 1. /api/chat (nativo Ollama)
            try:
                r = await cliente.post(base + "/api/chat", json={
                    "model": config.ollama_modelo, "stream": False,
                    "messages": msgs, "options": {"num_predict": max_tokens},
                })
                if r.status_code != 404:
                    r.raise_for_status()
                    return r.json().get("message", {}).get("content", "")
            except httpx.TimeoutException as e:
                errores.append(f"/api/chat timeout: {e}")
            except httpx.RequestError as e:
                errores.append(f"/api/chat request error: {e}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    errores.append(f"/api/chat status {e.response.status_code}: {e}")

            # 2. /v1/chat/completions (OpenAI-compatible)
            try:
                r = await cliente.post(base + "/v1/chat/completions", json={
                    "model": config.ollama_modelo, "stream": False, "messages": msgs,
                })
                if r.status_code != 404:
                    r.raise_for_status()
                    return r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except httpx.TimeoutException as e:
                errores.append(f"/v1/chat/completions timeout: {e}")
            except httpx.RequestError as e:
                errores.append(f"/v1/chat/completions request error: {e}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    errores.append(f"/v1/chat/completions status {e.response.status_code}: {e}")

            # 3. /api/generate (Ollama antiguo)
            try:
                r = await cliente.post(base + "/api/generate", json={
                    "model": config.ollama_modelo, "stream": False,
                    "system": system, "prompt": msgs[-1]["content"] if msgs else "",
                    "options": {"num_predict": max_tokens},
                })
                if r.status_code != 404:
                    r.raise_for_status()
                    return r.json().get("response", "")
            except httpx.TimeoutException as e:
                errores.append(f"/api/generate timeout: {e}")
            except httpx.RequestError as e:
                errores.append(f"/api/generate request error: {e}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    errores.append(f"/api/generate status {e.response.status_code}: {e}")

            detalle = " | ".join(errores) if errores else "sin detalle"
            raise ValueError(f"No se pudo obtener respuesta de Ollama. {detalle}")
    else:
        raise ValueError(
            f"Proveedor no soportado para operación local: {config.proveedor}. "
            f"Usa '{PROVEEDOR_LOCAL}' o 'anthropic'."
        )


def llamar_ia_sync(
    mensajes: list[dict],
    system: str,
    config: ConfigIA | None = None,
    max_tokens: int = 800,
    temperature: float = 0.7,
) -> str:
    """
    Versión síncrona para informes/servicio.py y decks/servicio.py.
    Wrapper que corre llamar_ia() en un nuevo event loop (en thread separado si es necesario).
    """
    import asyncio
    import concurrent.futures

    cfg = config or ConfigIA()

    try:
        # Si hay un event loop corriendo, correr en thread separado
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(
                asyncio.run,
                llamar_ia(mensajes, system, cfg, max_tokens)
            ).result()
    except RuntimeError:
        # No hay loop corriendo, crear uno nuevo
        return asyncio.run(llamar_ia(mensajes, system, cfg, max_tokens))
