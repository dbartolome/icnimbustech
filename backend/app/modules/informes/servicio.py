"""
Lógica de negocio del módulo Informes PDF.
Pipeline: datos DB → índice Claude → contenido Claude → PDF ReportLab.
"""

import json
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

from app.config import configuracion
from app.modules.informes.generador_pdf import generar_pdf
from app.modules.informes.schemas import TIPOS_INFORME, SolicitudInforme

DIRECTORIO_INFORMES = Path(__file__).parent.parent.parent.parent / "informes"

# Estado en memoria de los jobs (igual que decks)
_jobs: dict[str, dict[str, Any]] = {}


def _estado_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def _actualizar_job(job_id: str, **kwargs: Any) -> None:
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)


# =============================================================================
# Recopilación de datos del pipeline
# =============================================================================

async def _recopilar_datos(conexion: asyncpg.Connection, usuario_id: UUID, tipo: str, es_global: bool = False) -> dict:
    """Extrae KPIs y datos relevantes del pipeline para el tipo de informe."""

    filtro_prop = "" if es_global else "AND propietario_id = $1"
    args_prop: list = [] if es_global else [usuario_id]

    kpis = await conexion.fetchrow(f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')) AS activas,
            COUNT(*) FILTER (WHERE etapa = 'closed_won') AS ganadas,
            COUNT(*) FILTER (WHERE etapa = 'closed_lost') AS perdidas,
            COALESCE(SUM(importe) FILTER (WHERE etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')), 0) AS pipeline_activo,
            COALESCE(SUM(importe) FILTER (WHERE etapa = 'closed_won'), 0) AS importe_ganado,
            CASE
                WHEN COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) > 0
                THEN ROUND(COUNT(*) FILTER (WHERE etapa='closed_won')::NUMERIC
                    / COUNT(*) FILTER (WHERE etapa IN ('closed_won','closed_lost')) * 100, 1)
                ELSE 0
            END AS win_rate
        FROM oportunidades
        WHERE eliminado_en IS NULL {filtro_prop}
    """, *args_prop)

    top_productos = await conexion.fetch(f"""
        SELECT p.nombre, COUNT(o.id) AS ops, SUM(o.importe) AS total
        FROM oportunidades o
        JOIN productos p ON p.id = o.producto_id
        WHERE o.eliminado_en IS NULL AND o.etapa = 'closed_won' {filtro_prop}
        GROUP BY p.nombre ORDER BY total DESC LIMIT 5
    """, *args_prop)

    top_cuentas = await conexion.fetch(f"""
        SELECT c.nombre, COUNT(o.id) AS ops,
               COALESCE(SUM(o.importe) FILTER (WHERE o.etapa NOT IN ('closed_won','closed_lost','closed_withdrawn')), 0) AS pipeline
        FROM oportunidades o
        JOIN cuentas c ON c.id = o.cuenta_id
        WHERE o.eliminado_en IS NULL {filtro_prop}
        GROUP BY c.nombre ORDER BY pipeline DESC LIMIT 5
    """, *args_prop)

    return {
        "kpis": dict(kpis) if kpis else {},
        "top_productos": [dict(r) for r in top_productos],
        "top_cuentas": [dict(r) for r in top_cuentas],
    }


# =============================================================================
# Llamadas a Claude
# =============================================================================

async def _claude(prompt: str, config=None) -> str:
    from app.modules.ia.servicio import ConfigIA, llamar_ia
    return (await llamar_ia(
        mensajes=[{"role": "user", "content": prompt}],
        system="",
        config=config or ConfigIA(),
        max_tokens=500,
    )).strip()


async def _generar_indice(
    tipo: str,
    datos: dict,
    contexto: str | None,
    config=None,
    instrucciones_plantilla: str | None = None,
) -> list[dict]:
    """Genera el índice de secciones del informe."""
    kpis = datos["kpis"]
    prompt = f"""Eres un consultor de ventas para SGS España. Genera el índice estructurado de un informe de tipo "{TIPOS_INFORME.get(tipo, tipo)}".

Datos disponibles:
- Oportunidades activas: {kpis.get('activas', 0)}
- Pipeline activo: {kpis.get('pipeline_activo', 0):,.0f} €
- Importe ganado: {kpis.get('importe_ganado', 0):,.0f} €
- Win Rate: {kpis.get('win_rate', 0)}%
{f'- Contexto adicional: {contexto}' if contexto else ''}

Devuelve SOLO un JSON válido con esta estructura (sin markdown, sin explicaciones):
[
  {{"titulo": "Nombre de la sección", "descripcion": "Qué incluye esta sección"}},
  ...
]
Máximo 6 secciones. Títulos concisos en español de España.
{f"Instrucciones de plantilla: {instrucciones_plantilla}" if instrucciones_plantilla else ""}"""

    respuesta = await _claude(prompt, config)
    respuesta = respuesta.replace("```json", "").replace("```", "").strip()
    return json.loads(respuesta)


async def _generar_seccion(
    titulo: str,
    descripcion: str,
    datos: dict,
    config=None,
    instrucciones_plantilla: str | None = None,
) -> str:
    """Genera el contenido analítico de una sección."""
    kpis = datos["kpis"]
    top_prod = ", ".join(p["nombre"] for p in datos["top_productos"][:3]) or "N/D"
    top_ctas = ", ".join(c["nombre"] for c in datos["top_cuentas"][:3]) or "N/D"

    prompt = f"""Eres un analista de ventas senior de SGS España. Redacta el contenido de la sección "{titulo}" para un informe ejecutivo.

Descripción de la sección: {descripcion}

Datos del pipeline:
- Pipeline activo: {kpis.get('pipeline_activo', 0):,.0f} €
- Importe ganado: {kpis.get('importe_ganado', 0):,.0f} €
- Win Rate: {kpis.get('win_rate', 0)}%
- Oportunidades activas: {kpis.get('activas', 0)} | Ganadas: {kpis.get('ganadas', 0)} | Perdidas: {kpis.get('perdidas', 0)}
- Top productos ganados: {top_prod}
- Top cuentas por pipeline: {top_ctas}

Escribe 3-4 párrafos analíticos profesionales en español de España. Usa **Negrita** para resaltar insights clave. Sin listas, solo texto fluido. Sé específico con los datos.
{f"Instrucciones de plantilla: {instrucciones_plantilla}" if instrucciones_plantilla else ""}"""

    return await _claude(prompt, config)


# =============================================================================
# Tarea de generación (BackgroundTasks)
# =============================================================================

async def generar_informe_tarea(
    job_id: str,
    informe_id: UUID,
    usuario_id: UUID,
    usuario_nombre: str,
    usuario_rol: str,
    solicitud: SolicitudInforme,
    db_url: str,
    ia_config: dict | None = None,
) -> None:
    import asyncpg as apg

    from app.modules.ia.servicio import ConfigIA
    config = ConfigIA(**ia_config) if ia_config else ConfigIA()

    es_global = usuario_rol in ("admin", "manager")

    conn = await apg.connect(db_url.replace("+asyncpg", ""))
    try:
        _actualizar_job(job_id, estado="generando", progreso=5, paso_actual="Recopilando datos del pipeline…")
        datos = await _recopilar_datos(conn, usuario_id, solicitud.tipo, es_global=es_global)

        from app.modules.plantillas import servicio as plantillas_servicio
        plantilla_activa = await plantillas_servicio.obtener_plantilla_activa_por_tipo(conn, "informe")
        instrucciones_indice = None
        instrucciones_seccion = None
        if plantilla_activa and isinstance(plantilla_activa.get("contenido"), dict):
            instrucciones_indice = plantilla_activa["contenido"].get("prompt_indice")
            instrucciones_seccion = plantilla_activa["contenido"].get("prompt_seccion")

        _actualizar_job(job_id, progreso=25, paso_actual="Generando índice con IA…")
        indice = await _generar_indice(
            solicitud.tipo,
            datos,
            solicitud.contexto,
            config,
            instrucciones_plantilla=instrucciones_indice,
        )

        await conn.execute(
            "UPDATE informes_generados SET indice_json = $1 WHERE id = $2",
            json.dumps(indice), informe_id,
        )
        _actualizar_job(job_id, progreso=40, paso_actual="Redactando secciones con IA…", indice=indice)

        secciones = []
        total = len(indice)
        for i, item in enumerate(indice):
            contenido = await _generar_seccion(
                item["titulo"],
                item["descripcion"],
                datos,
                config,
                instrucciones_plantilla=instrucciones_seccion,
            )
            secciones.append({"titulo": item["titulo"], "contenido": contenido})
            progreso = 40 + int(40 * (i + 1) / total)
            _actualizar_job(job_id, progreso=progreso, paso_actual=f"Sección {i + 1}/{total}: {item['titulo'][:40]}…")

        _actualizar_job(job_id, progreso=85, paso_actual="Renderizando PDF…")

        kpis_portada = {
            "Pipeline activo": f"{datos['kpis'].get('pipeline_activo', 0):,.0f} €",
            "Importe ganado": f"{datos['kpis'].get('importe_ganado', 0):,.0f} €",
            "Win Rate": f"{datos['kpis'].get('win_rate', 0)}%",
            "Oportunidades activas": str(datos['kpis'].get('activas', 0)),
        }
        titulo = TIPOS_INFORME.get(solicitud.tipo, solicitud.tipo)
        pdf_bytes = generar_pdf(
            titulo=titulo,
            tipo_label=titulo,
            comercial=usuario_nombre,
            periodo=solicitud.periodo,
            secciones=secciones,
            kpis=kpis_portada,
        )

        DIRECTORIO_INFORMES.mkdir(parents=True, exist_ok=True)
        nombre_pdf = f"informe_{informe_id}.pdf"
        ruta = DIRECTORIO_INFORMES / nombre_pdf
        ruta.write_bytes(pdf_bytes)

        await conn.execute(
            """UPDATE informes_generados
               SET estado = 'completado', ruta_pdf = $1, paginas = $2, completado_en = NOW()
               WHERE id = $3""",
            str(ruta), len(secciones) + 1, informe_id,
        )

        # Registrar artefacto unificado (fallo silencioso para no romper flujo actual).
        try:
            from app.modules.artefactos import servicio as artefactos_servicio

            clave = f"informe:{solicitud.tipo}:{usuario_id}"
            await artefactos_servicio.registrar_version_artefacto(
                conn,
                tipo="informe",
                subtipo=solicitud.tipo,
                entidad_tipo=None,
                entidad_id=None,
                cuenta_id=None,
                usuario_id=usuario_id,
                titulo=titulo,
                prompt=solicitud.contexto,
                resultado_texto="\n\n".join(s["contenido"] for s in secciones),
                resultado_json={"indice": indice, "kpis": datos.get("kpis", {})},
                storage_key=str(ruta),
                modelo=(config.ollama_modelo if getattr(config, "proveedor", "") == "ollama" else getattr(config, "proveedor", None)),
                plantilla_id=(plantilla_activa["id"] if plantilla_activa else None),
                metadatos={
                    "periodo": solicitud.periodo,
                    "destinatario": solicitud.destinatario,
                    "clave_regeneracion": clave,
                },
                fuentes=[],
                origen_tabla="informes_generados",
                origen_id=str(informe_id),
            )
        except Exception:
            pass

        _actualizar_job(job_id, estado="completado", progreso=100, paso_actual="¡Informe listo!")

    except Exception as exc:
        await conn.execute(
            "UPDATE informes_generados SET estado = 'error', error_msg = $1 WHERE id = $2",
            str(exc), informe_id,
        )
        _actualizar_job(job_id, estado="error", paso_actual=f"Error: {exc}")
    finally:
        await conn.close()


# =============================================================================
# Servicios síncronos
# =============================================================================

async def iniciar_generacion(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    usuario_nombre: str,
    solicitud: SolicitudInforme,
) -> str:
    titulo = TIPOS_INFORME.get(solicitud.tipo, solicitud.tipo)
    if solicitud.periodo:
        titulo += f" · {solicitud.periodo}"

    fila = await conexion.fetchrow(
        """INSERT INTO informes_generados (usuario_id, tipo, titulo, periodo, destinatario, contexto)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
        usuario_id, solicitud.tipo, titulo,
        solicitud.periodo, solicitud.destinatario, solicitud.contexto,
    )
    informe_id = fila["id"]
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "informe_id": str(informe_id),
        "estado": "pendiente",
        "progreso": 0,
        "paso_actual": "Iniciando…",
        "indice": None,
    }
    return job_id, informe_id


