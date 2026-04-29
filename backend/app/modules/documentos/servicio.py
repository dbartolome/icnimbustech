"""
Lógica de negocio del módulo Documentos.
Almacenamiento local en dev — migrar a Supabase Storage en producción.
"""

import uuid
import tempfile
from pathlib import Path
from uuid import UUID

import asyncpg

from app.modules.documentos.schemas import DocumentoRead, DocumentoCuentaRead
from app.skills.extraer_texto import extraer_texto

# Directorio preferido + fallback para entornos donde /app/uploads no sea escribible.
_CANDIDATOS_UPLOADS = [
    Path("/app/uploads"),
    Path(tempfile.gettempdir()) / "sgs_uploads",
    Path(__file__).parent.parent.parent.parent / "uploads",
]
_DIRECTORIO_UPLOADS_EFECTIVO: Path | None = None
TAMAÑO_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
EXTENSIONES_PERMITIDAS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".txt", ".csv", ".png",
    ".jpg", ".jpeg", ".gif", ".zip",
    # Audio (para transcripción)
    ".mp3", ".wav", ".m4a", ".ogg", ".webm",
}


def _resolver_directorio_uploads() -> Path:
    """
    Devuelve un directorio escribible para almacenar documentos.
    Si /app/uploads no permite escritura (volumen con permisos restrictivos),
    cae automáticamente a /tmp/sgs_uploads.
    """
    global _DIRECTORIO_UPLOADS_EFECTIVO
    if _DIRECTORIO_UPLOADS_EFECTIVO is not None:
        return _DIRECTORIO_UPLOADS_EFECTIVO

    for candidato in _CANDIDATOS_UPLOADS:
        try:
            candidato.mkdir(parents=True, exist_ok=True)
            prueba = candidato / ".write_test"
            prueba.write_text("ok", encoding="utf-8")
            prueba.unlink(missing_ok=True)
            _DIRECTORIO_UPLOADS_EFECTIVO = candidato
            return candidato
        except Exception:
            continue

    # Si todos fallan, dejamos que pathlib lance un error explícito al escribir.
    _DIRECTORIO_UPLOADS_EFECTIVO = _CANDIDATOS_UPLOADS[-1]
    return _DIRECTORIO_UPLOADS_EFECTIVO


def ruta_documento(nombre_guardado: str) -> Path:
    return _resolver_directorio_uploads() / nombre_guardado


async def subir_documento(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    nombre_original: str,
    contenido: bytes,
    tipo_mime: str | None,
    oportunidad_id: UUID | None,
    cuenta_id: UUID | None = None,
) -> DocumentoRead:
    extension = Path(nombre_original).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Tipo de archivo no permitido: {extension}")

    if len(contenido) > TAMAÑO_MAX_BYTES:
        raise ValueError("El archivo supera el límite de 10 MB.")

    nombre_guardado = f"{uuid.uuid4()}{extension}"
    ruta = ruta_documento(nombre_guardado)
    _resolver_directorio_uploads().mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    fila = await conexion.fetchrow(
        """
        INSERT INTO documentos
            (usuario_id, oportunidad_id, cuenta_id, nombre_original, nombre_guardado, tipo_mime, tamaño_bytes)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, nombre_original, tipo_mime, tamaño_bytes, oportunidad_id, cuenta_id,
                  creado_en::TEXT AS creado_en,
                  FALSE AS tiene_transcripcion
        """,
        usuario_id, oportunidad_id, cuenta_id, nombre_original,
        nombre_guardado, tipo_mime, len(contenido),
    )

    oportunidad_nombre: str | None = None
    if oportunidad_id:
        oportunidad_nombre = await conexion.fetchval(
            "SELECT nombre FROM oportunidades WHERE id = $1", oportunidad_id
        )

    cuenta_nombre: str | None = None
    if cuenta_id:
        cuenta_nombre = await conexion.fetchval(
            "SELECT nombre FROM cuentas WHERE id = $1", cuenta_id
        )

    return DocumentoRead(**dict(fila), oportunidad_nombre=oportunidad_nombre, cuenta_nombre=cuenta_nombre)


async def listar_documentos(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    oportunidad_id: UUID | None,
    busqueda: str | None,
    pagina: int,
    por_pagina: int,
    sort_by: str = "creado_en",
    sort_dir: str = "desc",
) -> dict:
    condiciones = ["d.usuario_id = $1"]
    params: list = [usuario_id]
    n = 2

    if oportunidad_id:
        condiciones.append(f"d.oportunidad_id = ${n}")
        params.append(oportunidad_id)
        n += 1

    if busqueda:
        condiciones.append(f"d.nombre_original ILIKE ${n}")
        params.append(f"%{busqueda}%")
        n += 1

    where = "WHERE " + " AND ".join(condiciones)
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    campos_validos = {
        "nombre_original": "d.nombre_original",
        "tipo_mime": "d.tipo_mime",
        "tamano_bytes": "d.tamaño_bytes",
        "creado_en": "d.creado_en",
    }
    campo_orden = campos_validos.get(sort_by.lower(), "d.creado_en")

    total = await conexion.fetchval(
        f"SELECT COUNT(*) FROM documentos d {where}", *params
    )
    offset = (pagina - 1) * por_pagina
    filas = await conexion.fetch(
        f"""
        SELECT
            d.id, d.nombre_original, d.tipo_mime, d.tamaño_bytes,
            d.oportunidad_id, o.nombre AS oportunidad_nombre,
            d.cuenta_id, c.nombre AS cuenta_nombre,
            d.creado_en::TEXT AS creado_en,
            (d.transcripcion_texto IS NOT NULL) AS tiene_transcripcion
        FROM documentos d
        LEFT JOIN oportunidades o ON o.id = d.oportunidad_id
        LEFT JOIN cuentas c ON c.id = d.cuenta_id
        {where}
        ORDER BY {campo_orden} {direccion} NULLS LAST, d.id DESC
        LIMIT ${n} OFFSET ${n + 1}
        """,
        *params, por_pagina, offset,
    )

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [DocumentoRead(**dict(f)) for f in filas],
    }


