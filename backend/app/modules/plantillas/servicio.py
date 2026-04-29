"""
Lógica de negocio del módulo Plantillas de documentación.
"""

from uuid import UUID

import asyncpg
from jinja2 import Template, TemplateError

# Variables disponibles por tipo de plantilla
VARIABLES_POR_TIPO = {
    "pdf": [
        "cuenta_nombre", "sector", "num_empleados", "facturacion_estimada",
        "certificaciones_actuales", "pain_points", "productos_recomendados",
        "escenario_optimista_importe", "escenario_medio_importe", "escenario_pesimista_importe",
        "plan_accion", "argumentario", "fecha_generacion",
    ],
    "pptx": [
        "cuenta_nombre", "sector", "num_empleados",
        "productos_recomendados", "escenario_medio_importe",
        "plan_accion", "proxima_accion", "fecha_generacion",
    ],
    "investigacion": [
        "cuenta_nombre", "sector", "num_empleados", "facturacion_estimada",
        "certificaciones_actuales", "noticias_relevantes", "pain_points",
        "oportunidades_detectadas", "presencia_web",
    ],
    "propuesta": [
        "cuenta_nombre", "productos_recomendados", "escenario_medio_importe",
        "plan_accion", "argumentario",
    ],
    "briefing": [
        "cuenta_nombre", "oportunidades_activas", "importe_pipeline",
        "proximos_pasos", "alertas_criticas",
    ],
    "informe": [
        "tipo_informe", "periodo", "destinatario", "pipeline_activo", "importe_ganado",
        "win_rate", "oportunidades_activas", "top_productos", "top_cuentas",
    ],
}


async def listar_plantillas(
    conexion: asyncpg.Connection,
    tipo: str | None = None,
    solo_activas: bool = True,
) -> list[dict]:
    condiciones = []
    args: list = []

    if solo_activas:
        condiciones.append("activa = TRUE")

    if tipo:
        args.append(tipo)
        condiciones.append(f"tipo = ${len(args)}::tipo_plantilla")

    where = "WHERE " + " AND ".join(condiciones) if condiciones else ""

    filas = await conexion.fetch(
        f"""
        SELECT
            p.id, p.nombre, p.tipo, p.activa, p.contenido, p.variables,
            p.creado_en::TEXT AS creado_en,
            p.actualizado_en::TEXT AS actualizado_en,
            u.nombre_completo AS creado_por_nombre
        FROM plantillas_documentacion p
        LEFT JOIN usuarios u ON u.id = p.creado_por
        {where}
        ORDER BY p.tipo, p.nombre
        """,
        *args,
    )
    return [dict(f) for f in filas]


async def obtener_plantilla(conexion: asyncpg.Connection, plantilla_id: UUID) -> dict | None:
    fila = await conexion.fetchrow(
        """
        SELECT
            p.id, p.nombre, p.tipo, p.activa, p.contenido, p.variables,
            p.creado_en::TEXT AS creado_en,
            p.actualizado_en::TEXT AS actualizado_en,
            u.nombre_completo AS creado_por_nombre
        FROM plantillas_documentacion p
        LEFT JOIN usuarios u ON u.id = p.creado_por
        WHERE p.id = $1
        """,
        plantilla_id,
    )
    return dict(fila) if fila else None


async def obtener_plantilla_activa_por_tipo(
    conexion: asyncpg.Connection,
    tipo: str,
) -> dict | None:
    """Devuelve la plantilla activa más reciente para un tipo dado."""
    fila = await conexion.fetchrow(
        """
        SELECT id, nombre, tipo, contenido, variables
        FROM plantillas_documentacion
        WHERE tipo = $1::tipo_plantilla AND activa = TRUE
        ORDER BY actualizado_en DESC
        LIMIT 1
        """,
        tipo,
    )
    return dict(fila) if fila else None


async def crear_plantilla(
    conexion: asyncpg.Connection,
    nombre: str,
    tipo: str,
    contenido: dict,
    creado_por: UUID,
) -> dict:
    variables = VARIABLES_POR_TIPO.get(tipo, [])

    fila = await conexion.fetchrow(
        """
        INSERT INTO plantillas_documentacion (nombre, tipo, contenido, variables, creado_por)
        VALUES ($1, $2::tipo_plantilla, $3, $4, $5)
        RETURNING id, nombre, tipo, activa, contenido, variables,
                  creado_en::TEXT AS creado_en, actualizado_en::TEXT AS actualizado_en
        """,
        nombre,
        tipo,
        contenido,
        variables,
        creado_por,
    )
    return dict(fila)


async def actualizar_plantilla(
    conexion: asyncpg.Connection,
    plantilla_id: UUID,
    nombre: str | None,
    contenido: dict | None,
    activa: bool | None,
) -> dict | None:
    fila_actual = await conexion.fetchrow(
        "SELECT nombre, contenido, activa FROM plantillas_documentacion WHERE id = $1",
        plantilla_id,
    )
    if not fila_actual:
        return None

    fila = await conexion.fetchrow(
        """
        UPDATE plantillas_documentacion
        SET
            nombre   = $2,
            contenido = $3,
            activa   = $4
        WHERE id = $1
        RETURNING id, nombre, tipo, activa, contenido, variables,
                  actualizado_en::TEXT AS actualizado_en
        """,
        plantilla_id,
        nombre if nombre is not None else fila_actual["nombre"],
        contenido if contenido is not None else fila_actual["contenido"],
        activa if activa is not None else fila_actual["activa"],
    )
    return dict(fila)


async def eliminar_plantilla(conexion: asyncpg.Connection, plantilla_id: UUID) -> bool:
    resultado = await conexion.execute(
        "DELETE FROM plantillas_documentacion WHERE id = $1",
        plantilla_id,
    )
    return resultado == "DELETE 1"


def renderizar_template(template_str: str, variables: dict) -> str:
    """Renderiza un string Jinja2 con las variables dadas."""
    try:
        return Template(template_str).render(**variables)
    except TemplateError:
        return template_str  # Si hay error de template, devuelve sin renderizar


def variables_disponibles(tipo: str) -> list[str]:
    return VARIABLES_POR_TIPO.get(tipo, [])
