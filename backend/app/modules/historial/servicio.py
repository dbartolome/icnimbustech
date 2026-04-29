"""
Lógica de negocio del módulo Historial de documentos.
"""

import json
from uuid import UUID

import asyncpg

from app import storage


async def registrar_documento(
    conexion: asyncpg.Connection,
    cuenta_id: UUID | None,
    usuario_id: UUID,
    tipo: str,
    nombre_fichero: str,
    contenido: bytes,
    contexto_tipo: str | None = None,
    contexto_id: UUID | None = None,
    metadatos: dict | None = None,
) -> dict:
    """
    Sube el fichero a MinIO y registra la entrada en historial_documentos.
    Devuelve el registro creado.
    """
    storage_key = f"comercial_{usuario_id}/{tipo}/{nombre_fichero}"
    await storage.subir_fichero(storage_key, contenido, _content_type(tipo))

    contexto_tipo_final = (contexto_tipo or "cuenta").strip().lower()
    if contexto_id is None and cuenta_id is not None and contexto_tipo_final in {"cuenta", "cliente"}:
        contexto_id = cuenta_id

    fila = await conexion.fetchrow(
        """
        INSERT INTO historial_documentos
            (
                cuenta_id, usuario_id, tipo, nombre_fichero, storage_key, tamano_bytes, metadatos,
                contexto_tipo, contexto_id
            )
        VALUES ($1, $2, $3::tipo_documento_generado, $4, $5, $6, $7, $8::contexto_ia_tipo, $9)
        RETURNING id, cuenta_id, usuario_id, tipo, nombre_fichero,
                  storage_key, tamano_bytes, metadatos, contexto_tipo, contexto_id,
                  creado_en::TEXT AS creado_en
        """,
        cuenta_id,
        usuario_id,
        tipo,
        nombre_fichero,
        storage_key,
        len(contenido),
        json.dumps(metadatos or {}),
        contexto_tipo_final,
        contexto_id,
    )
    registro = dict(fila)

    # Reflejar en biblioteca unificada de artefactos IA (fallo silencioso para no romper flujo legacy).
    try:
        from app.modules.artefactos import servicio as artefactos_servicio

        texto_resultado = None
        if tipo == "briefing":
            texto_resultado = contenido.decode("utf-8", errors="replace")

        clave = f"{contexto_tipo_final}:{str(contexto_id or cuenta_id)}:{tipo}"
        meta_artefacto = dict(metadatos or {})
        meta_artefacto["clave_regeneracion"] = clave
        meta_artefacto["nombre_fichero"] = nombre_fichero

        fuentes = []
        try:
            contexto_prev = await artefactos_servicio.obtener_contexto_relevante(
                conexion,
                usuario_id=usuario_id,
                es_admin=False,
                entidad_tipo=contexto_tipo_final,
                entidad_id=contexto_id,
                cuenta_id=cuenta_id,
                limit=3,
            )
            fuentes = [
                {"fuente_artefacto_id": item.get("id"), "fuente_tipo": "artefacto"}
                for item in contexto_prev
                if item.get("id")
            ]
        except Exception:
            fuentes = []

        await artefactos_servicio.registrar_version_artefacto(
            conexion,
            tipo="documento",
            subtipo=tipo,
            entidad_tipo=contexto_tipo_final,
            entidad_id=contexto_id,
            cuenta_id=cuenta_id,
            usuario_id=usuario_id,
            titulo=nombre_fichero,
            prompt=None,
            resultado_texto=texto_resultado,
            resultado_json={},
            storage_key=storage_key,
            modelo=(metadatos or {}).get("modelo") if metadatos else None,
            plantilla_id=None,
            metadatos=meta_artefacto,
            fuentes=fuentes,
            origen_tabla="historial_documentos",
            origen_id=str(registro["id"]),
        )
    except Exception:
        pass

    return registro


