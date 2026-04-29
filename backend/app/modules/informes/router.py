"""
Router del módulo Informes PDF.
"""

from uuid import UUID

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.auth.dependencies import UsuarioAutenticado, obtener_usuario_actual
from app.config import configuracion
from app.database import obtener_conexion
from app.modules.ia.proveedores import PROVEEDOR_LOCAL
from app.modules.ia.contexto import resolver_contexto
from app.modules.informes import servicio
from app.modules.informes.schemas import EstadoJob, InformeResumen, RespuestaJob, SolicitudInforme

router = APIRouter(prefix="/informes", tags=["informes"])


@router.post("/generar", response_model=RespuestaJob, status_code=status.HTTP_202_ACCEPTED)
async def generar_informe(
    solicitud: SolicitudInforme,
    tareas: BackgroundTasks,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    if solicitud.proveedor != PROVEEDOR_LOCAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informes solo admite IA local (ollama).",
        )

    job_id, informe_id = await servicio.iniciar_generacion(
        conexion=conexion,
        usuario_id=UUID(usuario.usuario_id),
        usuario_nombre=usuario.email,
        solicitud=solicitud,
    )

    tareas.add_task(
        servicio.generar_informe_tarea,
        job_id=job_id,
        informe_id=informe_id,
        usuario_id=UUID(usuario.usuario_id),
        usuario_nombre=usuario.email,
        usuario_rol=usuario.rol,
        solicitud=solicitud,
        db_url=configuracion.DATABASE_URL,
        ia_config={
            "proveedor": solicitud.proveedor,
            "ollama_url": solicitud.ollama_url,
            "ollama_modelo": solicitud.ollama_modelo,
        },
    )

    return RespuestaJob(job_id=job_id, estado="pendiente", mensaje="Generación iniciada.")


@router.get("/status/{job_id}", response_model=EstadoJob)
async def estado_job(job_id: str):
    estado = servicio._estado_job(job_id)
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado.")
    return EstadoJob(
        job_id=job_id,
        estado=estado["estado"],
        progreso=estado["progreso"],
        paso_actual=estado.get("paso_actual"),
        indice=estado.get("indice"),
    )


@router.get("", response_model=list[InformeResumen])
async def listar_informes(
    pagina: int = Query(default=1, ge=1),
    por_pagina: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="creado_en"),
    sort_dir: str = Query(default="desc"),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    filas = await servicio.listar_informes(
        conexion,
        UUID(usuario.usuario_id),
        pagina=pagina,
        por_pagina=por_pagina,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return [InformeResumen(**f) for f in filas]


@router.get("/{informe_id}/descargar")
async def descargar_informe(
    informe_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    ruta = await servicio.obtener_ruta_pdf(conexion, informe_id, UUID(usuario.usuario_id))
    if not ruta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Informe no encontrado o no completado.")
    return FileResponse(
        path=str(ruta),
        filename=f"informe_sgs_{informe_id}.pdf",
        media_type="application/pdf",
    )


@router.post("/cuenta/{cuenta_id}/pdf", status_code=status.HTTP_200_OK)
async def generar_pdf_cuenta(
    cuenta_id: UUID,
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Genera PDF para una cuenta, lo sube a MinIO, registra en historial y lo devuelve.
    """
    from fastapi.responses import Response
    from app.skills.generar_pdf import generar_pdf_cuenta as skill_pdf
    from app.modules.historial import servicio as historial_servicio

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
        contenido, nombre_fichero = await skill_pdf(cuenta_id, conexion)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {e}")

    try:
        from app.modules.plantillas import servicio as plantillas_servicio
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conexion, "pdf")
        await historial_servicio.registrar_documento(
            conexion,
            cuenta_id=cuenta_id,
            usuario_id=UUID(usuario.usuario_id),
            tipo="pdf",
            nombre_fichero=nombre_fichero,
            contenido=contenido,
            contexto_tipo=ctx.tipo,
            contexto_id=ctx.contexto_id,
            metadatos={
                "plantilla_id": str(plantilla_activa["id"]) if plantilla_activa else None,
                "plantilla_nombre": plantilla_activa["nombre"] if plantilla_activa else None,
            },
        )
    except Exception:
        pass  # El historial falla en silencio — el fichero se devuelve igualmente

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


@router.post("/cuenta/{cuenta_id}/pptx", status_code=status.HTTP_200_OK)
async def generar_pptx_cuenta(
    cuenta_id: UUID,
    contexto_tipo: str | None = Query(default="cuenta"),
    contexto_id: UUID | None = Query(default=None),
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    """
    Genera PPTX para una cuenta, lo sube a MinIO, registra en historial y lo devuelve.
    """
    from fastapi.responses import Response
    from app.skills.generar_pptx import generar_pptx_cuenta as skill_pptx
    from app.modules.historial import servicio as historial_servicio

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
        contenido, nombre_fichero = await skill_pptx(cuenta_id, conexion)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando PPTX: {e}")

    try:
        from app.modules.plantillas import servicio as plantillas_servicio
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conexion, "pptx")
        await historial_servicio.registrar_documento(
            conexion,
            cuenta_id=cuenta_id,
            usuario_id=UUID(usuario.usuario_id),
            tipo="pptx",
            nombre_fichero=nombre_fichero,
            contenido=contenido,
            contexto_tipo=ctx.tipo,
            contexto_id=ctx.contexto_id,
            metadatos={
                "plantilla_id": str(plantilla_activa["id"]) if plantilla_activa else None,
                "plantilla_nombre": plantilla_activa["nombre"] if plantilla_activa else None,
            },
        )
    except Exception:
        pass  # El historial falla en silencio — el fichero se devuelve igualmente

    MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    return Response(
        content=contenido,
        media_type=MIME_PPTX,
        headers={"Content-Disposition": f'attachment; filename="{nombre_fichero}"'},
    )


@router.delete("/{informe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_informe(
    informe_id: UUID,
    usuario: UsuarioAutenticado = Depends(obtener_usuario_actual),
    conexion: asyncpg.Connection = Depends(obtener_conexion),
):
    eliminado = await servicio.eliminar_informe(conexion, informe_id, UUID(usuario.usuario_id))
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Informe no encontrado.")
