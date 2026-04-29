"""
Endpoints de jobs asíncronos para generación de documentos de cuenta.
POST /{cuenta_id}/pdf/generar     → job_id
POST /{cuenta_id}/pptx/generar    → job_id
POST /{cuenta_id}/briefing/generar → job_id
POST /{cuenta_id}/estudio-ia/generar → job_id
GET  /jobs/{job_id}               → estado + progreso
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.config import configuracion
from app.database import obtener_conexion
from app.modules.documentos_jobs import servicio
from app.modules.documentos import servicio as doc_servicio
from app.modules.documentos.schemas import DocumentoCuentaRead
from app.modules.ia.contexto import resolver_contexto

router = APIRouter(prefix="/cuentas", tags=["documentos-jobs"])


async def _resolver_contexto_job(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    contexto_tipo: str | None,
    contexto_id: UUID | None,
):
    """
    Resuelve contexto de forma robusta para jobs.
    Si llega oportunidad sin contexto_id, degrada a contexto de cuenta para no bloquear.
    """
    try:
        return await resolver_contexto(
            conexion,
            contexto_tipo=contexto_tipo,
            contexto_id=contexto_id,
            cuenta_id_por_defecto=cuenta_id,
        )
    except ValueError as exc:
        tipo = (contexto_tipo or "").strip().lower()
        if tipo == "oportunidad" and contexto_id is None:
            return await resolver_contexto(
                conexion,
                contexto_tipo="cuenta",
                contexto_id=None,
                cuenta_id_por_defecto=cuenta_id,
            )
        raise HTTPException(status_code=422, detail=str(exc))


def _validar_cuenta():
    """Dependencia que verifica que la cuenta existe y no está eliminada."""
    async def _inner(
        cuenta_id: UUID,
        conexion: asyncpg.Connection = Depends(obtener_conexion),
    ) -> UUID:
        fila = await conexion.fetchrow(
            "SELECT id FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
        )
        if not fila:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        return cuenta_id
    return _inner


# ── Investigación ─────────────────────────────────────────────────────────────

@router.post("/{cuenta_id}/investigacion/iniciar", status_code=202)
async def iniciar_investigacion(
    cuenta_id: UUID,
    tareas: BackgroundTasks,
    forzar: bool = False,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    # Si hay investigación reciente y no se fuerza, devolver el estado existente
    if not forzar:
        reciente = await conexion.fetchrow(
            """
            SELECT id FROM investigaciones_empresa
            WHERE cuenta_id = $1 AND estado = 'completada'
              AND completado_en > now() - INTERVAL '30 days'
            ORDER BY completado_en DESC LIMIT 1
            """,
            cuenta_id,
        )
        if reciente:
            # No lanzar job — ya existe resultado reciente
            return {"job_id": None, "estado": "completada", "investigacion_id": str(reciente["id"])}

    fila = await conexion.fetchrow(
        "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    job_id = servicio.crear_job("investigacion", f"Investigación · {fila['nombre']}")
    tareas.add_task(
        servicio.tarea_investigacion,
        job_id=job_id,
        cuenta_id=cuenta_id,
        db_url=configuracion.DATABASE_URL,
    )
    return {"job_id": job_id, "estado": "pendiente"}


# ── PDF ───────────────────────────────────────────────────────────────────────

@router.post("/{cuenta_id}/pdf/generar", status_code=202)
async def generar_pdf(
    cuenta_id: UUID,
    tareas: BackgroundTasks,
    contexto: str | None = Query(default=None),
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    estrategia_ia: str = Query(default="rapida"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    ctx = await _resolver_contexto_job(
        conexion=conexion,
        cuenta_id=cuenta_id,
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
    )
    if ctx.tipo in {"cuenta", "cliente"} and ctx.contexto_id != cuenta_id:
        raise HTTPException(status_code=422, detail="El contexto de cuenta/cliente no coincide con la ruta.")
    if ctx.tipo == "oportunidad" and ctx.cuenta_id and ctx.cuenta_id != cuenta_id:
        raise HTTPException(status_code=422, detail="La oportunidad no pertenece a la cuenta indicada.")

    job_id = servicio.crear_job("pdf", f"PDF · {fila['nombre']}")
    tareas.add_task(
        servicio.tarea_pdf,
        job_id=job_id,
        cuenta_id=cuenta_id,
        usuario_id=UUID(usuario.usuario_id),
        db_url=configuracion.DATABASE_URL,
        contexto=contexto,
        contexto_tipo=ctx.tipo,
        contexto_id=ctx.contexto_id,
        estrategia_ia=estrategia_ia,
    )
    return {"job_id": job_id, "estado": "pendiente"}


# ── PPTX ──────────────────────────────────────────────────────────────────────

@router.post("/{cuenta_id}/pptx/generar", status_code=202)
async def generar_pptx(
    cuenta_id: UUID,
    tareas: BackgroundTasks,
    contexto: str | None = Query(default=None),
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    estrategia_ia: str = Query(default="rapida"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    ctx = await _resolver_contexto_job(
        conexion=conexion,
        cuenta_id=cuenta_id,
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
    )
    if ctx.tipo in {"cuenta", "cliente"} and ctx.contexto_id != cuenta_id:
        raise HTTPException(status_code=422, detail="El contexto de cuenta/cliente no coincide con la ruta.")
    if ctx.tipo == "oportunidad" and ctx.cuenta_id and ctx.cuenta_id != cuenta_id:
        raise HTTPException(status_code=422, detail="La oportunidad no pertenece a la cuenta indicada.")

    job_id = servicio.crear_job("pptx", f"Presentación · {fila['nombre']}")
    tareas.add_task(
        servicio.tarea_pptx,
        job_id=job_id,
        cuenta_id=cuenta_id,
        usuario_id=UUID(usuario.usuario_id),
        db_url=configuracion.DATABASE_URL,
        contexto=contexto,
        contexto_tipo=ctx.tipo,
        contexto_id=ctx.contexto_id,
        estrategia_ia=estrategia_ia,
    )
    return {"job_id": job_id, "estado": "pendiente"}


# ── Briefing ──────────────────────────────────────────────────────────────────

@router.post("/{cuenta_id}/briefing/generar", status_code=202)
async def generar_briefing(
    cuenta_id: UUID,
    tareas: BackgroundTasks,
    contexto: str | None = Query(default=None),
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    estrategia_ia: str = Query(default="rapida"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    ctx = await _resolver_contexto_job(
        conexion=conexion,
        cuenta_id=cuenta_id,
        contexto_tipo=contexto_tipo,
        contexto_id=contexto_id,
    )
    if ctx.tipo in {"cuenta", "cliente"} and ctx.contexto_id != cuenta_id:
        raise HTTPException(status_code=422, detail="El contexto de cuenta/cliente no coincide con la ruta.")
    if ctx.tipo == "oportunidad" and ctx.cuenta_id and ctx.cuenta_id != cuenta_id:
        raise HTTPException(status_code=422, detail="La oportunidad no pertenece a la cuenta indicada.")

    job_id = servicio.crear_job("briefing", f"Briefing · {fila['nombre']}")
    tareas.add_task(
        servicio.tarea_briefing,
        job_id=job_id,
        cuenta_id=cuenta_id,
        usuario_id=UUID(usuario.usuario_id),
        db_url=configuracion.DATABASE_URL,
        contexto=contexto,
        contexto_tipo=ctx.tipo,
        contexto_id=ctx.contexto_id,
        estrategia_ia=estrategia_ia,
    )
    return {"job_id": job_id, "estado": "pendiente"}


# ── Estudio IA ────────────────────────────────────────────────────────────────

@router.post("/{cuenta_id}/estudio-ia/generar", status_code=202)
async def generar_estudio_ia(
    cuenta_id: UUID,
    tareas: BackgroundTasks,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        "SELECT nombre FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    job_id = servicio.crear_job("estudio_ia", f"Estudio IA · {fila['nombre']}")
    tareas.add_task(
        servicio.tarea_estudio_ia,
        job_id=job_id,
        cuenta_id=cuenta_id,
        usuario_id=UUID(usuario.usuario_id),
        db_url=configuracion.DATABASE_URL,
    )
    return {"job_id": job_id, "estado": "pendiente"}


# ── Estudio IA: obtener último análisis ──────────────────────────────────────

@router.get("/{cuenta_id}/estudio-ia")
async def obtener_estudio_ia(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    fila = await conexion.fetchrow(
        """
        SELECT analisis, creado_en::TEXT AS creado_en
        FROM estudios_ia_cuentas
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Sin estudio IA para esta cuenta.")
    import json
    analisis = fila["analisis"]
    if isinstance(analisis, str):
        analisis = json.loads(analisis)
    return {"analisis": analisis, "creado_en": fila["creado_en"]}