async def listar_historial(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    es_admin: bool,
    cuenta_id: UUID | None = None,
    contexto_tipo: str | None = None,
    contexto_id: UUID | None = None,
    pagina: int = 1,
    por_pagina: int = 100,
    sort_by: str = "creado_en",
    sort_dir: str = "desc",
) -> list[dict]:
    """
    Comercial ve solo sus propios documentos.
    Admin/manager ven todos (filtrados por cuenta si se pasa cuenta_id).
    """
    condiciones = []
    args: list = []

    if not es_admin:
        args.append(usuario_id)
        condiciones.append(f"hd.usuario_id = ${len(args)}")

    if cuenta_id:
        args.append(cuenta_id)
        condiciones.append(f"hd.cuenta_id = ${len(args)}")

    if contexto_tipo:
        args.append(contexto_tipo)
        condiciones.append(f"hd.contexto_tipo = ${len(args)}::contexto_ia_tipo")

    if contexto_id:
        args.append(contexto_id)
        condiciones.append(f"hd.contexto_id = ${len(args)}")

    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    campos_validos = {
        "tipo": "hd.tipo",
        "nombre_fichero": "hd.nombre_fichero",
        "tamano_bytes": "hd.tamano_bytes",
        "creado_en": "hd.creado_en",
        "cuenta_nombre": "c.nombre",
        "usuario_nombre": "u.nombre_completo",
    }
    campo_orden = campos_validos.get(sort_by.lower(), "hd.creado_en")
    offset = (pagina - 1) * por_pagina

    filas = await conexion.fetch(
        f"""
        SELECT
            hd.id, hd.tipo, hd.nombre_fichero, hd.tamano_bytes, hd.metadatos,
            hd.contexto_tipo, hd.contexto_id,
            hd.creado_en::TEXT AS creado_en,
            c.nombre AS cuenta_nombre,
            u.nombre_completo AS usuario_nombre
        FROM historial_documentos hd
        LEFT JOIN cuentas c ON c.id = hd.cuenta_id
        JOIN usuarios u ON u.id = hd.usuario_id
        {where}
        ORDER BY {campo_orden} {direccion} NULLS LAST, hd.id DESC
        LIMIT ${len(args) + 1}
        OFFSET ${len(args) + 2}
        """,
        *args,
        por_pagina,
        offset,
    )
    return [dict(f) for f in filas]


