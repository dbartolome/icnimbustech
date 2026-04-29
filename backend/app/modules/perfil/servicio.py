"""
Lógica de negocio del módulo Mi Perfil.
Gestiona perfil personal, objetivos y configuración de notificaciones.
"""

import csv
import io
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.modules.perfil.schemas import (
    ObjetivoCreate,
    ObjetivoRead,
    ObjetivoUpdate,
    NotificacionesConfig,
    NotificacionesUpdate,
    PerfilRead,
    PerfilStats,
    PerfilUpdate,
)

# ── Etapas cerradas (excluidas del pipeline activo) ───────────────────────────

ETAPAS_CERRADAS = ("closed_won", "closed_lost", "closed_withdrawn")

ETAPA_EXPORT_CSV: dict[str, str] = {
    "estimation_sent": "Estimation Sent to Client",
    "technically_approved": "Technically Approved",
    "in_progress": "In Progress",
    "discover": "Discover",
    "contract_offer_sent": "Contract Offer Sent",
    "propose": "Propose",
    "estimation_accepted": "Estimation Accepted",
    "negotiate": "Negotiate",
    "closed_won": "Closed Won",
    "closed_lost": "Closed Lost",
    "closed_withdrawn": "Closed Withdrawn",
}


def _formatear_fecha_csv(valor) -> str:
    if not valor:
        return ""
    if hasattr(valor, "strftime"):
        return valor.strftime("%Y-%m-%d")
    return str(valor)


def _formatear_importe_csv(valor) -> str:
    if valor is None:
        return "0.00"
    try:
        return f"{Decimal(valor):.2f}"
    except Exception:
        return "0.00"


def _etapa_para_export(valor: str | None) -> str:
    if not valor:
        return "Discover"
    return ETAPA_EXPORT_CSV.get(valor, valor.replace("_", " ").title())


async def resetear_cuenta(usuario_id: UUID, conexion: asyncpg.Connection) -> dict:
    """
    Elimina todos los datos de negocio del usuario y limpia cuentas huérfanas.
    Mantiene el usuario, credenciales y configuración personal intactos.
    """
    tablas_usuario = [
        "oportunidades",
        "seguimientos",
        "notas_voz",
        "sesiones_audio",
        "conversaciones_ia",
        "informes_generados",
        "historial_documentos",
        "estudios_ia_cuentas",
        "ia_artefactos",
        "ia_artefacto_auditoria",
        "forecast_snapshots",
        "comercial_objetivos",
        "objetivos_comerciales",
        "validaciones_calidad",
        "coaching_sesiones",
        "importaciones",
        "alertas",
    ]

    eliminados: dict[str, int] = {}
    for tabla in tablas_usuario:
        try:
            resultado = await conexion.execute(
                f"DELETE FROM {tabla} WHERE usuario_id = $1", usuario_id
            )
            n = int(resultado.split()[-1]) if resultado else 0
            if n > 0:
                eliminados[tabla] = n
        except Exception:
            pass

    # oportunidades usa propietario_id
    try:
        resultado = await conexion.execute(
            "DELETE FROM oportunidades WHERE propietario_id = $1", usuario_id
        )
        n = int(resultado.split()[-1]) if resultado else 0
        if n > 0:
            eliminados["oportunidades"] = eliminados.get("oportunidades", 0) + n
    except Exception:
        pass

    # Limpiar cuentas huérfanas (sin oportunidades)
    resultado_cuentas = await conexion.execute(
        """
        DELETE FROM cuentas
        WHERE id NOT IN (SELECT DISTINCT cuenta_id FROM oportunidades WHERE cuenta_id IS NOT NULL)
          AND eliminado_en IS NULL
        """
    )
    cuentas_eliminadas = int(resultado_cuentas.split()[-1]) if resultado_cuentas else 0
    if cuentas_eliminadas > 0:
        eliminados["cuentas_huerfanas"] = cuentas_eliminadas

    return {"eliminados": eliminados, "total_tablas": len(eliminados)}


def _es_error_esquema(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            asyncpg.exceptions.UndefinedTableError,
            asyncpg.exceptions.UndefinedColumnError,
        ),
    )


# ── Perfil ────────────────────────────────────────────────────────────────────

