"""
Lógica de negocio para gestión de usuarios.
"""

from uuid import UUID

from asyncpg import Connection

from app.auth.utils import hashear_contrasena
from app.modules.usuarios.schemas import PermisosUsuario, UsuarioCreate, UsuarioRead, UsuarioUpdate

# =============================================================================
# Helpers internos
# =============================================================================

def calcular_permisos(rol: str) -> PermisosUsuario:
    """Devuelve los permisos según el rol del usuario."""
    es_admin = rol == "admin"
    es_manager_o_admin = rol in ("admin", "manager", "supervisor")
    puede_importar = rol in ("admin", "manager", "supervisor", "comercial")
    return PermisosUsuario(
        ver_equipo=es_manager_o_admin,
        ver_todos_pipeline=es_manager_o_admin,
        gestionar_usuarios=es_admin,
        importar_datos=puede_importar,
        ver_informes_ejecutivos=es_manager_o_admin,
        gestionar_alertas=es_manager_o_admin,
    )


async def _sbus_del_usuario(conexion: Connection, usuario_id: UUID) -> list[str]:
    """Devuelve los códigos SBU asignados a un manager."""
    filas = await conexion.fetch(
        """
        SELECT s.codigo
        FROM manager_sbus ms
        JOIN sbu s ON s.id = ms.sbu_id
        WHERE ms.manager_id = $1
        ORDER BY s.codigo
        """,
        usuario_id,
    )
    return [f["codigo"] for f in filas]


async def _fila_a_usuario(conexion: Connection, fila) -> UsuarioRead:
    sbus = await _sbus_del_usuario(conexion, fila["id"])
    return UsuarioRead(
        id=fila["id"],
        email=fila["email"],
        nombre_completo=fila["nombre_completo"],
        rol=fila["rol"],
        nombre_csv=fila["nombre_csv"],
        manager_id=fila["manager_id"],
        activo=fila["activo"],
        creado_en=fila["creado_en"],
        sbus_asignados=sbus,
    )


# =============================================================================
# Consultas
# =============================================================================

async def listar_usuarios(
    conexion: Connection,
    *,
    rol: str | None = None,
    busqueda: str | None = None,
    pagina: int = 1,
    por_pagina: int = 50,
) -> dict:
    condiciones = ["u.eliminado_en IS NULL"]
    params: list = []

    if rol:
        params.append(rol)
        condiciones.append(f"u.rol = ${len(params)}")

    if busqueda:
        params.append(f"%{busqueda}%")
        condiciones.append(
            f"(u.nombre_completo ILIKE ${len(params)} OR u.email ILIKE ${len(params)})"
        )

    where = " AND ".join(condiciones)
    offset = (pagina - 1) * por_pagina

    params_count = list(params)
    total_fila = await conexion.fetchval(
        f"SELECT COUNT(*) FROM usuarios u WHERE {where}", *params_count
    )

    params.extend([por_pagina, offset])
    filas = await conexion.fetch(
        f"""
        SELECT u.id, u.email, u.nombre_completo, u.rol, u.nombre_csv,
               u.manager_id, u.activo, u.creado_en
        FROM usuarios u
        WHERE {where}
        ORDER BY u.nombre_completo
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """,
        *params,
    )

    usuarios = [await _fila_a_usuario(conexion, f) for f in filas]
    return {
        "total": total_fila,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "datos": usuarios,
    }


async def obtener_usuario(conexion: Connection, usuario_id: UUID) -> UsuarioRead | None:
    fila = await conexion.fetchrow(
        """
        SELECT id, email, nombre_completo, rol, nombre_csv, manager_id, activo, creado_en
        FROM usuarios
        WHERE id = $1 AND eliminado_en IS NULL
        """,
        usuario_id,
    )
    if not fila:
        return None
    return await _fila_a_usuario(conexion, fila)


# =============================================================================
# Mutaciones
# =============================================================================

async def crear_usuario(
    conexion: Connection, datos: UsuarioCreate, creado_por_id: str
) -> UsuarioRead:
    hash_pw = hashear_contrasena(datos.contrasena)

    fila = await conexion.fetchrow(
        """
        INSERT INTO usuarios (email, nombre_completo, hash_contrasena, rol, nombre_csv, manager_id)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, email, nombre_completo, rol, nombre_csv, manager_id, activo, creado_en
        """,
        datos.email,
        datos.nombre_completo,
        hash_pw,
        datos.rol,
        datos.nombre_csv,
        datos.manager_id,
    )

    # Asignar SBUs si es manager
    if datos.rol == "manager" and datos.sbus_ids:
        for sbu_id in datos.sbus_ids:
            await conexion.execute(
                "INSERT INTO manager_sbus (manager_id, sbu_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                fila["id"],
                sbu_id,
            )

    return await _fila_a_usuario(conexion, fila)


async def actualizar_usuario(
    conexion: Connection,
    usuario_id: UUID,
    datos: UsuarioUpdate,
    actualizado_por_id: str,
) -> UsuarioRead | None:
    fila_actual = await conexion.fetchrow(
        "SELECT id, email, nombre_completo, rol, nombre_csv, manager_id, activo, creado_en FROM usuarios WHERE id = $1 AND eliminado_en IS NULL",
        usuario_id,
    )
    if not fila_actual:
        return None

    campos: dict = {}
    if datos.nombre_completo is not None:
        campos["nombre_completo"] = datos.nombre_completo
    if datos.nombre_csv is not None:
        campos["nombre_csv"] = datos.nombre_csv
    if datos.manager_id is not None:
        campos["manager_id"] = datos.manager_id
    if datos.activo is not None:
        campos["activo"] = datos.activo

    # Cambio de rol — registrar en audit
    if datos.rol is not None and datos.rol != fila_actual["rol"]:
        campos["rol"] = datos.rol
        await conexion.execute(
            """
            INSERT INTO audit_role_changes (usuario_id, rol_anterior, rol_nuevo, cambiado_por_id, motivo)
            VALUES ($1, $2, $3, $4, $5)
            """,
            usuario_id,
            fila_actual["rol"],
            datos.rol,
            actualizado_por_id,
            datos.motivo_cambio_rol,
        )

    if campos:
        set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(campos))
        await conexion.execute(
            f"UPDATE usuarios SET {set_clause} WHERE id = $1",
            usuario_id,
            *campos.values(),
        )

    # Reemplazar SBUs si se especifican
    if datos.sbus_ids is not None:
        await conexion.execute("DELETE FROM manager_sbus WHERE manager_id = $1", usuario_id)
        for sbu_id in datos.sbus_ids:
            await conexion.execute(
                "INSERT INTO manager_sbus (manager_id, sbu_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                usuario_id,
                sbu_id,
            )

    return await obtener_usuario(conexion, usuario_id)


async def eliminar_usuario(conexion: Connection, usuario_id: UUID) -> bool:
    resultado = await conexion.execute(
        "UPDATE usuarios SET eliminado_en = NOW(), activo = FALSE WHERE id = $1 AND eliminado_en IS NULL",
        usuario_id,
    )
    return resultado != "UPDATE 0"
