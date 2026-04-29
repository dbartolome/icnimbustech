"""
Lógica de negocio del módulo de artefactos IA unificados.
"""

import json
from pathlib import Path
from uuid import UUID

import asyncpg

TIPOS_ENTIDAD_VALIDOS = {"cuenta", "cliente", "producto", "oportunidad", "comercial", "global"}


def _orden_seguro(sort_by: str, sort_dir: str) -> tuple[str, str]:
    campos = {
        "tipo": "a.tipo",
        "subtipo": "a.subtipo",
        "titulo": "a.titulo",
        "estado": "a.estado",
        "creado_en": "a.creado_en",
        "actualizado_en": "a.actualizado_en",
    }
    campo = campos.get(sort_by.lower(), "a.actualizado_en")
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    return campo, direccion


def _normalizar_entidad_tipo(entidad_tipo: str | None) -> str | None:
    valor = (entidad_tipo or "").strip().lower()
    return valor or None


def _json_a_dict(valor) -> dict:
    """
    Normaliza campos JSON que pueden venir legacy como texto serializado.
    """
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str):
        try:
            parsed = json.loads(valor)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


async def _auditar(
    conexion: asyncpg.Connection,
    artefacto_id: UUID,
    version_id: UUID | None,
    usuario_id: UUID | None,
    accion: str,
    detalle: dict | None = None,
) -> None:
    detalle_json = json.dumps(detalle or {}, ensure_ascii=False)
    await conexion.execute(
        """
        INSERT INTO ia_artefacto_auditoria
            (artefacto_id, version_id, usuario_id, accion, detalle)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        artefacto_id,
        version_id,
        usuario_id,
        accion,
        detalle_json,
    )


async def _obtener_artefacto_por_origen(
    conexion: asyncpg.Connection,
    origen_tabla: str | None,
    origen_id: str | None,
) -> dict | None:
    if not origen_tabla or not origen_id:
        return None
    fila = await conexion.fetchrow(
        """
        SELECT id, version_actual
        FROM ia_artefactos
        WHERE origen_tabla = $1 AND origen_id = $2 AND eliminado_en IS NULL
        """,
        origen_tabla,
        origen_id,
    )
    return dict(fila) if fila else None


async def _obtener_artefacto_por_clave_regeneracion(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    tipo: str,
    subtipo: str,
    clave_regeneracion: str | None,
) -> dict | None:
    if not clave_regeneracion:
        return None
    fila = await conexion.fetchrow(
        """
        SELECT id, version_actual
        FROM ia_artefactos
        WHERE usuario_id = $1
          AND tipo = $2
          AND subtipo = $3
          AND metadatos->>'clave_regeneracion' = $4
          AND eliminado_en IS NULL
        ORDER BY actualizado_en DESC
        LIMIT 1
        """,
        usuario_id,
        tipo,
        subtipo,
        clave_regeneracion,
    )
    return dict(fila) if fila else None


async def _insertar_fuentes_version(
    conexion: asyncpg.Connection,
    version_id: UUID,
    fuentes: list[dict] | None,
) -> None:
    if not fuentes:
        return
    for fuente in fuentes:
        await conexion.execute(
            """
            INSERT INTO ia_artefacto_fuentes
                (version_id, fuente_artefacto_id, fuente_tipo, fuente_ref, peso)
            VALUES ($1, $2, $3, $4, $5)
            """,
            version_id,
            fuente.get("fuente_artefacto_id"),
            fuente.get("fuente_tipo", "artefacto"),
            fuente.get("fuente_ref"),
            fuente.get("peso"),
        )


async def registrar_version_artefacto(
    conexion: asyncpg.Connection,
    *,
    tipo: str,
    subtipo: str,
    entidad_tipo: str | None,
    entidad_id: UUID | None,
    cuenta_id: UUID | None,
    usuario_id: UUID,
    titulo: str,
    prompt: str | None = None,
    resultado_texto: str | None = None,
    resultado_json: dict | None = None,
    storage_key: str | None = None,
    modelo: str | None = None,
    plantilla_id: UUID | None = None,
    metadatos: dict | None = None,
    fuentes: list[dict] | None = None,
    origen_tabla: str | None = None,
    origen_id: str | None = None,
) -> dict:
    # Normaliza trazabilidad de origen para evitar artefactos huérfanos sin entidad.
    tipo_entidad_normalizado = (entidad_tipo or "").strip().lower() or None
    if tipo_entidad_normalizado and tipo_entidad_normalizado not in TIPOS_ENTIDAD_VALIDOS:
        tipo_entidad_normalizado = "global"
    entidad_tipo_final = tipo_entidad_normalizado
    entidad_id_final = entidad_id

    if entidad_tipo_final in {"cuenta", "cliente"} and entidad_id_final is None and cuenta_id is not None:
        entidad_id_final = cuenta_id
    if entidad_tipo_final is None and cuenta_id is not None:
        entidad_tipo_final = "cuenta"
        entidad_id_final = cuenta_id
    if entidad_tipo_final is None:
        entidad_tipo_final = "global"

    meta = metadatos or {}
    if entidad_tipo_final:
        meta.setdefault("origen_entidad_tipo", entidad_tipo_final)
    if entidad_id_final:
        meta.setdefault("origen_entidad_id", str(entidad_id_final))
    elif cuenta_id:
        meta.setdefault("origen_entidad_id", str(cuenta_id))

    meta_json = json.dumps(meta, ensure_ascii=False)
    resultado_json_txt = json.dumps(resultado_json or {}, ensure_ascii=False)
    clave_regeneracion = meta.get("clave_regeneracion")
    artefacto = await _obtener_artefacto_por_origen(conexion, origen_tabla, origen_id)
    if not artefacto:
        artefacto = await _obtener_artefacto_por_clave_regeneracion(
            conexion,
            usuario_id=usuario_id,
            tipo=tipo,
            subtipo=subtipo,
            clave_regeneracion=clave_regeneracion,
        )

    if artefacto:
        artefacto_id = artefacto["id"]
        nueva_version = int(artefacto["version_actual"]) + 1
        await conexion.execute(
            "UPDATE ia_artefacto_versiones SET es_actual = FALSE WHERE artefacto_id = $1",
            artefacto_id,
        )
        fila_version = await conexion.fetchrow(
            """
            INSERT INTO ia_artefacto_versiones
                (artefacto_id, version_num, es_actual, prompt, resultado_texto, resultado_json,
                 storage_key, modelo, plantilla_id, metadatos)
            VALUES ($1, $2, TRUE, $3, $4, $5::jsonb, $6, $7, $8, $9::jsonb)
            RETURNING id
            """,
            artefacto_id,
            nueva_version,
            prompt,
            resultado_texto,
            resultado_json_txt,
            storage_key,
            modelo,
            plantilla_id,
            meta_json,
        )
        await conexion.execute(
            """
            UPDATE ia_artefactos
            SET version_actual = $2, titulo = $3, estado = 'activo',
                origen_tabla = COALESCE($4, origen_tabla),
                origen_id = COALESCE($5, origen_id),
                metadatos = metadatos || $6::jsonb,
                actualizado_en = now()
            WHERE id = $1
            """,
            artefacto_id,
            nueva_version,
            titulo,
            origen_tabla,
            origen_id,
            meta_json,
        )
        await _insertar_fuentes_version(conexion, fila_version["id"], fuentes)
        await _auditar(
            conexion,
            artefacto_id=artefacto_id,
            version_id=fila_version["id"],
            usuario_id=usuario_id,
            accion="versionar",
            detalle={"version_num": nueva_version},
        )
    else:
        fila_art = await conexion.fetchrow(
            """
            INSERT INTO ia_artefactos
                (tipo, subtipo, entidad_tipo, entidad_id, cuenta_id, usuario_id, titulo,
                 origen_tabla, origen_id, metadatos)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
            RETURNING id
            """,
            tipo,
            subtipo,
            entidad_tipo_final,
            entidad_id_final,
            cuenta_id,
            usuario_id,
            titulo,
            origen_tabla,
            origen_id,
            meta_json,
        )
        artefacto_id = fila_art["id"]
        fila_version = await conexion.fetchrow(
            """
            INSERT INTO ia_artefacto_versiones
                (artefacto_id, version_num, es_actual, prompt, resultado_texto, resultado_json,
                 storage_key, modelo, plantilla_id, metadatos)
            VALUES ($1, 1, TRUE, $2, $3, $4::jsonb, $5, $6, $7, $8::jsonb)
            RETURNING id
            """,
            artefacto_id,
            prompt,
            resultado_texto,
            resultado_json_txt,
            storage_key,
            modelo,
            plantilla_id,
            meta_json,
        )
        await _insertar_fuentes_version(conexion, fila_version["id"], fuentes)
        await _auditar(
            conexion,
            artefacto_id=artefacto_id,
            version_id=fila_version["id"],
            usuario_id=usuario_id,
            accion="crear",
            detalle={"version_num": 1},
        )

    fila = await conexion.fetchrow(
        """
        SELECT id, tipo, subtipo, entidad_tipo, entidad_id, cuenta_id, usuario_id, titulo,
               estado, version_actual, metadatos,
               creado_en::TEXT AS creado_en,
               actualizado_en::TEXT AS actualizado_en,
               eliminado_en::TEXT AS eliminado_en
        FROM ia_artefactos
        WHERE id = $1
        """,
        artefacto_id,
    )
    return dict(fila)


async def listar_artefactos(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    es_admin: bool,
    tipo: str | None = None,
    subtipo: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: UUID | None = None,
    cuenta_id: UUID | None = None,
    texto: str | None = None,
    propietario_id: UUID | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
    sort_by: str = "actualizado_en",
    sort_dir: str = "desc",
) -> dict:
    condiciones = ["a.eliminado_en IS NULL"]
    args: list = []
    entidad_tipo_norm = _normalizar_entidad_tipo(entidad_tipo)

    if not es_admin:
        args.append(usuario_id)
        condiciones.append(f"a.usuario_id = ${len(args)}")
    elif propietario_id:
        args.append(propietario_id)
        condiciones.append(f"a.usuario_id = ${len(args)}")

    if tipo:
        args.append(tipo)
        condiciones.append(f"a.tipo = ${len(args)}")
    if subtipo:
        args.append(subtipo)
        condiciones.append(f"a.subtipo = ${len(args)}")
    if entidad_tipo_norm and entidad_id and entidad_tipo_norm in {"cuenta", "cliente"}:
        args.append(entidad_tipo_norm)
        idx_tipo = len(args)
        args.append(entidad_id)
        idx_id = len(args)
        # Compatibilidad con datos legacy: algunos artefactos solo tienen cuenta_id.
        condiciones.append(
            f"((a.entidad_tipo = ${idx_tipo} AND a.entidad_id = ${idx_id}) OR a.cuenta_id = ${idx_id})"
        )
    else:
        if entidad_tipo_norm:
            args.append(entidad_tipo_norm)
            condiciones.append(f"a.entidad_tipo = ${len(args)}")
        if entidad_id:
            args.append(entidad_id)
            condiciones.append(f"a.entidad_id = ${len(args)}")
    if cuenta_id:
        args.append(cuenta_id)
        condiciones.append(f"a.cuenta_id = ${len(args)}")
    if texto:
        args.append(f"%{texto}%")
        condiciones.append(f"(a.titulo ILIKE ${len(args)} OR a.subtipo ILIKE ${len(args)})")

    where = "WHERE " + " AND ".join(condiciones)
    campo, direccion = _orden_seguro(sort_by, sort_dir)
    offset = (pagina - 1) * por_pagina

    total = await conexion.fetchval(f"SELECT COUNT(*) FROM ia_artefactos a {where}", *args)

    filas = await conexion.fetch(
        f"""
        SELECT
            a.id, a.tipo, a.subtipo, a.entidad_tipo, a.entidad_id, a.cuenta_id, a.usuario_id,
            a.titulo, a.estado, a.version_actual, a.origen_tabla, a.origen_id, a.metadatos,
            a.creado_en::TEXT AS creado_en,
            a.actualizado_en::TEXT AS actualizado_en,
            a.eliminado_en::TEXT AS eliminado_en
        FROM ia_artefactos a
        {where}
        ORDER BY {campo} {direccion} NULLS LAST, a.id DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        por_pagina,
        offset,
    )
    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": [dict(f) for f in filas],
    }


