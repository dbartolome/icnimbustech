"""
Agente 2 — AnalistaPipeline

Cruza la investigación pública (Agente 1) con los datos reales del pipeline SGS
y genera una propuesta comercial estructurada.

Motor: Ollama local — los datos confidenciales NUNCA salen del servidor.
"""

import json
import logging
import re
from typing import Any
from uuid import UUID

import asyncpg

from app.agents.base import AgentBase, ConfigAgente, ResultadoAgente
from app.config import configuracion
from app.skills.analizar_pipeline import analizar_pipeline, formatear_para_prompt as fmt_pipeline
from app.skills.buscar_empresa import formatear_para_prompt as fmt_investigacion
from app.skills.calcular_escenarios import calcular_escenarios, formatear_para_prompt as fmt_escenarios

# Configuración base — se sobreescribe con runtime config al ejecutar
_CONFIG_BASE = ConfigAgente(
    proveedor="ollama",
    ollama_url=configuracion.OLLAMA_URL,
    ollama_modelo=configuracion.OLLAMA_MODEL_DEFAULT,
    temperatura=0.2,
    max_tokens=3000,
)

logger = logging.getLogger(__name__)

_CATALOGO_FALLBACK = [
    {
        "linea": "Certificación y auditoría",
        "servicio": "Certificación de sistemas de gestión y auditorías de tercera parte.",
        "normas_clave": "ISO 9001, ISO 14001, ISO 45001, ISO 27001, ISO 50001",
    },
    {
        "linea": "Inspección y ensayos técnicos",
        "servicio": "Inspecciones reglamentarias y ensayos no destructivos.",
        "normas_clave": "RIPCI, ISO 17020, ISO 9712",
    },
    {
        "linea": "Sostenibilidad y ESG",
        "servicio": "Huella de carbono, verificación ESG y reporting CSRD.",
        "normas_clave": "ISO 14064, ISO 14067, CSRD, ESRS",
    },
    {
        "linea": "Ciberseguridad y Digital Trust",
        "servicio": "Certificación y consultoría en seguridad de la información y privacidad.",
        "normas_clave": "ISO 27001, ISO 27701, ISO 22301, NIS2, DORA",
    },
]


def _config_runtime() -> ConfigAgente:
    """Carga config operacional desde runtime (DB) para usar el modelo configurado."""
    try:
        from app.modules.ia.proveedores import (
            normalizar_ollama_url_operacional,
            obtener_configs_operacionales,
        )
        cfg = obtener_configs_operacionales().get("informes", {})
        return ConfigAgente(
            proveedor="ollama",
            ollama_url=normalizar_ollama_url_operacional(
                cfg.get("ollama_url") or configuracion.OLLAMA_URL
            ),
            ollama_modelo=cfg.get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT,
            temperatura=0.2,
            max_tokens=3000,
        )
    except Exception:
        return _CONFIG_BASE

_SYSTEM = """Eres un analista comercial experto en certificación y auditoría industrial para SGS España.
Tu misión es generar propuestas comerciales estructuradas cruzando datos de investigación de empresas con el portfolio SGS.

REGLAS ESTRICTAS:
- Responde SIEMPRE con JSON válido, sin texto adicional antes ni después del JSON.
- Usa SOLO los datos proporcionados — no inventes cifras ni empresas.
- Los importes son los calculados previamente — no los cambies.
- Si no tienes datos suficientes para un campo, usa null.
- Los porcentajes van como número entero (85, no "85%").
- Responde en español de España.
"""

_PROMPT = """Eres un analista SGS España. Analiza estos datos y genera una propuesta comercial en JSON.

{datos_investigacion}

{datos_pipeline}

CATÁLOGO SGS (top productos disponibles):
{catalogo}

{datos_escenarios}

Responde SOLO con este JSON (sin texto adicional):
{{
  "productos_recomendados": [
    {{"producto": "nombre del servicio SGS", "score_fit": 80, "norma": "ISO XXXX", "argumentario": "motivo breve"}}
  ],
  "escenario_optimista": {{"importe": 50000, "productos": ["producto1"], "probabilidad": 70, "plazo_meses": 4, "descripcion": "escenario favorable"}},
  "escenario_medio": {{"importe": 30000, "productos": ["producto1"], "probabilidad": 50, "plazo_meses": 7, "descripcion": "escenario base"}},
  "escenario_pesimista": {{"importe": 15000, "productos": ["producto1"], "probabilidad": 30, "plazo_meses": 12, "descripcion": "escenario conservador"}},
  "plan_de_accion": [
    {{"accion": "acción concreta", "prioridad": 1, "tipo": "nuevo", "plazo_dias": 15, "responsable": "comercial"}}
  ],
  "argumentario_general": "Argumentario de 2 párrafos para el comercial."
}}
"""