# ── Polling de estado ─────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def estado_job(
    job_id: str,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    estado = servicio.estado_job(job_id)
    if not estado:
        raise HTTPException(status_code=404, detail="Job no encontrado.")
    return estado


# ── Archivos de cuenta (documentos manuales) ──────────────────────────────────

@router.post("/{cuenta_id}/archivos/subir", response_model=DocumentoCuentaRead, status_code=201)
async def subir_archivo_cuenta(
    cuenta_id: UUID,
    archivo: UploadFile = File(...),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Sube un archivo a la cuenta, extrae texto automáticamente (PDF/DOCX/TXT)."""
    fila = await conexion.fetchrow(
        "SELECT id FROM cuentas WHERE id = $1 AND eliminado_en IS NULL", cuenta_id
    )
    if not fila:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    contenido = await archivo.read()
    try:
        return await doc_servicio.subir_a_cuenta(
            conexion=conexion,
            cuenta_id=cuenta_id,
            usuario_id=UUID(usuario.usuario_id),
            nombre_original=archivo.filename or "archivo",
            contenido=contenido,
            tipo_mime=archivo.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{cuenta_id}/archivos", response_model=list[DocumentoCuentaRead])
async def listar_archivos_cuenta(
    cuenta_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    return await doc_servicio.listar_de_cuenta(conexion, cuenta_id)


@router.get("/{cuenta_id}/archivos/{doc_id}/contenido")
async def contenido_archivo(
    cuenta_id: UUID,
    doc_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    texto = await doc_servicio.obtener_contenido_extraido(conexion, doc_id, cuenta_id)
    if texto is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado o sin texto extraído.")
    return {"texto": texto}


@router.get("/{cuenta_id}/archivos/{doc_id}/descargar")
async def descargar_archivo_cuenta(
    cuenta_id: UUID,
    doc_id: UUID,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    resultado = await doc_servicio.descargar_de_cuenta(conexion, doc_id, cuenta_id)
    if not resultado:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    ruta, nombre = resultado
    return FileResponse(path=str(ruta), filename=nombre, media_type="application/octet-stream")


@router.delete("/{cuenta_id}/archivos/{doc_id}", status_code=204)
async def eliminar_archivo_cuenta(
    cuenta_id: UUID,
    doc_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    eliminado = await doc_servicio.eliminar_de_cuenta(
        conexion, doc_id, cuenta_id, UUID(usuario.usuario_id)
    )
    if not eliminado:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
