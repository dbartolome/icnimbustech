"""
Endpoints del módulo Importación CSV.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.auth.dependencies import UsuarioAutenticado, requerir_rol
from app.database import obtener_conexion
from app.modules.importacion import servicio

router = APIRouter(prefix="/importacion", tags=["importacion"])

MODOS_PERMITIDOS = {"append", "upsert", "reset"}
TAMANO_MAXIMO = 10 * 1024 * 1024  # 10 MB


class PeticionChatCsv(BaseModel):
    pregunta: str
    importacion_id: UUID | None = None


@router.post("/csv", status_code=status.HTTP_202_ACCEPTED)
async def importar_csv(
    archivo: UploadFile = File(...),
    modo: str = Form(default="reset"),
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    # Validar extensión
    if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se aceptan archivos .csv",
        )

    # Validar modo
    if modo not in MODOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Modo inválido. Opciones: {', '.join(MODOS_PERMITIDOS)}",
        )

    contenido = await archivo.read()

    # Validar tamaño
    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 10 MB.",
        )

    # Crear registro de importación
    importacion_id = await conexion.fetchval(
        """INSERT INTO importaciones (usuario_id, nombre_archivo, modo, estado)
           VALUES ($1, $2, $3, 'procesando') RETURNING id""",
        UUID(usuario.usuario_id), archivo.filename, modo,
    )

    # Procesar de forma síncrona (se migrará a background task en producción)
    await servicio.procesar_csv(
        conexion,
        importacion_id,
        contenido,
        modo,
        forzar_propietario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
    )

    estado = await servicio.obtener_estado(
        conexion,
        importacion_id,
        usuario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
    )
    return estado


@router.get("/{importacion_id}/estado")
async def estado_importacion(
    importacion_id: UUID,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    estado = await servicio.obtener_estado(
        conexion,
        importacion_id,
        usuario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
    )
    if not estado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importación no encontrada.")
    return estado


@router.get("/historial")
async def historial(
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    return await servicio.listar_historial(
        conexion,
        usuario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
    )


@router.delete("/{importacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_importacion(
    importacion_id: UUID,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    filas = await conexion.execute(
        """DELETE FROM importaciones
           WHERE id = $1
             AND ($2 OR usuario_id = $3)""",
        importacion_id,
        not usuario.es_comercial,
        UUID(usuario.usuario_id),
    )
    if filas == "DELETE 0":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importación no encontrada.")


@router.post("/chat")
async def chat_csv(
    payload: PeticionChatCsv,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    try:
        return await servicio.responder_chat_csv(
            conexion,
            usuario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
            pregunta=payload.pregunta,
            importacion_id=payload.importacion_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Fallo del chat CSV: {exc}",
        )


@router.get("/{importacion_id}/preview")
async def preview_importacion(
    importacion_id: UUID,
    usuario: UsuarioAutenticado = Depends(requerir_rol("admin", "manager", "supervisor", "comercial")),
    conexion=Depends(obtener_conexion),
):
    vista = await servicio.obtener_preview_importacion(
        conexion,
        importacion_id=importacion_id,
        usuario_id=UUID(usuario.usuario_id) if usuario.es_comercial else None,
    )
    if not vista:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importación no encontrada.")
    return vista