async def obtener_ruta_descarga(
    conexion: asyncpg.Connection,
    documento_id: UUID,
    usuario_id: UUID,
) -> tuple[Path, str] | None:
    """Devuelve (ruta_local, nombre_original) o None si no existe."""
    fila = await conexion.fetchrow(
        "SELECT nombre_guardado, nombre_original FROM documentos WHERE id = $1 AND usuario_id = $2",
        documento_id, usuario_id,
    )
    if not fila:
        return None

    ruta = ruta_documento(fila["nombre_guardado"])
    if not ruta.exists():
        return None

    return ruta, fila["nombre_original"]


async def eliminar_documento(
    conexion: asyncpg.Connection,
    documento_id: UUID,
    usuario_id: UUID,
) -> bool:
    fila = await conexion.fetchrow(
        "SELECT nombre_guardado FROM documentos WHERE id = $1 AND usuario_id = $2",
        documento_id, usuario_id,
    )
    if not fila:
        return False

    ruta = ruta_documento(fila["nombre_guardado"])
    if ruta.exists():
        ruta.unlink()

    await conexion.execute(
        "DELETE FROM documentos WHERE id = $1 AND usuario_id = $2",
        documento_id, usuario_id,
    )
    return True


# ── Documentos por cuenta ─────────────────────────────────────────────────────

async def subir_a_cuenta(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
    usuario_id: UUID,
    nombre_original: str,
    contenido: bytes,
    tipo_mime: str | None,
) -> "DocumentoCuentaRead":
    """Sube un documento asociado a una cuenta y extrae su texto."""
    extension = Path(nombre_original).suffix.lower()
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError(f"Tipo de archivo no permitido: {extension}")
    if len(contenido) > TAMAÑO_MAX_BYTES:
        raise ValueError("El archivo supera el límite de 10 MB.")

    nombre_guardado = f"{uuid.uuid4()}{extension}"
    ruta = ruta_documento(nombre_guardado)
    _resolver_directorio_uploads().mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)

    texto = extraer_texto(contenido, nombre_original, tipo_mime)

    fila = await conexion.fetchrow(
        """
        INSERT INTO documentos
            (usuario_id, cuenta_id, nombre_original, nombre_guardado, tipo_mime, tamaño_bytes, contenido_extraido)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, nombre_original, tipo_mime, tamaño_bytes, creado_en::TEXT AS creado_en
        """,
        usuario_id, cuenta_id, nombre_original,
        nombre_guardado, tipo_mime, len(contenido), texto or None,
    )

    return DocumentoCuentaRead(
        id=fila["id"],
        nombre_original=fila["nombre_original"],
        tipo_mime=fila["tipo_mime"],
        tamaño_bytes=fila["tamaño_bytes"],
        creado_en=fila["creado_en"],
        tiene_texto=bool(texto),
    )


async def listar_de_cuenta(
    conexion: asyncpg.Connection,
    cuenta_id: UUID,
) -> list["DocumentoCuentaRead"]:
    filas = await conexion.fetch(
        """
        SELECT id, nombre_original, tipo_mime, tamaño_bytes,
               contenido_extraido IS NOT NULL AND contenido_extraido <> '' AS tiene_texto,
               creado_en::TEXT AS creado_en
        FROM documentos
        WHERE cuenta_id = $1
        ORDER BY creado_en DESC
        """,
        cuenta_id,
    )
    return [DocumentoCuentaRead(**dict(f)) for f in filas]


async def obtener_contenido_extraido(
    conexion: asyncpg.Connection,
    documento_id: UUID,
    cuenta_id: UUID,
) -> str | None:
    return await conexion.fetchval(
        "SELECT contenido_extraido FROM documentos WHERE id = $1 AND cuenta_id = $2",
        documento_id, cuenta_id,
    )


async def eliminar_de_cuenta(
    conexion: asyncpg.Connection,
    documento_id: UUID,
    cuenta_id: UUID,
    usuario_id: UUID,
) -> bool:
    fila = await conexion.fetchrow(
        "SELECT nombre_guardado FROM documentos WHERE id = $1 AND cuenta_id = $2 AND usuario_id = $3",
        documento_id, cuenta_id, usuario_id,
    )
    if not fila:
        return False

    ruta = ruta_documento(fila["nombre_guardado"])
    if ruta.exists():
        ruta.unlink()

    await conexion.execute(
        "DELETE FROM documentos WHERE id = $1",
        documento_id,
    )
    return True


async def descargar_de_cuenta(
    conexion: asyncpg.Connection,
    documento_id: UUID,
    cuenta_id: UUID,
) -> tuple[Path, str] | None:
    fila = await conexion.fetchrow(
        "SELECT nombre_guardado, nombre_original FROM documentos WHERE id = $1 AND cuenta_id = $2",
        documento_id, cuenta_id,
    )
    if not fila:
        return None
    ruta = ruta_documento(fila["nombre_guardado"])
    if not ruta.exists():
        return None
    return ruta, fila["nombre_original"]