async def obtener_perfil(usuario_id: UUID, conexion: asyncpg.Connection) -> PerfilRead:
    """Obtiene el perfil completo del usuario (datos base + perfil extendido)."""
    try:
        fila = await conexion.fetchrow(
            """
            SELECT
                u.id        AS usuario_id,
                u.email,
                u.nombre_completo,
                u.rol,
                u.manager_id,
                p.telefono,
                p.zona,
                p.sbu_principal,
                p.avatar_url
            FROM usuarios u
            LEFT JOIN comercial_perfil p ON p.usuario_id = u.id
            WHERE u.id = $1 AND u.activo = TRUE AND u.eliminado_en IS NULL
            """,
            usuario_id,
        )
    except Exception as exc:
        if not _es_error_esquema(exc):
            raise
        # Fallback para entornos sin tabla extendida de perfil.
        fila = await conexion.fetchrow(
            """
            SELECT
                u.id        AS usuario_id,
                u.email,
                u.nombre_completo,
                u.rol,
                u.manager_id,
                NULL::TEXT  AS telefono,
                NULL::TEXT  AS zona,
                NULL::TEXT  AS sbu_principal,
                NULL::TEXT  AS avatar_url
            FROM usuarios u
            WHERE u.id = $1 AND u.activo = TRUE AND u.eliminado_en IS NULL
            """,
            usuario_id,
        )
    if not fila:
        raise ValueError("Usuario no encontrado")
    return PerfilRead(**dict(fila))


