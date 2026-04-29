"""
Endpoints del módulo Voice Studio.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.config import configuracion
from app.database import obtener_conexion
from app.modules.voice import servicio
from app.modules.ia.proveedores import PROVEEDOR_LOCAL
from app.modules.ia.contexto import resolver_contexto

router = APIRouter(prefix="/voice", tags=["voice"])

FOCOS_PERMITIDOS = {"general", "productos", "equipo", "pipeline"}


class PeticionBriefing(BaseModel):
    foco: str = "general"
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT


@router.post("/briefing")
async def generar_briefing(
    peticion: PeticionBriefing,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    from app.modules.ia.servicio import ConfigIA
    config = ConfigIA(
        proveedor=peticion.proveedor,
        ollama_url=peticion.ollama_url,
        ollama_modelo=peticion.ollama_modelo,
    )

    if config.proveedor != PROVEEDOR_LOCAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Voice Studio solo admite IA local (ollama).",
        )

    if peticion.foco not in FOCOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Foco inválido. Opciones: {', '.join(FOCOS_PERMITIDOS)}",
        )

    try:
        script = await servicio.generar_script_briefing(peticion.foco, config)
        return {"script": script, "foco": peticion.foco}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando el briefing: {str(e)}",
        )


@router.post("/briefing/{cuenta_id}", response_class=PlainTextResponse)
async def generar_briefing_cuenta(
    cuenta_id: UUID,
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    peticion: PeticionBriefing | None = None,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Genera un briefing de audio personalizado para una cuenta específica.
    Lee la propuesta_comercial real de DB — no usa datos hardcodeados.
    """
    from app.agents.base import ConfigAgente
    from app.skills.generar_audio import generar_audio_cuenta
    from app.modules.plantillas import servicio as plantillas_servicio

    config = None
    if peticion and peticion.proveedor == "ollama":
        config = ConfigAgente(
            proveedor="ollama",
            ollama_url=peticion.ollama_url,
            ollama_modelo=peticion.ollama_modelo,
        )
    ctx = await resolver_contexto(
        conexion,
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
        cuenta_id_por_defecto=cuenta_id,
    )
    if ctx.tipo in {"cuenta", "cliente"} and ctx.contexto_id != cuenta_id:
        raise HTTPException(status_code=422, detail="El contexto de cuenta/cliente no coincide con la ruta.")
    if ctx.tipo == "oportunidad" and ctx.cuenta_id and ctx.cuenta_id != cuenta_id:
        raise HTTPException(status_code=422, detail="La oportunidad no pertenece a la cuenta indicada.")

    try:
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conexion, "briefing")
        instrucciones_extra = None
        if plantilla_activa and isinstance(plantilla_activa.get("contenido"), dict):
            instrucciones_extra = plantilla_activa["contenido"].get("prompt_base")
        script = await generar_audio_cuenta(
            cuenta_id,
            conexion,
            config,
            instrucciones_extra=instrucciones_extra,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando briefing: {e}")

    # Persistir en historial_documentos (fallo silencioso — no afecta la respuesta)
    try:
        from datetime import date
        from app.modules.historial import servicio as historial_servicio
        nombre_fichero = f"briefing_{str(cuenta_id)[:8]}_{date.today().isoformat()}.txt"
        await historial_servicio.registrar_documento(
            conexion,
            cuenta_id=cuenta_id,
            usuario_id=UUID(usuario.usuario_id),
            tipo="briefing",
            nombre_fichero=nombre_fichero,
            contenido=script.encode("utf-8"),
            contexto_tipo=ctx.tipo,
            contexto_id=ctx.contexto_id,
            metadatos={
                "foco": "cuenta",
                "plantilla_id": str(plantilla_activa["id"]) if plantilla_activa else None,
                "plantilla_nombre": plantilla_activa["nombre"] if plantilla_activa else None,
            },
        )
    except Exception:
        pass

    return script


@router.post("/briefing/{cuenta_id}/audio")
async def generar_audio_mp3(
    cuenta_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Convierte el último briefing de texto de una cuenta a MP3 mediante OpenAI TTS.
    Persiste el audio en MinIO y lo registra en historial_documentos.
    """
    from app.config import configuracion as cfg

    # Recuperar último briefing de texto para esta cuenta
    fila_briefing = await conexion.fetchrow(
        """
        SELECT id, storage_key, nombre_fichero
        FROM historial_documentos
        WHERE cuenta_id = $1
          AND tipo = 'briefing'
          AND (usuario_id = $2 OR $3)
        ORDER BY creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
        UUID(usuario.usuario_id),
        not usuario.es_comercial,
    )
    if not fila_briefing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin briefing de texto disponible para esta cuenta.")

    from app import storage as minio_storage
    script_bytes = await minio_storage.descargar_fichero(fila_briefing["storage_key"])
    script_texto = script_bytes.decode("utf-8", errors="replace")

    # TTS → MP3 (OpenAI si hay clave; edge-tts gratuito como fallback)
    try:
        if cfg.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            cliente_openai = AsyncOpenAI(api_key=cfg.OPENAI_API_KEY)
            respuesta_tts = await cliente_openai.audio.speech.create(
                model="tts-1",
                voice="onyx",
                input=script_texto,
                response_format="mp3",
            )
            audio_bytes = respuesta_tts.content
            metadatos_tts = {"voz": "onyx", "motor": "openai-tts-1"}
        else:
            import tempfile, os
            import edge_tts
            voz = "es-ES-AlvaroNeural"
            communicate = edge_tts.Communicate(script_texto, voz)
            tmp_path = tempfile.mktemp(suffix=".mp3")
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()
            os.unlink(tmp_path)
            metadatos_tts = {"voz": voz, "motor": "edge-tts"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error en TTS: {e}")

    # Persistir MP3 en historial_documentos
    from datetime import date
    from app.modules.historial import servicio as historial_servicio

    nombre_mp3 = fila_briefing["nombre_fichero"].replace(".txt", "") + ".mp3"
    registro = await historial_servicio.registrar_documento(
        conexion,
        cuenta_id=cuenta_id,
        usuario_id=UUID(usuario.usuario_id),
        tipo="audio",
        nombre_fichero=nombre_mp3,
        contenido=audio_bytes,
        contexto_tipo="cuenta",
        contexto_id=cuenta_id,
        metadatos={"audio_origen_id": str(fila_briefing["id"]), **metadatos_tts},
    )

    # Vincular al briefing origen
    await conexion.execute(
        "UPDATE historial_documentos SET audio_origen_id = $1 WHERE id = $2",
        fila_briefing["id"],
        registro["id"],
    )

    return {"doc_id": str(registro["id"]), "nombre_fichero": nombre_mp3, "tamano_bytes": len(audio_bytes)}
