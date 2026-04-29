"""
Endpoints del módulo IA Copilot.
Proxy seguro — la API key de Anthropic vive en el servidor.
KPIs en tiempo real, contexto de cuenta, historial persistido.
"""

from uuid import UUID
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

import asyncpg
import httpx
import anthropic

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual, requerir_rol
from app.config import configuracion
from app.database import obtener_conexion, obtener_pool
from app.modules.ia import servicio
from app.modules.ia.proveedores import (
    PROVEEDORES_EXTERNOS,
    PROVEEDORES_DEEP_RESEARCH_SOPORTADOS,
    PROVEEDOR_LOCAL,
    _es_ip_privada,
    establecer_config_research_runtime,
    establecer_config_operacional_runtime,
    guardar_config_operacional_en_db,
    guardar_config_research_en_db,
    estado_proveedores,
    obtener_api_key_externa,
    obtener_modelo_research,
    obtener_ollama_url_research,
    obtener_configs_operacionales,
    obtener_proveedor_research_activo,
    normalizar_proveedor,
    proveedor_externo_configurado,
)

router = APIRouter(prefix="/ia", tags=["ia"])
PROVEEDORES_CHAT_OPERATIVO = {PROVEEDOR_LOCAL}


class MensajeChat(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class PeticionChat(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mensajes: list[MensajeChat] = Field(validation_alias=AliasChoices("mensajes", "messages"))
    # Operación diaria: por defecto IA local cerrada (Ollama)
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT
    documento_id: UUID | None = None  # Si se pasa, carga texto del doc como contexto


class PeticionModelosOllama(BaseModel):
    ollama_url: str = configuracion.OLLAMA_URL


class PeticionConfigResearch(BaseModel):
    proveedor: str
    modelo: str | None = None
    api_key: str | None = None
    ollama_url: str | None = None


class PeticionTestOllama(BaseModel):
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT
    mensaje: str = "Responde exactamente: OK"


class PeticionTestResearch(BaseModel):
    proveedor: str
    modelo: str | None = None
    api_key: str | None = None
    ollama_url: str | None = None


class ConfigOperacionalServicio(BaseModel):
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str
    ollama_modelo: str


class PeticionConfigOperacional(BaseModel):
    copilot: ConfigOperacionalServicio
    voice: ConfigOperacionalServicio
    informes: ConfigOperacionalServicio
    decks: ConfigOperacionalServicio
    cross_selling: ConfigOperacionalServicio | None = None
    importacion: ConfigOperacionalServicio | None = None


def _candidatos_url_ollama(ollama_url: str) -> list[str]:
    """
    Construye URLs candidatas para tests desde el backend.
    Si llega una IP privada/localhost, sustituye por la URL configurada en OLLAMA_URL.
    """
    url_servidor = configuracion.OLLAMA_URL.rstrip("/")
    base = (ollama_url or "").strip().rstrip("/")
    if not base:
        return [url_servidor]

    candidatos = [base]
    try:
        parsed = urlparse(base)
        host = (parsed.hostname or "").lower()
        if _es_ip_privada(host):
            if url_servidor not in candidatos:
                candidatos.append(url_servidor)
    except Exception:
        pass

    if url_servidor not in candidatos:
        candidatos.append(url_servidor)
    return candidatos


async def _probar_ollama_con_fallback(
    ollama_url: str,
    modelo: str,
    mensaje: str = "Responde exactamente: OK",
) -> str:
    bases = _candidatos_url_ollama(ollama_url)
    payload_v1 = {
        "model": modelo,
        "stream": False,
        "messages": [
            {"role": "system", "content": "Responde de forma breve."},
            {"role": "user", "content": mensaje},
        ],
    }
    payload_api = {
        "model": modelo,
        "stream": False,
        "messages": payload_v1["messages"],
    }
    payload_generate = {
        "model": modelo,
        "stream": False,
        "system": "Responde de forma breve.",
        "prompt": mensaje,
    }
    errores: list[str] = []
    errores_conexion: list[str] = []

    async with httpx.AsyncClient(timeout=30.0) as cliente:
        for base in bases:
            # 1) Endpoint nativo de Ollama /api/chat (más fiable con modelos locales)
            try:
                r = await cliente.post(base + "/api/chat", json=payload_api)
                r.raise_for_status()
                datos = r.json()
                texto = (datos.get("message", {}).get("content") or "").strip()
                if texto:
                    return texto
            except httpx.HTTPStatusError as e:
                errores.append(f"{base}/api/chat -> {e.response.status_code}")
            except httpx.RequestError as e:
                errores_conexion.append(f"{base}: {e}")
                continue

            # 2) OpenAI-compatible endpoint (fallback)
            try:
                r = await cliente.post(base + "/v1/chat/completions", json=payload_v1)
                r.raise_for_status()
                datos = r.json()
                texto = (
                    datos.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if texto:
                    return texto
            except httpx.HTTPStatusError as e:
                errores.append(f"{base}/v1/chat/completions -> {e.response.status_code}")
            except httpx.RequestError as e:
                errores_conexion.append(f"{base}: {e}")
                continue

            # 3) Endpoint legacy /api/generate (último recurso)
            try:
                r = await cliente.post(base + "/api/generate", json=payload_generate)
                r.raise_for_status()
                datos = r.json()
                texto = (datos.get("response") or "").strip()
                return texto or "OK"
            except httpx.HTTPStatusError as e:
                errores.append(f"{base}/api/generate -> {e.response.status_code}")
            except httpx.RequestError as e:
                errores_conexion.append(f"{base}: {e}")
                continue

    if errores_conexion and not errores:
        raise RuntimeError(
            "No se pudo conectar con Ollama en ninguna URL candidata: "
            + " | ".join(errores_conexion)
        )

    raise RuntimeError(
        "No se detectó una API Ollama compatible en la URL indicada. "
        f"Endpoints probados: {', '.join(errores) if errores else 'sin detalle'}"
    )


@router.post("/chat")
async def chat(
    peticion: PeticionChat,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    pool: asyncpg.Pool = Depends(obtener_pool),
):
    """
    Chat genérico con KPIs reales del pipeline global.
    Sin contexto de cuenta específica, sin persistencia de historial.
    """
    proveedor = normalizar_proveedor(peticion.proveedor, PROVEEDOR_LOCAL)
    if proveedor not in PROVEEDORES_CHAT_OPERATIVO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Proveedor '{proveedor}' no soportado en chat operativo. "
                f"Usa: {', '.join(sorted(PROVEEDORES_CHAT_OPERATIVO))}"
            ),
        )
    if proveedor in PROVEEDORES_EXTERNOS and not proveedor_externo_configurado(proveedor):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"La API key del proveedor '{proveedor}' no está configurada.",
        )

    mensajes = [{"role": m.role, "content": m.content} for m in peticion.mensajes]

    async def generador():
        try:
            async with pool.acquire() as conexion:
                async for chunk in servicio.chat_streaming(
                    mensajes=mensajes,
                    conexion=conexion,
                    usuario_id=None,  # No persistir sin contexto de cuenta
                    cuenta_id=None,
                    rol_usuario=usuario.rol,
                    proveedor=proveedor,
                    ollama_url=peticion.ollama_url,
                    ollama_modelo=peticion.ollama_modelo,
                ):
                    yield f"data: {chunk}\n\n"
        except Exception as e:
            async with pool.acquire() as conexion:
                fallback = await servicio.respuesta_fallback_operativa(
                    conexion,
                    mensajes=mensajes,
                    cuenta_id=None,
                    documento_texto=None,
                )
            yield f"data: {fallback}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generador(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/{cuenta_id}")