async def listar_artefactos_ia(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    es_admin: bool,
    contexto_tipo: str | None = None,
    contexto_id: UUID | None = None,
    pagina: int = 1,
    por_pagina: int = 50,
    sort_by: str = "creado_en",
    sort_dir: str = "desc",
) -> dict:
    condiciones_doc = []
    condiciones_inf = []
    condiciones_chat = []
    condiciones_audio = []
    args: list = []

    if not es_admin:
        args.append(usuario_id)
        condiciones_doc.append(f"hd.usuario_id = ${len(args)}")
        condiciones_inf.append(f"ig.usuario_id = ${len(args)}")
        condiciones_chat.append(f"ci.usuario_id = ${len(args)}")
        condiciones_audio.append(f"sa.usuario_id = ${len(args)}")

    if contexto_tipo:
        args.append(contexto_tipo)
        condiciones_doc.append(f"hd.contexto_tipo = ${len(args)}::contexto_ia_tipo")

    if contexto_id:
        args.append(contexto_id)
        condiciones_doc.append(f"hd.contexto_id = ${len(args)}")
        condiciones_inf.append(f"ig.id = ${len(args)}")
        condiciones_chat.append(f"ci.cuenta_id = ${len(args)}")
        condiciones_audio.append(f"sa.propietario_objetivo = ${len(args)}")

    where_doc = ("WHERE " + " AND ".join(condiciones_doc)) if condiciones_doc else ""
    where_inf = ("WHERE " + " AND ".join(condiciones_inf)) if condiciones_inf else ""
    where_chat = ("WHERE " + " AND ".join(condiciones_chat)) if condiciones_chat else ""
    where_audio = ("WHERE " + " AND ".join(condiciones_audio)) if condiciones_audio else ""

    campos_validos = {
        "tipo": "tipo",
        "titulo": "titulo",
        "contexto_tipo": "contexto_tipo",
        "usuario_nombre": "usuario_nombre",
        "creado_en": "creado_en",
    }
    campo_orden = campos_validos.get(sort_by.lower(), "creado_en")
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    offset = (pagina - 1) * por_pagina
    limit_pos = len(args) + 1
    offset_pos = len(args) + 2

    filas = await conexion.fetch(
        f"""
        SELECT * FROM (
            SELECT
                hd.id::TEXT AS id,
                'documento'::TEXT AS tipo,
                hd.tipo::TEXT AS subtipo,
                hd.nombre_fichero AS titulo,
                hd.contexto_tipo::TEXT AS contexto_tipo,
                hd.contexto_id::TEXT AS contexto_id,
                COALESCE(c.nombre, 'N/A') AS entidad_nombre,
                u.nombre_completo AS usuario_nombre,
                hd.creado_en::TEXT AS creado_en,
                jsonb_build_object(
                    'tamano_bytes', hd.tamano_bytes,
                    'metadatos', hd.metadatos
                ) AS extra
            FROM historial_documentos hd
            LEFT JOIN cuentas c ON c.id = hd.cuenta_id
            JOIN usuarios u ON u.id = hd.usuario_id
            {where_doc}

            UNION ALL

            SELECT
                ig.id::TEXT AS id,
                'informe'::TEXT AS tipo,
                ig.tipo::TEXT AS subtipo,
                ig.titulo AS titulo,
                'informe'::TEXT AS contexto_tipo,
                ig.id::TEXT AS contexto_id,
                COALESCE(ig.destinatario, 'N/A') AS entidad_nombre,
                u.nombre_completo AS usuario_nombre,
                ig.creado_en::TEXT AS creado_en,
                jsonb_build_object(
                    'estado', ig.estado::TEXT,
                    'paginas', ig.paginas,
                    'periodo', ig.periodo
                ) AS extra
            FROM informes_generados ig
            JOIN usuarios u ON u.id = ig.usuario_id
            {where_inf}

            UNION ALL

            SELECT
                ci.id::TEXT AS id,
                'chat'::TEXT AS tipo,
                'copilot'::TEXT AS subtipo,
                COALESCE(substring(ci.respuesta, 1, 120), 'Conversación') AS titulo,
                'cuenta'::TEXT AS contexto_tipo,
                ci.cuenta_id::TEXT AS contexto_id,
                COALESCE(c.nombre, 'N/A') AS entidad_nombre,
                u.nombre_completo AS usuario_nombre,
                ci.creado_en::TEXT AS creado_en,
                jsonb_build_object(
                    'mensajes', COALESCE(jsonb_array_length(ci.mensajes), 0),
                    'rol_usuario', ci.rol_usuario
                ) AS extra
            FROM conversaciones_ia ci
            LEFT JOIN cuentas c ON c.id = ci.cuenta_id
            JOIN usuarios u ON u.id = ci.usuario_id
            {where_chat}

            UNION ALL

            SELECT
                sa.id::TEXT AS id,
                'audio'::TEXT AS tipo,
                'briefing'::TEXT AS subtipo,
                ('Briefing ' || sa.foco) AS titulo,
                'comercial'::TEXT AS contexto_tipo,
                sa.propietario_objetivo::TEXT AS contexto_id,
                COALESCE(uo.nombre_completo, 'N/A') AS entidad_nombre,
                uu.nombre_completo AS usuario_nombre,
                sa.creado_en::TEXT AS creado_en,
                jsonb_build_object(
                    'foco', sa.foco,
                    'duracion_min', sa.duracion_min,
                    'duracion_estimada_seg', sa.duracion_estimada_seg
                ) AS extra
            FROM sesiones_audio sa
            JOIN usuarios uu ON uu.id = sa.usuario_id
            LEFT JOIN usuarios uo ON uo.id = sa.propietario_objetivo
            {where_audio}
        ) artefactos
        ORDER BY {campo_orden} {direccion} NULLS LAST, id DESC
        LIMIT ${limit_pos} OFFSET ${offset_pos}
        """,
        *args,
        por_pagina,
        offset,
    )

    return {
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [dict(f) for f in filas],
    }


async def obtener_url_descarga(
    conexion: asyncpg.Connection,
    doc_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
    expires: int = 3600,
) -> str | None:
    """
    Genera URL prefirmada (1h). Comercial solo accede a sus propios documentos.
    """
    condicion_usuario = "" if es_admin else "AND hd.usuario_id = $2"
    args = [doc_id] if es_admin else [doc_id, usuario_id]

    fila = await conexion.fetchrow(
        f"SELECT storage_key FROM historial_documentos hd WHERE hd.id = $1 {condicion_usuario}",
        *args,
    )
    if not fila:
        return None

    return await storage.obtener_url_descarga(fila["storage_key"], expires)