def _extraer_json(texto: str) -> dict:
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("No se encontró JSON válido en la respuesta de Ollama")


async def _llamar_ollama(prompt: str, system: str, config: ConfigAgente) -> str:
    """
    Llama a Ollama con fallback entre endpoints:
    /api/chat → /v1/chat/completions → /api/generate
    """
    import httpx

    base = config.ollama_url.rstrip("/")
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    timeout = httpx.Timeout(90.0, connect=10.0)
    errores: list[str] = []

    async with httpx.AsyncClient(timeout=timeout) as cliente:
        # 1. Intento /api/chat (nativo Ollama)
        try:
            r = await cliente.post(base + "/api/chat", json={
                "model": config.ollama_modelo,
                "stream": False,
                "messages": msgs,
                "options": {"num_predict": config.max_tokens},
            })
            if r.status_code != 404:
                r.raise_for_status()
                return r.json().get("message", {}).get("content", "")
        except httpx.TimeoutException as e:
            errores.append(f"/api/chat timeout: {e}")
        except httpx.RequestError as e:
            errores.append(f"/api/chat request error: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                errores.append(f"/api/chat status {e.response.status_code}: {e}")

        # 2. Intento OpenAI-compatible
        try:
            r = await cliente.post(base + "/v1/chat/completions", json={
                "model": config.ollama_modelo,
                "stream": False,
                "max_tokens": config.max_tokens,
                "messages": msgs,
            })
            if r.status_code != 404:
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException as e:
            errores.append(f"/v1/chat/completions timeout: {e}")
        except httpx.RequestError as e:
            errores.append(f"/v1/chat/completions request error: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                errores.append(f"/v1/chat/completions status {e.response.status_code}: {e}")

        # 3. Intento /api/generate (Ollama antiguo)
        try:
            r = await cliente.post(base + "/api/generate", json={
                "model": config.ollama_modelo,
                "stream": False,
                "system": system,
                "prompt": prompt,
                "options": {"num_predict": config.max_tokens},
            })
            if r.status_code != 404:
                r.raise_for_status()
                return r.json().get("response", "")
        except httpx.TimeoutException as e:
            errores.append(f"/api/generate timeout: {e}")
        except httpx.RequestError as e:
            errores.append(f"/api/generate request error: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                errores.append(f"/api/generate status {e.response.status_code}: {e}")

    detalle = " | ".join(errores) if errores else "sin detalle"
    raise RuntimeError(f"No se pudo obtener respuesta de Ollama. {detalle}")


async def _obtener_catalogo(sector: str | None, conexion: asyncpg.Connection) -> str:
    """Obtiene productos del catálogo SGS relevantes para el sector."""
    try:
        filas = await conexion.fetch(
            "SELECT linea, servicio, normas_clave FROM catalogo_servicios ORDER BY linea LIMIT 20"
        )
    except asyncpg.UndefinedTableError:
        logger.warning(
            "Tabla catalogo_servicios no existe. Se usa catálogo fallback para generar propuesta."
        )
        filas = _CATALOGO_FALLBACK
    if not filas:
        return "Catálogo no disponible"
    return "\n".join(
        f"- {r['linea']}: {r['servicio'][:120]} | Normas: {r['normas_clave'] or 'N/A'}"
        for r in filas
    )


class AnalistaPipeline(AgentBase):
    nombre = "analista_pipeline"

    async def run(
        self,
        entrada: dict[str, Any],
        conexion: asyncpg.Connection,
    ) -> ResultadoAgente:
        """
        entrada esperada: {"cuenta_id": "uuid", "investigacion_id": "uuid"}
        Devuelve: {"propuesta_id": "uuid"}
        """
        try:
            cuenta_id = UUID(entrada["cuenta_id"])
            investigacion_id = UUID(entrada["investigacion_id"])
        except (KeyError, ValueError) as e:
            return ResultadoAgente(exito=False, error=f"Parámetros inválidos: {e}")

        # Crear registro de propuesta en estado "procesando"
        cfg = _config_runtime()
        propuesta_id = await conexion.fetchval(
            """
            INSERT INTO propuestas_comerciales
                (cuenta_id, investigacion_id, estado, modelo_usado, iniciado_en)
            VALUES ($1, $2, 'procesando', $3, now())
            RETURNING id
            """,
            cuenta_id,
            investigacion_id,
            cfg.ollama_modelo,
        )

        try:
            # 1. Leer investigación pública (Agente 1)
            inv = await conexion.fetchrow(
                """
                SELECT sector, num_empleados, facturacion_estimada,
                       certificaciones_actuales, noticias_relevantes,
                       pain_points, oportunidades_detectadas, presencia_web
                FROM investigaciones_empresa WHERE id = $1
                """,
                investigacion_id,
            )
            if not inv:
                raise ValueError(f"Investigación {investigacion_id} no encontrada")

            # Construir objeto FichaEmpresa para formatear
            from app.skills.buscar_empresa import FichaEmpresa
            nombre_cuenta = await conexion.fetchval(
                "SELECT nombre FROM cuentas WHERE id = $1", cuenta_id
            )
            ficha = FichaEmpresa(
                nombre=nombre_cuenta or "Empresa",
                sector=inv["sector"],
                num_empleados=inv["num_empleados"],
                facturacion_estimada=inv["facturacion_estimada"],
                certificaciones_actuales=list(inv["certificaciones_actuales"] or []),
                noticias_relevantes=list(inv["noticias_relevantes"] or []),
                pain_points=list(inv["pain_points"] or []),
                oportunidades_detectadas=list(inv["oportunidades_detectadas"] or []),
                presencia_web=inv["presencia_web"],
            )

            # 2. Leer métricas reales del pipeline (datos confidenciales — Ollama)
            metricas = await analizar_pipeline(cuenta_id, conexion)

            # 3. Obtener productos top para calcular escenarios
            productos_top = [p["nombre"] for p in metricas.productos_contratados[:3]]

            # 4. Calcular escenarios con datos reales
            escenarios = await calcular_escenarios(cuenta_id, productos_top, conexion)

            # 5. Obtener catálogo SGS relevante
            catalogo = await _obtener_catalogo(inv["sector"], conexion)

            # 6. Construir prompt y llamar a Ollama
            prompt = _PROMPT.format(
                datos_investigacion=fmt_investigacion(ficha),
                datos_pipeline=fmt_pipeline(metricas),
                catalogo=catalogo,
                datos_escenarios=fmt_escenarios(escenarios),
            )

            respuesta_raw = await _llamar_ollama(prompt, _SYSTEM, _config_runtime())
            datos = _extraer_json(respuesta_raw)

            # 7. Persistir propuesta — usar escenarios calculados si Ollama los alteró
            def _escenario_json(e_ollama: dict | None, e_real) -> dict:
                """Prioriza importes reales sobre los de Ollama."""
                if not e_ollama:
                    return {
                        "importe": e_real.importe,
                        "productos": e_real.productos,
                        "probabilidad": e_real.probabilidad,
                        "plazo_meses": e_real.plazo_meses,
                        "descripcion": e_real.descripcion,
                    }
                return {**e_ollama, "importe": e_real.importe}

            await conexion.execute(
                """
                UPDATE propuestas_comerciales SET
                    estado                  = 'completada',
                    productos_recomendados  = $2,
                    escenario_optimista     = $3,
                    escenario_medio         = $4,
                    escenario_pesimista     = $5,
                    plan_de_accion          = $6,
                    argumentario_general    = $7,
                    completado_en           = now()
                WHERE id = $1
                """,
                propuesta_id,
                json.dumps(datos.get("productos_recomendados", [])),
                json.dumps(_escenario_json(datos.get("escenario_optimista"), escenarios.optimista)),
                json.dumps(_escenario_json(datos.get("escenario_medio"), escenarios.medio)),
                json.dumps(_escenario_json(datos.get("escenario_pesimista"), escenarios.pesimista)),
                json.dumps(datos.get("plan_de_accion", [])),
                datos.get("argumentario_general"),
            )

            return ResultadoAgente(
                exito=True,
                datos={"propuesta_id": str(propuesta_id)},
            )

        except Exception as e:
            import traceback as _tb
            msg = str(e) or repr(e) or type(e).__name__
            await conexion.execute(
                "UPDATE propuestas_comerciales SET estado = 'error', error_msg = $2 WHERE id = $1",
                propuesta_id,
                f"{msg}\n{_tb.format_exc()}",
            )
            return ResultadoAgente(exito=False, error=msg)