async def chat_cuenta(
    cuenta_id: UUID,
    peticion: PeticionChat,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    pool: asyncpg.Pool = Depends(obtener_pool),
):
    """
    Chat contextual para una cuenta específica.
    - Sistema prompt incluye contexto de la cuenta (propuesta, investigación)
    - KPIs específicos de la cuenta
    - Historial persistido en DB para auditoría
    """
    proveedor = normalizar_proveedor(peticion.proveedor, PROVEEDOR_LOCAL)
    if proveedor not in PROVEEDORES_CHAT_OPERATIVO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Proveedor '{proveedor}' no soportado en chat operativo. "
                f"Usa: {', '.join(sorted(PROVEEDORES_CHAT_OPERATIVO))}"
            ),
        )
    if proveedor in PROVEEDORES_EXTERNOS and not proveedor_externo_configurado(proveedor):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"La API key del proveedor '{proveedor}' no está configurada.",
        )

    mensajes = [{"role": m.role, "content": m.content} for m in peticion.mensajes]

    async def generador():
        doc_texto: str | None = None
        try:
            async with pool.acquire() as conexion:
                # Cargar texto del documento si se indica
                if peticion.documento_id:
                    from app.modules.documentos import servicio as doc_srv
                    doc_texto = await doc_srv.obtener_contenido_extraido(
                        conexion, peticion.documento_id, cuenta_id
                    )

                async for chunk in servicio.chat_streaming(
                    mensajes=mensajes,
                    conexion=conexion,
                    usuario_id=UUID(usuario.usuario_id),
                    cuenta_id=cuenta_id,
                    rol_usuario=usuario.rol,
                    proveedor=proveedor,
                    ollama_url=peticion.ollama_url,
                    ollama_modelo=peticion.ollama_modelo,
                    documento_texto=doc_texto,
                ):
                    yield f"data: {chunk}\n\n"
        except Exception as e:
            async with pool.acquire() as conexion:
                fallback = await servicio.respuesta_fallback_operativa(
                    conexion,
                    mensajes=mensajes,
                    cuenta_id=cuenta_id,
                    documento_texto=doc_texto,
                )
            yield f"data: {fallback}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generador(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/proveedores/estado")