async def obtener_documento_descarga(
    conexion: asyncpg.Connection,
    doc_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> dict | None:
    """
    Obtiene nombre/tipo/contenido de un documento generado.
    Se usa para servir descarga directa desde backend (sin URL prefirmada externa).
    """
    condicion_usuario = "" if es_admin else "AND hd.usuario_id = $2"
    args = [doc_id] if es_admin else [doc_id, usuario_id]
    fila = await conexion.fetchrow(
        f"""
        SELECT hd.nombre_fichero, hd.tipo::TEXT AS tipo, hd.storage_key
        FROM historial_documentos hd
        WHERE hd.id = $1 {condicion_usuario}
        """,
        *args,
    )
    if not fila:
        return None
    contenido = await storage.descargar_fichero(fila["storage_key"])
    return {
        "nombre_fichero": fila["nombre_fichero"],
        "tipo": fila["tipo"],
        "contenido": contenido,
    }


async def eliminar_documento(
    conexion: asyncpg.Connection,
    doc_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> bool:
    """
    Elimina de MinIO y de DB. Comercial solo puede borrar los suyos.
    """
    condicion_usuario = "" if es_admin else "AND usuario_id = $2"
    args = [doc_id] if es_admin else [doc_id, usuario_id]

    fila = await conexion.fetchrow(
        f"SELECT storage_key FROM historial_documentos WHERE id = $1 {condicion_usuario}",
        *args,
    )
    if not fila:
        return False

    await storage.eliminar_fichero(fila["storage_key"])
    await conexion.execute(
        "DELETE FROM historial_documentos WHERE id = $1",
        doc_id,
    )
    return True


# =============================================================================
# Compartición pública
# =============================================================================

async def crear_token_comparticion(
    conexion: asyncpg.Connection,
    doc_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
    dias_expiracion: int = 7,
) -> dict | None:
    condicion = "" if es_admin else "AND usuario_id = $2"
    args = [doc_id] if es_admin else [doc_id, usuario_id]
    existe = await conexion.fetchval(
        f"SELECT id FROM historial_documentos WHERE id = $1 {condicion}",
        *args,
    )
    if not existe:
        return None

    fila = await conexion.fetchrow(
        """
        INSERT INTO artefacto_compartidos (doc_id, creado_por, expira_en)
        VALUES ($1, $2, now() + ($3 || ' days')::INTERVAL)
        RETURNING token, expira_en::TEXT AS expira_en
        """,
        doc_id,
        usuario_id,
        str(dias_expiracion),
    )
    return dict(fila)


async def obtener_documento_compartido(
    conexion: asyncpg.Connection,
    token: str,
) -> dict | None:
    fila = await conexion.fetchrow(
        """
        SELECT ac.doc_id, ac.documentos_id,
               hd.storage_key, hd.nombre_fichero, hd.tipo::TEXT AS tipo,
               d.nombre_original  AS doc_nombre,
               d.tipo_mime        AS doc_mime,
               d.nombre_guardado  AS doc_guardado
        FROM artefacto_compartidos ac
        LEFT JOIN historial_documentos hd ON hd.id = ac.doc_id
        LEFT JOIN documentos d            ON d.id  = ac.documentos_id
        WHERE ac.token = $1 AND ac.expira_en > now()
        """,
        token,
    )
    if not fila:
        return None

    await conexion.execute(
        "UPDATE artefacto_compartidos SET usos = usos + 1 WHERE token = $1",
        token,
    )

    # Fuente: historial_documentos (MinIO)
    if fila["doc_id"]:
        contenido = await storage.descargar_fichero(fila["storage_key"])
        return {"contenido": contenido, "nombre_fichero": fila["nombre_fichero"], "tipo": fila["tipo"]}

    # Fuente: documentos (disco local)
    from app.modules.documentos.servicio import ruta_documento
    ruta = ruta_documento(str(fila["doc_guardado"]))
    contenido = ruta.read_bytes()
    tipo_mime = str(fila["doc_mime"] or "application/octet-stream")
    return {"contenido": contenido, "nombre_fichero": fila["doc_nombre"], "tipo": tipo_mime}


# =============================================================================
# Helpers internos
# =============================================================================

def _content_type(tipo: str) -> str:
    return {
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "investigacion": "application/json",
        "propuesta": "application/json",
        "briefing": "text/plain",
        "audio": "audio/mpeg",
    }.get(tipo, "application/octet-stream")
