"""
Router del módulo de generación de Decks de Visita.
POST /decks/generar  → inicia generación en background, devuelve job_id
GET  /decks/status/{job_id}  → estado actual del job
GET  /decks/download/{job_id}  → descarga el .pptx generado
"""

import uuid

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.database import obtener_conexion
from app.modules.ia.proveedores import PROVEEDOR_LOCAL
from app.modules.decks.schemas import SolicitudDeck, RespuestaJob, EstadoJob
from app.config import configuracion
from app.modules.decks.servicio import (
    generar_deck_tarea,
    obtener_estado_job,
    TMP_DIR,
    _jobs,
)

router = APIRouter(prefix="/decks", tags=["decks"])


@router.post("/generar", response_model=RespuestaJob, status_code=202)
async def generar_deck(
    solicitud: SolicitudDeck,
    background_tasks: BackgroundTasks,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """Inicia la generación de un deck de visita en background.
    Precarga el catálogo y la matriz sectorial para enriquecer el prompt IA.
    """
    if solicitud.proveedor != PROVEEDOR_LOCAL:
        raise HTTPException(
            status_code=422,
            detail="Decks solo admite IA local (ollama).",
        )

    job_id = uuid.uuid4().hex

    # Precargar catálogo y matriz sectorial (antes de lanzar la tarea sync)
    try:
        catalogo = await conexion.fetch(
            "SELECT linea, servicio, entregables, normas_clave FROM catalogo_servicios WHERE normas_clave ILIKE $1 OR linea ILIKE $2 ORDER BY linea LIMIT 3",
            f"%{solicitud.norma}%",
            f"%{solicitud.norma}%",
        )
        if not catalogo:
            catalogo = await conexion.fetch(
                "SELECT linea, servicio, entregables, normas_clave FROM catalogo_servicios ORDER BY linea LIMIT 4"
            )
        catalogo_context = "\n".join(
            f"• {r['linea']}: {r['servicio'][:200]} | Entregables: {(r['entregables'] or '')[:150]} | Normas: {r['normas_clave'] or ''}"
            for r in catalogo
        )

        matriz = await conexion.fetchrow(
            "SELECT certificaciones_tipo, pain_points, servicios_sgs_tipo FROM matriz_sectorial WHERE sector ILIKE $1 LIMIT 1",
            f"%{solicitud.sector}%",
        )
        matriz_context = (
            f"Certificaciones típicas: {matriz['certificaciones_tipo']}\nPain points: {matriz['pain_points']}\nServicios SGS aplicables: {matriz['servicios_sgs_tipo']}"
            if matriz else ""
        )
    except Exception:
        catalogo_context = ""
        matriz_context = ""

    _jobs[job_id] = {
        "estado": EstadoJob.pendiente,
        "progreso": 0,
        "mensaje": "En cola...",
        "archivo": None,
    }

    from uuid import UUID
    background_tasks.add_task(
        generar_deck_tarea,
        job_id,
        solicitud,
        catalogo_context,
        matriz_context,
        {
            "proveedor": solicitud.proveedor,
            "ollama_url": solicitud.ollama_url or configuracion.OLLAMA_URL,
            "ollama_modelo": solicitud.ollama_modelo or configuracion.OLLAMA_MODEL_DEFAULT,
        },
        usuario_id=UUID(usuario.usuario_id),
        db_url=configuracion.DATABASE_URL,
    )

    return RespuestaJob(
        job_id=job_id,
        estado=EstadoJob.pendiente,
        progreso=0,
        mensaje="En cola...",
    )


@router.get("/status/{job_id}", response_model=RespuestaJob)
async def estado_deck(
    job_id: str,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Devuelve el estado actual del job de generación."""
    job = obtener_estado_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    return RespuestaJob(job_id=job_id, **job)


@router.get("/download/{job_id}")
async def descargar_deck(
    job_id: str,
    _usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
):
    """Descarga el .pptx generado cuando el job está completado."""
    job = obtener_estado_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    if job["estado"] != EstadoJob.completado:
        raise HTTPException(status_code=409, detail="El deck aún no está listo")

    archivo = job.get("archivo")
    if not archivo:
        raise HTTPException(status_code=500, detail="Archivo no encontrado")

    ruta = TMP_DIR / archivo
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo expirado o eliminado")

    return FileResponse(
        path=str(ruta),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=archivo,
    )