async def obtener_estado_proveedores(
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """
    Estado de configuración IA sin exponer secretos.
    Útil para el panel de configuración frontend.
    """
    return estado_proveedores()


@router.get("/research/config")
async def obtener_config_research(
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
):
    estado = estado_proveedores()
    proveedor_activo = obtener_proveedor_research_activo()
    return {
        "proveedor_activo": proveedor_activo,
        "modelo_activo": obtener_modelo_research(proveedor_activo),
        "ollama_url_activa": estado["research"]["ollama_url_activa"],
        "proveedores": estado["research"]["externos"],
    }


@router.get("/operacional/config")
async def obtener_config_operacional(
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
):
    return {"configs": obtener_configs_operacionales()}


@router.put("/operacional/config")
async def actualizar_config_operacional(
    peticion: PeticionConfigOperacional,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    for servicio in ("copilot", "voice", "informes", "decks", "cross_selling", "importacion"):
        entrada = getattr(peticion, servicio, None)
        if entrada is None:
            continue
        if normalizar_proveedor(entrada.proveedor, PROVEEDOR_LOCAL) != PROVEEDOR_LOCAL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"El servicio '{servicio}' solo permite proveedor 'ollama'.",
            )
        establecer_config_operacional_runtime(
            servicio=servicio,
            ollama_url=entrada.ollama_url,
            ollama_modelo=entrada.ollama_modelo,
        )

    await guardar_config_operacional_en_db(conexion)
    return {"ok": True, "configs": obtener_configs_operacionales()}


@router.put("/research/config")
async def actualizar_config_research(
    peticion: PeticionConfigResearch,
    _usuario: UsuarioAutenticado = Depends(requerir_rol("admin")),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    proveedor = normalizar_proveedor(peticion.proveedor, "anthropic")
    if proveedor not in {*PROVEEDORES_EXTERNOS, PROVEEDOR_LOCAL}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Proveedor '{proveedor}' no reconocido.",
        )
    if proveedor not in PROVEEDORES_DEEP_RESEARCH_SOPORTADOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Proveedor '{proveedor}' aún no soportado en deep research. "
                "Soportados: anthropic, openai, gemini, ollama."
            ),
        )
    requiere_key = proveedor != PROVEEDOR_LOCAL
    if requiere_key and not proveedor_externo_configurado(proveedor) and not (peticion.api_key and peticion.api_key.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No hay API key configurada para '{proveedor}'. Indica una clave.",
        )

    activo = establecer_config_research_runtime(
        proveedor=proveedor,
        modelo=peticion.modelo,
        api_key=peticion.api_key,
        ollama_url=peticion.ollama_url,
    )
    await guardar_config_research_en_db(conexion)
    return {
        "ok": True,
        "proveedor_activo": activo,
        "modelo_activo": obtener_modelo_research(activo),
    }