async def listar_informes(
    conexion: asyncpg.Connection,
    usuario_id: UUID,
    pagina: int = 1,
    por_pagina: int = 20,
    sort_by: str = "creado_en",
    sort_dir: str = "desc",
) -> list[dict]:
    direccion = "ASC" if sort_dir.lower() == "asc" else "DESC"
    campos_validos = {
        "tipo": "tipo",
        "titulo": "titulo",
        "estado": "estado",
        "paginas": "paginas",
        "creado_en": "creado_en",
        "completado_en": "completado_en",
    }
    campo_orden = campos_validos.get(sort_by.lower(), "creado_en")
    offset = (pagina - 1) * por_pagina
    filas = await conexion.fetch(
        """SELECT id, tipo, titulo, periodo, destinatario, estado, paginas,
                  creado_en::TEXT, completado_en::TEXT
           FROM informes_generados
           WHERE usuario_id = $1
           ORDER BY """ + campo_orden + f""" {direccion} NULLS LAST, id DESC
           LIMIT $2 OFFSET $3""",
        usuario_id,
        por_pagina,
        offset,
    )
    return [dict(f) for f in filas]


async def obtener_ruta_pdf(conexion: asyncpg.Connection, informe_id: UUID, usuario_id: UUID) -> Path | None:
    fila = await conexion.fetchrow(
        "SELECT ruta_pdf FROM informes_generados WHERE id = $1 AND usuario_id = $2 AND estado = 'completado'",
        informe_id, usuario_id,
    )
    if not fila or not fila["ruta_pdf"]:
        return None
    ruta = Path(fila["ruta_pdf"])
    return ruta if ruta.exists() else None


async def eliminar_informe(conexion: asyncpg.Connection, informe_id: UUID, usuario_id: UUID) -> bool:
    fila = await conexion.fetchrow(
        "SELECT ruta_pdf FROM informes_generados WHERE id = $1 AND usuario_id = $2",
        informe_id, usuario_id,
    )
    if not fila:
        return False
    if fila["ruta_pdf"]:
        ruta = Path(fila["ruta_pdf"])
        if ruta.exists():
            ruta.unlink()
    await conexion.execute(
        "DELETE FROM informes_generados WHERE id = $1 AND usuario_id = $2",
        informe_id, usuario_id,
    )
    return True