async def actualizar_perfil(
    usuario_id: UUID,
    datos: PerfilUpdate,
    conexion: asyncpg.Connection,
) -> PerfilRead:
    """Actualiza nombre_completo en usuarios y el resto en comercial_perfil (upsert)."""
    async with conexion.transaction():
        if datos.nombre_completo is not None:
            await conexion.execute(
                "UPDATE usuarios SET nombre_completo = $1, actualizado_en = NOW() WHERE id = $2",
                datos.nombre_completo,
                usuario_id,
            )

        # Upsert en comercial_perfil
        try:
            perfil_existente = await conexion.fetchval(
                "SELECT id FROM comercial_perfil WHERE usuario_id = $1", usuario_id
            )
        except Exception as exc:
            if not _es_error_esquema(exc):
                raise
            perfil_existente = None

        if perfil_existente:
            campos = []
            valores = []
            idx = 1
            for campo in ("telefono", "zona", "sbu_principal", "avatar_url"):
                valor = getattr(datos, campo)
                if valor is not None:
                    campos.append(f"{campo} = ${idx}")
                    valores.append(valor)
                    idx += 1
            if campos:
                valores.append(usuario_id)
                try:
                    await conexion.execute(
                        f"UPDATE comercial_perfil SET {', '.join(campos)}, actualizado_en = NOW() WHERE usuario_id = ${idx}",
                        *valores,
                    )
                except Exception as exc:
                    if not _es_error_esquema(exc):
                        raise
        else:
            sbu = datos.sbu_principal.value if datos.sbu_principal else None
            try:
                await conexion.execute(
                    """
                    INSERT INTO comercial_perfil (usuario_id, telefono, zona, sbu_principal, avatar_url)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    usuario_id,
                    datos.telefono,
                    datos.zona,
                    sbu,
                    datos.avatar_url,
                )
            except Exception as exc:
                if not _es_error_esquema(exc):
                    raise

    return await obtener_perfil(usuario_id, conexion)


async def exportar_csv_perfil(usuario_id: UUID, conexion: asyncpg.Connection) -> tuple[bytes, str]:
    """Genera un CSV reimportable con todas las oportunidades del comercial."""
    usuario = await conexion.fetchrow(
        """
        SELECT nombre_completo, email
        FROM usuarios
        WHERE id = $1 AND activo = TRUE AND eliminado_en IS NULL
        """,
        usuario_id,
    )
    if not usuario:
        raise ValueError("Usuario no encontrado")

    filas = await conexion.fetch(
        """
        SELECT
            o.id,
            o.external_id,
            o.nombre AS oportunidad_nombre,
            o.importe,
            o.fecha_creacion,
            o.fecha_decision,
            o.etapa,
            o.tipo,
            o.linea_negocio,
            o.canal_venta,
            c.nombre AS cuenta_nombre,
            s.nombre AS sbu_nombre,
            p.nombre AS producto_nombre
        FROM oportunidades o
        LEFT JOIN cuentas c ON c.id = o.cuenta_id
        LEFT JOIN sbu s ON s.id = o.sbu_id
        LEFT JOIN productos p ON p.id = o.producto_id
        WHERE o.propietario_id = $1
          AND o.eliminado_en IS NULL
        ORDER BY o.fecha_creacion DESC NULLS LAST, o.creado_en DESC
        """,
        usuario_id,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "Opportunity Name",
            "Strategic Business Unit",
            "Business Line",
            "Product Name",
            "Short Description",
            "Account Name",
            "Canal de Venta",
            "Opportunity Owner",
            "Amount",
            "Created Date",
            "Stage",
            "Decision Date",
            "Type",
            "Opportunity ID",
        ]
    )

    owner = str(usuario["nombre_completo"] or "").strip()
    for fila in filas:
        opportunity_id = (str(fila["external_id"] or "").strip() or f"MVP-{fila['id']}")
        writer.writerow(
            [
                str(fila["oportunidad_nombre"] or "").strip() or "Oportunidad sin nombre",
                str(fila["sbu_nombre"] or "").strip(),
                str(fila["linea_negocio"] or "").strip(),
                str(fila["producto_nombre"] or "").strip(),
                "",
                str(fila["cuenta_nombre"] or "").strip() or "Cuenta sin nombre",
                str(fila["canal_venta"] or "").strip(),
                owner,
                _formatear_importe_csv(fila["importe"]),
                _formatear_fecha_csv(fila["fecha_creacion"]),
                _etapa_para_export(fila["etapa"]),
                _formatear_fecha_csv(fila["fecha_decision"]),
                str(fila["tipo"] or "").strip() or "New Business",
                opportunity_id,
            ]
        )

    contenido = buffer.getvalue().encode("utf-8-sig")
    email = str(usuario["email"] or "usuario").split("@")[0].replace(" ", "_")
    nombre_fichero = f"export_perfil_{email}.csv"
    return contenido, nombre_fichero


async def obtener_stats(usuario_id: UUID, conexion: asyncpg.Connection) -> PerfilStats:
    """Calcula KPIs del comercial haciendo JOIN con la tabla oportunidades."""
    fila = await conexion.fetchrow(
        """
        SELECT
            COALESCE(SUM(CASE WHEN etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')
                              THEN importe ELSE 0 END), 0)  AS pipeline_activo,
            COUNT(*) FILTER (WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn'))
                                                             AS oportunidades_abiertas,
            COUNT(*) FILTER (WHERE etapa = 'closed_won')    AS oportunidades_ganadas,
            COUNT(*) FILTER (WHERE etapa = 'closed_lost')   AS oportunidades_perdidas,
            CASE
                WHEN COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) = 0 THEN 0
                ELSE ROUND(
                    COUNT(*) FILTER (WHERE etapa = 'closed_won')::DECIMAL * 100 /
                    COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')),
                    1
                )
            END                                              AS win_rate,
            CASE
                WHEN COUNT(*) FILTER (WHERE etapa = 'closed_won') = 0 THEN 0
                ELSE ROUND(
                    SUM(CASE WHEN etapa = 'closed_won' THEN importe ELSE 0 END) /
                    COUNT(*) FILTER (WHERE etapa = 'closed_won'),
                    0
                )
            END                                              AS ticket_medio
        FROM oportunidades
        WHERE propietario_id = $1
        """,
        usuario_id,
    )
    return PerfilStats(
        pipeline_activo=fila["pipeline_activo"] or Decimal("0"),
        win_rate=fila["win_rate"] or Decimal("0"),
        oportunidades_abiertas=fila["oportunidades_abiertas"] or 0,
        oportunidades_ganadas=fila["oportunidades_ganadas"] or 0,
        oportunidades_perdidas=fila["oportunidades_perdidas"] or 0,
        ticket_medio=fila["ticket_medio"] or Decimal("0"),
    )


# ── Objetivos ─────────────────────────────────────────────────────────────────

def _calcular_progreso(valor_actual: Decimal, valor_meta: Decimal) -> float:
    if valor_meta == 0:
        return 0.0
    return round(float(valor_actual / valor_meta * 100), 1)


async def listar_objetivos(usuario_id: UUID, conexion: asyncpg.Connection) -> list[ObjetivoRead]:
    try:
        filas = await conexion.fetch(
            "SELECT id, nombre, valor_actual, valor_meta, unidad, periodo FROM comercial_objetivos WHERE usuario_id = $1 ORDER BY creado_en DESC",
            usuario_id,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            return []
        raise
    return [
        ObjetivoRead(
            **dict(f),
            progreso_pct=_calcular_progreso(f["valor_actual"], f["valor_meta"]),
        )
        for f in filas
    ]


async def crear_objetivo(
    usuario_id: UUID,
    datos: ObjetivoCreate,
    conexion: asyncpg.Connection,
) -> ObjetivoRead:
    try:
        fila = await conexion.fetchrow(
            """
            INSERT INTO comercial_objetivos (usuario_id, nombre, valor_actual, valor_meta, unidad, periodo)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, nombre, valor_actual, valor_meta, unidad, periodo
            """,
            usuario_id,
            datos.nombre,
            datos.valor_actual,
            datos.valor_meta,
            datos.unidad.value,
            datos.periodo,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            raise ValueError("La funcionalidad de objetivos de perfil no está disponible en este entorno.")
        raise
    return ObjetivoRead(
        **dict(fila),
        progreso_pct=_calcular_progreso(fila["valor_actual"], fila["valor_meta"]),
    )


async def actualizar_objetivo(
    objetivo_id: UUID,
    usuario_id: UUID,
    datos: ObjetivoUpdate,
    conexion: asyncpg.Connection,
) -> ObjetivoRead:
    try:
        fila = await conexion.fetchrow(
            """
            UPDATE comercial_objetivos
            SET valor_actual = $1
            WHERE id = $2 AND usuario_id = $3
            RETURNING id, nombre, valor_actual, valor_meta, unidad, periodo
            """,
            datos.valor_actual,
            objetivo_id,
            usuario_id,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            raise ValueError("La funcionalidad de objetivos de perfil no está disponible en este entorno.")
        raise
    if not fila:
        raise ValueError("Objetivo no encontrado")
    return ObjetivoRead(
        **dict(fila),
        progreso_pct=_calcular_progreso(fila["valor_actual"], fila["valor_meta"]),
    )


async def eliminar_objetivo(
    objetivo_id: UUID,
    usuario_id: UUID,
    conexion: asyncpg.Connection,
) -> None:
    try:
        resultado = await conexion.execute(
            "DELETE FROM comercial_objetivos WHERE id = $1 AND usuario_id = $2",
            objetivo_id,
            usuario_id,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            raise ValueError("La funcionalidad de objetivos de perfil no está disponible en este entorno.")
        raise
    if resultado == "DELETE 0":
        raise ValueError("Objetivo no encontrado")


# ── Notificaciones ────────────────────────────────────────────────────────────

async def obtener_config_notificaciones(
    usuario_id: UUID,
    conexion: asyncpg.Connection,
) -> NotificacionesConfig:
    try:
        fila = await conexion.fetchrow(
            "SELECT alertas_pipeline, briefing_diario, alerta_win_rate, hora_briefing, umbral_win_rate, voz_tts, duracion_podcast_min FROM notificaciones_config WHERE usuario_id = $1",
            usuario_id,
        )
    except Exception as exc:
        if not _es_error_esquema(exc):
            raise
        fila = None
    if not fila:
        # Config por defecto si no existe
        return NotificacionesConfig(
            alertas_pipeline=True,
            briefing_diario=False,
            alerta_win_rate=True,
            hora_briefing="08:00",
            umbral_win_rate=Decimal("60.0"),
            voz_tts="es-ES",
            duracion_podcast_min=5,
        )
    datos = dict(fila)
    datos["hora_briefing"] = str(fila["hora_briefing"])[:5]  # TIME → "HH:MM"
    return NotificacionesConfig(**datos)


async def actualizar_config_notificaciones(
    usuario_id: UUID,
    datos: NotificacionesUpdate,
    conexion: asyncpg.Connection,
) -> NotificacionesConfig:
    # Upsert: si no existe la config, la crea con defaults
    try:
        await conexion.execute(
            """
            INSERT INTO notificaciones_config (usuario_id) VALUES ($1)
            ON CONFLICT (usuario_id) DO NOTHING
            """,
            usuario_id,
        )
    except Exception as exc:
        if _es_error_esquema(exc):
            # Si no existe la tabla, devolvemos config por defecto para no romper UI.
            return await obtener_config_notificaciones(usuario_id, conexion)
        raise

    campos = []
    valores = []
    idx = 1
    for campo in (
        "alertas_pipeline",
        "briefing_diario",
        "alerta_win_rate",
        "hora_briefing",
        "umbral_win_rate",
        "voz_tts",
        "duracion_podcast_min",
    ):
        valor = getattr(datos, campo)
        if valor is not None:
            campos.append(f"{campo} = ${idx}")
            valores.append(valor)
            idx += 1

    if campos:
        valores.append(usuario_id)
        try:
            await conexion.execute(
                f"UPDATE notificaciones_config SET {', '.join(campos)} WHERE usuario_id = ${idx}",
                *valores,
            )
        except Exception as exc:
            if not _es_error_esquema(exc):
                raise

    return await obtener_config_notificaciones(usuario_id, conexion)