@router.post("/ollama/models")
async def listar_modelos_ollama(
    peticion: PeticionModelosOllama,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """
    Lista modelos de una instancia Ollama desde backend para evitar CORS en frontend.
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as cliente:
            datos = None
            errores: list[str] = []
            for base in _candidatos_url_ollama(peticion.ollama_url):
                try:
                    respuesta = await cliente.get(base.rstrip("/") + "/api/tags")
                    respuesta.raise_for_status()
                    datos = respuesta.json()
                    break
                except Exception as e:
                    errores.append(f"{base}: {e}")
            if datos is None:
                raise RuntimeError(" | ".join(errores) if errores else "sin detalle")
        modelos = [{"name": m.get("name"), "size": int(m.get("size", 0) or 0)}
                   for m in datos.get("models", []) if m.get("name")]
        return {"models": modelos}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo conectar con Ollama en {peticion.ollama_url}: {e}",
        ) from e


@router.post("/ollama/test")
async def probar_ollama(
    peticion: PeticionTestOllama,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """
    Test directo contra Ollama sin depender de DB ni de prompts del copilot.
    """
    try:
        texto = await _probar_ollama_con_fallback(
            ollama_url=peticion.ollama_url,
            modelo=peticion.ollama_modelo,
            mensaje=peticion.mensaje,
        )
        return {"ok": True, "respuesta": texto or "Sin contenido"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fallo conectando con Ollama ({peticion.ollama_modelo}) en {peticion.ollama_url}: {e}",
        ) from e


@router.post("/research/test")
async def probar_research(
    peticion: PeticionTestResearch,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """
    Test de proveedor externo para Deep Research.
    Verifica key/model con una respuesta mínima.
    """
    proveedor = normalizar_proveedor(peticion.proveedor, "anthropic")
    if proveedor not in PROVEEDORES_DEEP_RESEARCH_SOPORTADOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Proveedor no soportado para Deep Research. Usa anthropic, openai, gemini u ollama.",
        )

    modelo = (peticion.modelo or obtener_modelo_research(proveedor)).strip()
    api_key = (peticion.api_key or "").strip() or obtener_api_key_externa(proveedor)
    if proveedor != PROVEEDOR_LOCAL and not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No hay API key para '{proveedor}'.",
        )

    try:
        if proveedor == "anthropic":
            cliente = anthropic.Anthropic(api_key=api_key)
            r = cliente.messages.create(
                model=modelo,
                max_tokens=30,
                messages=[{"role": "user", "content": "Responde exactamente: OK"}],
            )
            texto = r.content[0].text.strip()
            return {"ok": True, "respuesta": texto}

        if proveedor == "openai":
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": modelo,
                "input": "Responde exactamente: OK",
                "max_output_tokens": 30,
            }
            async with httpx.AsyncClient(timeout=30.0) as cliente:
                r = await cliente.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
                r.raise_for_status()
                datos = r.json()
            texto = (datos.get("output_text") or "").strip() or "OK"
            return {"ok": True, "respuesta": texto}

        if proveedor == PROVEEDOR_LOCAL:
            ollama_url = (
                peticion.ollama_url.strip()
                if peticion.ollama_url and peticion.ollama_url.strip()
                else obtener_ollama_url_research().strip()
            ).rstrip("/")
            texto = await _probar_ollama_con_fallback(
                ollama_url=ollama_url,
                modelo=modelo,
                mensaje="Responde exactamente: OK",
            )
            return {"ok": True, "respuesta": texto or "OK"}

        # gemini
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        payload = {"contents": [{"role": "user", "parts": [{"text": "Responde exactamente: OK"}]}]}
        async with httpx.AsyncClient(timeout=30.0) as cliente:
            r = await cliente.post(url, json=payload)
            r.raise_for_status()
            datos = r.json()
        cand = (datos.get("candidates") or [{}])[0]
        parts = cand.get("content", {}).get("parts", []) or []
        texto = " ".join((p.get("text") or "").strip() for p in parts if p.get("text")).strip() or "OK"
        return {"ok": True, "respuesta": texto}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fallo test Deep Research con {proveedor}/{modelo}: {e}",
        ) from e


@router.get("/conversaciones/{cuenta_id}")
async def listar_conversaciones(
    cuenta_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
    limit: int = 20,
):
    """
    Devuelve el historial de conversaciones del usuario para una cuenta específica.
    Útil para auditoría y contexto de conversaciones anteriores.
    """
    filas = await conexion.fetch(
        """
        SELECT id, usuario_id, rol_usuario,
               COALESCE(jsonb_array_length(mensajes), 0) AS num_mensajes,
               substring(respuesta, 1, 100) AS preview,
               creado_en
        FROM conversaciones_ia
        WHERE cuenta_id = $1 AND usuario_id = $2
        ORDER BY creado_en DESC
        LIMIT $3
        """,
        cuenta_id,
        UUID(usuario.usuario_id),
        limit,
    )
    return [
        {
            "id": str(f["id"]),
            "rol_usuario": f["rol_usuario"],
            "num_mensajes": f["num_mensajes"],
            "preview": f["preview"],
            "creado_en": f["creado_en"].isoformat(),
        }
        for f in filas
    ]