def _key_origen_desde_fila(fila: dict) -> tuple[str, str, str]:
    entidad_tipo = str(fila.get("entidad_tipo") or "").strip().lower()
    entidad_id = str(fila.get("entidad_id") or "").strip()
    if entidad_tipo and entidad_tipo != "global" and entidad_id:
        return entidad_tipo, entidad_id, f"{entidad_tipo}:{entidad_id}"

    origen_tabla = str(fila.get("origen_tabla") or "").strip().lower()
    origen_id = str(fila.get("origen_id") or "").strip()
    if origen_tabla and origen_id:
        return origen_tabla, origen_id, f"{origen_tabla}:{origen_id}"

    return "sin_origen", "", "sin_origen"


def _nombre_origen_desde_fila(fila: dict) -> str:
    nombre = str(fila.get("entidad_nombre") or "").strip()
    if nombre:
        return nombre
    titulo = str(fila.get("titulo") or "").strip()
    return titulo or "Sin origen"


async def listar_repositorio_agrupado(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    es_admin: bool,
    tipo: str | None = None,
    subtipo: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: UUID | None = None,
    cuenta_id: UUID | None = None,
    q: str | None = None,
    propietario_id: UUID | None = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> dict:
    condiciones = ["a.eliminado_en IS NULL"]
    args: list = []
    entidad_tipo_norm = _normalizar_entidad_tipo(entidad_tipo)

    if not es_admin:
        args.append(usuario_id)
        condiciones.append(f"a.usuario_id = ${len(args)}")
    elif propietario_id:
        args.append(propietario_id)
        condiciones.append(f"a.usuario_id = ${len(args)}")
    if tipo:
        args.append(tipo)
        condiciones.append(f"a.tipo = ${len(args)}")
    if subtipo:
        args.append(subtipo)
        condiciones.append(f"a.subtipo = ${len(args)}")
    if entidad_tipo_norm and entidad_id and entidad_tipo_norm in {"cuenta", "cliente"}:
        args.append(entidad_tipo_norm)
        idx_tipo = len(args)
        args.append(entidad_id)
        idx_id = len(args)
        condiciones.append(
            f"((a.entidad_tipo = ${idx_tipo} AND a.entidad_id = ${idx_id}) OR a.cuenta_id = ${idx_id})"
        )
    else:
        if entidad_tipo_norm:
            args.append(entidad_tipo_norm)
            condiciones.append(f"a.entidad_tipo = ${len(args)}")
        if entidad_id:
            args.append(entidad_id)
            condiciones.append(f"a.entidad_id = ${len(args)}")
    if cuenta_id:
        args.append(cuenta_id)
        condiciones.append(f"a.cuenta_id = ${len(args)}")
    if q:
        args.append(f"%{q}%")
        condiciones.append(f"(a.titulo ILIKE ${len(args)} OR a.subtipo ILIKE ${len(args)})")

    where = "WHERE " + " AND ".join(condiciones)
    offset = (pagina - 1) * por_pagina

    total_items = await conexion.fetchval(f"SELECT COUNT(*) FROM ia_artefactos a {where}", *args)
    filas = await conexion.fetch(
        f"""
        SELECT
            a.id::TEXT AS id,
            a.tipo,
            a.subtipo,
            a.titulo,
            a.estado,
            a.version_actual,
            a.entidad_tipo,
            a.entidad_id::TEXT AS entidad_id,
            a.cuenta_id::TEXT AS cuenta_id,
            a.origen_tabla,
            a.origen_id,
            a.creado_en::TEXT AS creado_en,
            a.actualizado_en::TEXT AS actualizado_en,
            COALESCE(v.resultado_texto, '') AS preview_texto,
            COALESCE(v.storage_key, '') AS storage_key,
            COALESCE(c.nombre, cl.nombre, p.nombre, o.nombre, u.nombre_completo, '') AS entidad_nombre
        FROM ia_artefactos a
        LEFT JOIN ia_artefacto_versiones v
            ON v.artefacto_id = a.id AND v.es_actual = TRUE
        LEFT JOIN cuentas c
            ON a.entidad_tipo = 'cuenta' AND c.id = a.entidad_id
        LEFT JOIN cuentas cl
            ON a.entidad_tipo = 'cliente' AND cl.id = a.entidad_id
        LEFT JOIN productos p
            ON a.entidad_tipo = 'producto' AND p.id = a.entidad_id
        LEFT JOIN oportunidades o
            ON a.entidad_tipo = 'oportunidad' AND o.id = a.entidad_id
        LEFT JOIN usuarios u
            ON a.entidad_tipo = 'comercial' AND u.id = a.entidad_id
        {where}
        ORDER BY a.actualizado_en DESC, a.id DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args,
        por_pagina,
        offset,
    )

    grupos_idx: dict[str, dict] = {}
    orden_grupos: list[str] = []

    for fila_raw in filas:
        fila = dict(fila_raw)
        origen_tipo, origen_id_txt, origen_key = _key_origen_desde_fila(fila)
        if origen_key not in grupos_idx:
            grupos_idx[origen_key] = {
                "origen_tipo": origen_tipo,
                "origen_id": origen_id_txt or None,
                "origen_key": origen_key,
                "origen_nombre": _nombre_origen_desde_fila(fila),
                "actualizado_en": fila["actualizado_en"],
                "total": 0,
                "items": [],
            }
            orden_grupos.append(origen_key)

        grupo = grupos_idx[origen_key]
        grupo["total"] += 1
        if fila["actualizado_en"] > grupo["actualizado_en"]:
            grupo["actualizado_en"] = fila["actualizado_en"]

        grupo["items"].append(
            {
                "id": fila["id"],
                "tipo": fila["tipo"],
                "subtipo": fila["subtipo"],
                "titulo": fila["titulo"],
                "estado": fila["estado"],
                "version_actual": fila["version_actual"],
                "creado_en": fila["creado_en"],
                "actualizado_en": fila["actualizado_en"],
                "preview_texto": fila["preview_texto"][:500],
                "storage_key": fila["storage_key"] or None,
                "entidad_tipo": fila.get("entidad_tipo"),
                "entidad_id": fila.get("entidad_id"),
                "cuenta_id": fila.get("cuenta_id"),
                "origen_tabla": fila.get("origen_tabla"),
                "origen_id": fila.get("origen_id"),
            }
        )

    grupos = [grupos_idx[key] for key in orden_grupos]
    return {
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_items": total_items,
        "total_grupos": len(grupos),
        "datos": grupos,
    }


async def obtener_artefacto(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> dict | None:
    condicion_usuario = "" if es_admin else "AND a.usuario_id = $2"
    args = [artefacto_id] if es_admin else [artefacto_id, usuario_id]

    artefacto = await conexion.fetchrow(
        f"""
        SELECT
            a.id, a.tipo, a.subtipo, a.entidad_tipo, a.entidad_id, a.cuenta_id, a.usuario_id,
            a.titulo, a.estado, a.version_actual, a.origen_tabla, a.origen_id, a.metadatos,
            a.creado_en::TEXT AS creado_en,
            a.actualizado_en::TEXT AS actualizado_en,
            a.eliminado_en::TEXT AS eliminado_en
        FROM ia_artefactos a
        WHERE a.id = $1 AND a.eliminado_en IS NULL {condicion_usuario}
        """,
        *args,
    )
    if not artefacto:
        return None

    version = await conexion.fetchrow(
        """
        SELECT
            id, artefacto_id, version_num, es_actual, prompt, resultado_texto,
            resultado_json, storage_key, modelo, plantilla_id, metadatos,
            creado_en::TEXT AS creado_en
        FROM ia_artefacto_versiones
        WHERE artefacto_id = $1 AND es_actual = TRUE
        LIMIT 1
        """,
        artefacto_id,
    )
    total_versiones = await conexion.fetchval(
        "SELECT COUNT(*) FROM ia_artefacto_versiones WHERE artefacto_id = $1",
        artefacto_id,
    )
    artefacto_dict = dict(artefacto)
    artefacto_dict["metadatos"] = _json_a_dict(artefacto_dict.get("metadatos"))

    version_dict = dict(version) if version else None
    if version_dict is not None:
        version_dict["resultado_json"] = _json_a_dict(version_dict.get("resultado_json"))
        version_dict["metadatos"] = _json_a_dict(version_dict.get("metadatos"))

    return {
        "artefacto": artefacto_dict,
        "version_actual": version_dict,
        "total_versiones": total_versiones or 0,
    }


async def listar_versiones(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> list[dict]:
    permitido = await conexion.fetchval(
        "SELECT 1 FROM ia_artefactos WHERE id = $1 AND eliminado_en IS NULL " + ("" if es_admin else "AND usuario_id = $2"),
        artefacto_id,
        *( [] if es_admin else [usuario_id] ),
    )
    if not permitido:
        return []

    filas = await conexion.fetch(
        """
        SELECT
            id, artefacto_id, version_num, es_actual, prompt, resultado_texto,
            resultado_json, storage_key, modelo, plantilla_id, metadatos,
            creado_en::TEXT AS creado_en
        FROM ia_artefacto_versiones
        WHERE artefacto_id = $1
        ORDER BY version_num DESC
        """,
        artefacto_id,
    )
    out: list[dict] = []
    for fila in filas:
        item = dict(fila)
        item["resultado_json"] = _json_a_dict(item.get("resultado_json"))
        item["metadatos"] = _json_a_dict(item.get("metadatos"))
        out.append(item)
    return out


async def crear_version_manual(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
    payload: dict,
) -> dict | None:
    condicion_usuario = "" if es_admin else "AND usuario_id = $2"
    args = [artefacto_id] if es_admin else [artefacto_id, usuario_id]
    artefacto = await conexion.fetchrow(
        f"""
        SELECT id, version_actual, tipo, subtipo, entidad_tipo, entidad_id, cuenta_id, titulo, metadatos
        FROM ia_artefactos
        WHERE id = $1 AND eliminado_en IS NULL {condicion_usuario}
        """,
        *args,
    )
    if not artefacto:
        return None

    nueva_version = int(artefacto["version_actual"]) + 1
    await conexion.execute(
        "UPDATE ia_artefacto_versiones SET es_actual = FALSE WHERE artefacto_id = $1",
        artefacto_id,
    )
    fila_version = await conexion.fetchrow(
        """
        INSERT INTO ia_artefacto_versiones
            (artefacto_id, version_num, es_actual, prompt, resultado_texto, resultado_json,
             storage_key, modelo, plantilla_id, metadatos)
        VALUES ($1, $2, TRUE, $3, $4, $5::jsonb, $6, $7, $8, $9::jsonb)
        RETURNING id
        """,
        artefacto_id,
        nueva_version,
        payload.get("prompt"),
        payload.get("resultado_texto"),
        json.dumps(payload.get("resultado_json") or {}, ensure_ascii=False),
        payload.get("storage_key"),
        payload.get("modelo"),
        payload.get("plantilla_id"),
        json.dumps(payload.get("metadatos") or {}, ensure_ascii=False),
    )
    await _insertar_fuentes_version(conexion, fila_version["id"], payload.get("fuentes") or [])
    await conexion.execute(
        "UPDATE ia_artefactos SET version_actual = $2, actualizado_en = now() WHERE id = $1",
        artefacto_id,
        nueva_version,
    )
    await _auditar(
        conexion,
        artefacto_id=artefacto_id,
        version_id=fila_version["id"],
        usuario_id=usuario_id,
        accion="versionar",
        detalle={"version_num": nueva_version, "manual": True},
    )
    return await obtener_artefacto(
        conexion,
        artefacto_id=artefacto_id,
        usuario_id=usuario_id,
        es_admin=es_admin,
    )


async def marcar_version_actual(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    version_num: int,
    usuario_id: UUID,
    es_admin: bool,
) -> bool:
    condicion_usuario = "" if es_admin else "AND usuario_id = $3"
    args = [artefacto_id, version_num] if es_admin else [artefacto_id, version_num, usuario_id]
    existe = await conexion.fetchval(
        f"""
        SELECT 1
        FROM ia_artefactos a
        JOIN ia_artefacto_versiones v ON v.artefacto_id = a.id
        WHERE a.id = $1 AND v.version_num = $2 AND a.eliminado_en IS NULL {condicion_usuario}
        """,
        *args,
    )
    if not existe:
        return False

    await conexion.execute(
        "UPDATE ia_artefacto_versiones SET es_actual = FALSE WHERE artefacto_id = $1",
        artefacto_id,
    )
    fila = await conexion.fetchrow(
        """
        UPDATE ia_artefacto_versiones
        SET es_actual = TRUE
        WHERE artefacto_id = $1 AND version_num = $2
        RETURNING id
        """,
        artefacto_id,
        version_num,
    )
    await conexion.execute(
        "UPDATE ia_artefactos SET version_actual = $2, actualizado_en = now() WHERE id = $1",
        artefacto_id,
        version_num,
    )
    await _auditar(
        conexion,
        artefacto_id=artefacto_id,
        version_id=fila["id"] if fila else None,
        usuario_id=usuario_id,
        accion="marcar_actual",
        detalle={"version_num": version_num},
    )
    return True


async def eliminar_artefacto(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> bool:
    condicion_usuario = "" if es_admin else "AND usuario_id = $2"
    args = [artefacto_id] if es_admin else [artefacto_id, usuario_id]
    res = await conexion.execute(
        f"""
        UPDATE ia_artefactos
        SET eliminado_en = now(), estado = 'eliminado'
        WHERE id = $1 AND eliminado_en IS NULL {condicion_usuario}
        """,
        *args,
    )
    ok = res == "UPDATE 1"
    if ok:
        await _auditar(
            conexion,
            artefacto_id=artefacto_id,
            version_id=None,
            usuario_id=usuario_id,
            accion="eliminar",
            detalle={},
        )
    return ok


async def obtener_contexto_relevante(
    conexion: asyncpg.Connection,
    *,
    usuario_id: UUID,
    es_admin: bool,
    entidad_tipo: str | None = None,
    entidad_id: UUID | None = None,
    cuenta_id: UUID | None = None,
    limit: int = 12,
) -> list[dict]:
    condiciones = ["a.eliminado_en IS NULL"]
    args: list = []
    if not es_admin:
        args.append(usuario_id)
        condiciones.append(f"a.usuario_id = ${len(args)}")
    if entidad_tipo:
        args.append(entidad_tipo)
        condiciones.append(f"a.entidad_tipo = ${len(args)}")
    if entidad_id:
        args.append(entidad_id)
        condiciones.append(f"a.entidad_id = ${len(args)}")
    if cuenta_id:
        args.append(cuenta_id)
        condiciones.append(f"a.cuenta_id = ${len(args)}")
    where = "WHERE " + " AND ".join(condiciones)

    filas = await conexion.fetch(
        f"""
        SELECT
            a.id, a.tipo, a.subtipo, a.titulo, a.entidad_tipo, a.entidad_id, a.cuenta_id,
            a.actualizado_en::TEXT AS actualizado_en,
            v.version_num, v.resultado_texto,
            v.resultado_json
        FROM ia_artefactos a
        LEFT JOIN ia_artefacto_versiones v
            ON v.artefacto_id = a.id AND v.es_actual = TRUE
        {where}
        ORDER BY a.actualizado_en DESC
        LIMIT ${len(args) + 1}
        """,
        *args,
        limit,
    )
    return [dict(f) for f in filas]


def _mime_por_subtipo(subtipo: str | None) -> str:
    valor = (subtipo or "").strip().lower()
    if valor in {"pdf", "informe"}:
        return "application/pdf"
    if valor in {"pptx", "deck"}:
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    if valor in {"audio", "briefing"}:
        return "audio/mpeg"
    if valor in {"chat", "transcripcion"}:
        return "text/plain; charset=utf-8"
    if valor in {"investigacion", "propuesta"}:
        return "application/json"
    return "application/octet-stream"


async def obtener_blob_artefacto(
    conexion: asyncpg.Connection,
    *,
    artefacto_id: UUID,
    usuario_id: UUID,
    es_admin: bool,
) -> tuple[bytes, str, str]:
    detalle = await obtener_artefacto(
        conexion,
        artefacto_id=artefacto_id,
        usuario_id=usuario_id,
        es_admin=es_admin,
    )
    if not detalle:
        raise ValueError("artefacto_no_encontrado")

    artefacto = detalle.get("artefacto") or {}
    version = detalle.get("version_actual") or {}
    origen_tabla = str(artefacto.get("origen_tabla") or "").strip().lower()
    origen_id = str(artefacto.get("origen_id") or "").strip()
    subtipo = str(artefacto.get("subtipo") or artefacto.get("tipo") or "artefacto")
    titulo = str(artefacto.get("titulo") or f"artefacto.{subtipo}")

    if origen_tabla == "historial_documentos" and origen_id:
        condicion_usuario = "" if es_admin else "AND usuario_id = $2"
        args = [UUID(origen_id)] if es_admin else [UUID(origen_id), usuario_id]
        fila_doc = await conexion.fetchrow(
            f"SELECT storage_key, tipo, nombre_fichero FROM historial_documentos WHERE id = $1 {condicion_usuario}",
            *args,
        )
        if not fila_doc:
            raise ValueError("origen_no_encontrado")
        from app import storage

        contenido = await storage.descargar_fichero(fila_doc["storage_key"])
        tipo = str(fila_doc["tipo"] or subtipo)
        nombre = str(fila_doc["nombre_fichero"] or titulo)
        return contenido, _mime_por_subtipo(tipo), nombre

    if origen_tabla == "informes_generados" and origen_id:
        condicion_usuario = "" if es_admin else "AND usuario_id = $2"
        args = [UUID(origen_id)] if es_admin else [UUID(origen_id), usuario_id]
        fila_inf = await conexion.fetchrow(
            f"SELECT ruta_pdf, titulo FROM informes_generados WHERE id = $1 {condicion_usuario}",
            *args,
        )
        if not fila_inf or not fila_inf["ruta_pdf"]:
            raise ValueError("origen_no_encontrado")
        ruta = Path(fila_inf["ruta_pdf"])
        if not ruta.exists():
            raise ValueError("archivo_no_encontrado")
        contenido = ruta.read_bytes()
        nombre = f"{str(fila_inf['titulo'] or titulo).strip() or 'informe'}.pdf"
        return contenido, "application/pdf", nombre

    storage_key = str(version.get("storage_key") or "").strip()
    if storage_key:
        ruta = Path(storage_key)
        if ruta.exists():
            mime = _mime_por_subtipo(subtipo)
            if ruta.suffix.lower() == ".pdf":
                mime = "application/pdf"
            elif ruta.suffix.lower() == ".pptx":
                mime = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif ruta.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}:
                mime = "audio/mpeg"
            return ruta.read_bytes(), mime, ruta.name
        try:
            from app import storage

            contenido = await storage.descargar_fichero(storage_key)
            return contenido, _mime_por_subtipo(subtipo), titulo
        except Exception:
            pass

    if version.get("resultado_texto"):
        return str(version["resultado_texto"]).encode("utf-8"), "text/plain; charset=utf-8", f"{titulo}.txt"

    if version.get("resultado_json"):
        payload = json.dumps(version["resultado_json"], ensure_ascii=False, indent=2)
        return payload.encode("utf-8"), "application/json", f"{titulo}.json"

    raise ValueError("sin_contenido_previsualizable")
