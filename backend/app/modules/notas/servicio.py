"""
Lógica de negocio del módulo Notas de Voz.
"""

import httpx
from uuid import UUID

import asyncpg

from app.config import configuracion
from app.modules.notas.schemas import NotaCreate, NotaRead


async def listar_notas(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    oportunidad_id: UUID | None,
    busqueda: str | None,
    pagina: int,
    por_pagina: int,
) -> dict:
    condiciones = ["n.usuario_id = $1", "n.eliminado_en IS NULL" if False else "TRUE"]
    params: list = [usuario_id]
    n = 2

    # Sin soft-delete en esta tabla, filtramos solo por usuario
    condiciones = ["n.usuario_id = $1"]

    if oportunidad_id:
        condiciones.append(f"n.oportunidad_id = ${n}")
        params.append(oportunidad_id)
        n += 1

    if busqueda:
        condiciones.append(f"(n.titulo ILIKE ${n} OR n.transcripcion ILIKE ${n})")
        params.append(f"%{busqueda}%")
        n += 1

    where = "WHERE " + " AND ".join(condiciones)

    total = await conexion.fetchval(
        f"SELECT COUNT(*) FROM notas_voz n {where}", *params
    )

    offset = (pagina - 1) * por_pagina
    filas = await conexion.fetch(
        f"""
        SELECT
            n.id,
            n.titulo,
            n.transcripcion,
            n.duracion_seg,
            n.oportunidad_id,
            o.nombre AS oportunidad_nombre,
            n.creado_en::TEXT AS creado_en
        FROM notas_voz n
        LEFT JOIN oportunidades o ON o.id = n.oportunidad_id
        {where}
        ORDER BY n.creado_en DESC
        LIMIT ${n} OFFSET ${n + 1}
        """,
        *params, por_pagina, offset,
    )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [NotaRead(**dict(f)) for f in filas],
    }


async def crear_nota(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    datos: NotaCreate,
) -> NotaRead:
    fila = await conexion.fetchrow(
        """
        INSERT INTO notas_voz (usuario_id, titulo, transcripcion, duracion_seg, oportunidad_id)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, titulo, transcripcion, duracion_seg, oportunidad_id, creado_en::TEXT AS creado_en
        """,
        usuario_id, datos.titulo, datos.transcripcion,
        datos.duracion_seg, datos.oportunidad_id,
    )

    oportunidad_nombre: str | None = None
    if datos.oportunidad_id:
        oportunidad_nombre = await conexion.fetchval(
            "SELECT nombre FROM oportunidades WHERE id = $1", datos.oportunidad_id
        )

    return NotaRead(
        **dict(fila),
        oportunidad_nombre=oportunidad_nombre,
    )


async def eliminar_nota(
    conexion: asyncpg.Connection,
    nota_id: UUID,
    usuario_id: UUID,
) -> bool:
    resultado = await conexion.execute(
        "DELETE FROM notas_voz WHERE id = $1 AND usuario_id = $2",
        nota_id, usuario_id,
    )
    return resultado == "DELETE 1"


def _urls_ollama_candidatas() -> list[str]:
    base = (configuracion.OLLAMA_URL or "").strip().rstrip("/")
    if not base:
        return []
    return [base]


async def transcribir_audio_openai(
    *,
    contenido: bytes,
    nombre_fichero: str,
    content_type: str | None,
) -> str:
    """
    Transcribe audio con OpenAI Whisper.
    Requiere OPENAI_API_KEY configurada en backend.
    """
    if not contenido:
        raise ValueError("El archivo de audio está vacío.")

    tipo = content_type or "application/octet-stream"
    timeout = httpx.Timeout(120.0, connect=10.0)
    errores: list[str] = []

    api_key = (configuracion.OPENAI_API_KEY or "").strip()
    if api_key:
        async with httpx.AsyncClient(timeout=timeout) as cliente:
            respuesta = await cliente.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data={
                    "model": "whisper-1",
                    "language": "es",
                    "response_format": "json",
                },
                files={"file": (nombre_fichero, contenido, tipo)},
            )

        if respuesta.status_code < 400:
            data = respuesta.json()
            texto = (data.get("text") or "").strip()
            if texto:
                return texto
        else:
            try:
                detalle = respuesta.json().get("error", {}).get("message", "")
            except Exception:
                detalle = respuesta.text
            errores.append(f"OpenAI: {respuesta.status_code} {detalle}".strip())

    # Fallback local: Ollama OpenAI-compatible (si tiene modelo speech-to-text instalado)
    modelos = [configuracion.OLLAMA_MODEL_DEFAULT, "whisper", "whisper:latest"]
    endpoints = ["/v1/audio/transcriptions"]
    async with httpx.AsyncClient(timeout=timeout) as cliente:
        for base in _urls_ollama_candidatas():
            for endpoint in endpoints:
                for modelo in modelos:
                    try:
                        respuesta = await cliente.post(
                            base + endpoint,
                            data={
                                "model": modelo,
                                "language": "es",
                                "response_format": "json",
                            },
                            files={"file": (nombre_fichero, contenido, tipo)},
                        )
                        if respuesta.status_code >= 400:
                            errores.append(f"Ollama {base}{endpoint} ({modelo}): {respuesta.status_code}")
                            continue
                        data = respuesta.json()
                        texto = (data.get("text") or data.get("response") or "").strip()
                        if texto:
                            return texto
                    except Exception as exc:
                        errores.append(f"Ollama {base}{endpoint} ({modelo}): {exc}")

    # Último fallback: faster-whisper local
    try:
        import asyncio, functools, tempfile, os

        def _transcribir_sync(data: bytes, nombre: str, modelo: str) -> str:
            from faster_whisper import WhisperModel
            ext = os.path.splitext(nombre)[1] or ".webm"
            tmp = tempfile.mktemp(suffix=ext)
            with open(tmp, "wb") as f:
                f.write(data)
            try:
                model = WhisperModel(modelo, device="cpu", compute_type="int8")
                segments, _ = model.transcribe(tmp, language="es", beam_size=1)
                return " ".join(seg.text.strip() for seg in segments)
            finally:
                os.unlink(tmp)

        loop = asyncio.get_event_loop()
        texto = await loop.run_in_executor(
            None,
            functools.partial(
                _transcribir_sync,
                contenido,
                nombre_fichero,
                configuracion.WHISPER_MODELO,
            ),
        )
        if texto:
            return texto
    except Exception as exc:
        errores.append(f"faster-whisper: {exc}")

    raise ValueError(
        "No se pudo transcribir el audio. "
        + ("Detalle: " + " | ".join(errores[:4]) if errores else "")
    )
