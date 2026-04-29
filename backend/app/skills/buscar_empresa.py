"""
Skill: buscar_empresa

Investiga información pública de una empresa usando proveedores externos
de IA con capacidades de búsqueda web.
SOLO información pública — nunca recibe datos del pipeline SGS.
"""

import json
import re
from dataclasses import dataclass, field

import anthropic
import httpx
from app.modules.ia.proveedores import (
    PROVEEDOR_LOCAL,
    obtener_ollama_url_research,
    normalizar_proveedor,
    obtener_api_key_externa,
    obtener_modelo_research,
    obtener_proveedor_research_activo,
)


@dataclass
class FichaEmpresa:
    nombre: str
    sector: str | None = None
    num_empleados: str | None = None
    facturacion_estimada: str | None = None
    certificaciones_actuales: list[str] = field(default_factory=list)
    noticias_relevantes: list[str] = field(default_factory=list)
    pain_points: list[str] = field(default_factory=list)
    oportunidades_detectadas: list[str] = field(default_factory=list)
    presencia_web: str | None = None
    fuentes: list[str] = field(default_factory=list)
    raw_research: str = ""


_SYSTEM = """Eres un analista de inteligencia comercial especializado en empresas españolas.
Tu misión es investigar empresas para identificar oportunidades de certificación y auditoría.

Cuando investigues una empresa:
- Usa web search para encontrar información real y verificable
- Busca específicamente: sector, tamaño, certificaciones ISO actuales, noticias recientes, problemas de calidad o compliance
- Sé específico con los datos — evita generalidades
- Si no encuentras información sobre un punto, indica "No encontrado" en lugar de inventar
- Responde SIEMPRE en JSON válido con el esquema solicitado
"""

_PROMPT = """Investiga en profundidad la empresa "{nombre}" en España.

Busca y estructura esta información:
1. Sector y actividad principal exacta
2. Tamaño: número de empleados y facturación si está disponible públicamente
3. Certificaciones ISO o de calidad que ya tiene (busca en su web, LinkedIn, noticias)
4. Noticias relevantes de los últimos 12 meses (expansión, premios, problemas, cambios directivos)
5. Presencia digital: URL web principal
6. Pain points detectados públicamente (multas, reclamaciones, incidentes de calidad, auditorías fallidas)
7. Oportunidades de certificación identificadas (sectores donde opera que requieren ciertas normas)

Devuelve SOLO este JSON, sin texto adicional:
{{
  "sector": "descripción del sector",
  "num_empleados": "rango aproximado o número exacto",
  "facturacion_estimada": "cifra o rango si está disponible, si no: null",
  "certificaciones_actuales": ["ISO 9001:2015", "..."],
  "noticias_relevantes": ["noticia 1", "noticia 2"],
  "pain_points": ["problema detectado 1", "..."],
  "oportunidades_detectadas": ["podría necesitar ISO 14001 por...", "..."],
  "presencia_web": "https://...",
  "fuentes": ["url1", "url2"]
}}
"""


def _extraer_json(texto: str) -> dict:
    """Extrae el primer JSON válido de la respuesta de Claude."""
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

    raise ValueError(f"No se encontró JSON válido en la respuesta")


def _extraer_texto_final(contenido: list) -> str:
    """Extrae solo los bloques de texto de la respuesta (ignora tool_use/tool_result)."""
    return "\n".join(
        bloque.text
        for bloque in contenido
        if hasattr(bloque, "type") and bloque.type == "text"
    )


async def _investigar_con_anthropic(prompt: str, api_key: str, modelo: str) -> tuple[dict, str]:
    cliente = anthropic.Anthropic(api_key=api_key)
    mensajes = [{"role": "user", "content": prompt}]

    for _ in range(6):  # max 6 iteraciones para evitar loops infinitos
        respuesta = cliente.messages.create(
            model=modelo,
            max_tokens=4096,
            system=_SYSTEM,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=mensajes,
        )

        if respuesta.stop_reason == "end_turn":
            texto_final = _extraer_texto_final(respuesta.content)
            try:
                return _extraer_json(texto_final), texto_final
            except ValueError:
                return {}, texto_final

        if respuesta.stop_reason == "tool_use":
            mensajes.append({"role": "assistant", "content": respuesta.content})
            resultados_tool = [
                {
                    "type": "tool_result",
                    "tool_use_id": bloque.id,
                    "content": "Búsqueda realizada.",
                }
                for bloque in respuesta.content
                if hasattr(bloque, "type") and bloque.type == "tool_use"
            ]
            mensajes.append({"role": "user", "content": resultados_tool})
        else:
            texto_final = _extraer_texto_final(respuesta.content)
            return {}, texto_final

    return {}, ""


def _extraer_texto_openai(respuesta: dict) -> str:
    if isinstance(respuesta.get("output_text"), str) and respuesta["output_text"].strip():
        return respuesta["output_text"].strip()

    trozos: list[str] = []
    for item in respuesta.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for bloque in item.get("content", []) or []:
            if bloque.get("type") in {"output_text", "text"}:
                texto = (bloque.get("text") or "").strip()
                if texto:
                    trozos.append(texto)
    return "\n".join(trozos).strip()


async def _investigar_con_openai(prompt: str, api_key: str, modelo: str) -> tuple[dict, str]:
    payload = {
        "model": modelo,
        "tools": [{"type": "web_search_preview"}],
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": _SYSTEM}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90.0) as cliente:
        respuesta = await cliente.post("https://api.openai.com/v1/responses", json=payload, headers=headers)
        respuesta.raise_for_status()
        datos = respuesta.json()

    texto_final = _extraer_texto_openai(datos)
    if not texto_final:
        return {}, json.dumps(datos, ensure_ascii=False)[:2000]
    try:
        return _extraer_json(texto_final), texto_final
    except ValueError:
        return {}, texto_final


def _extraer_texto_gemini(respuesta: dict) -> str:
    candidatos = respuesta.get("candidates") or []
    if not candidatos:
        return ""
    partes = candidatos[0].get("content", {}).get("parts", []) or []
    textos = [(p.get("text") or "").strip() for p in partes if p.get("text")]
    return "\n".join([t for t in textos if t]).strip()


async def _investigar_con_gemini(prompt: str, api_key: str, modelo: str) -> tuple[dict, str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
    payload = {
        "system_instruction": {"parts": [{"text": _SYSTEM}]},
        "tools": [{"google_search": {}}],
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    async with httpx.AsyncClient(timeout=90.0) as cliente:
        respuesta = await cliente.post(url, json=payload)
        respuesta.raise_for_status()
        datos = respuesta.json()

    texto_final = _extraer_texto_gemini(datos)
    if not texto_final:
        return {}, json.dumps(datos, ensure_ascii=False)[:2000]
    try:
        return _extraer_json(texto_final), texto_final
    except ValueError:
        return {}, texto_final


_SYSTEM_OLLAMA = """Eres un analista de inteligencia comercial. Investiga empresas españolas y responde SOLO con JSON válido, sin texto adicional."""

_PROMPT_OLLAMA = """Investiga la empresa "{nombre}" en España. Devuelve SOLO este JSON:
{{"sector":"sector principal","num_empleados":"rango","facturacion_estimada":null,"certificaciones_actuales":[],"noticias_relevantes":[],"pain_points":[],"oportunidades_detectadas":[],"presencia_web":null,"fuentes":[]}}"""


async def _investigar_con_ollama(prompt: str, modelo: str, ollama_url: str) -> tuple[dict, str]:
    # Para Ollama (modelo local pequeño) usamos un prompt compacto para evitar timeout
    nombre_empresa = ""
    import re as _re
    m = _re.search(r'Investiga en profundidad la empresa "(.+?)" en España', prompt)
    if m:
        nombre_empresa = m.group(1)
    prompt_corto = _PROMPT_OLLAMA.format(nombre=nombre_empresa) if nombre_empresa else prompt

    payload_v1 = {
        "model": modelo,
        "stream": False,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": _SYSTEM_OLLAMA},
            {"role": "user", "content": prompt_corto},
        ],
    }
    payload_api = {
        "model": modelo,
        "stream": False,
        "messages": payload_v1["messages"],
        "options": {"num_predict": 500},
    }
    payload_generate = {
        "model": modelo,
        "stream": False,
        "system": _SYSTEM_OLLAMA,
        "prompt": prompt_corto,
        "options": {"num_predict": 500},
    }
    base = ollama_url.rstrip("/")
    errores: list[str] = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as cliente:
        try:
            respuesta = await cliente.post(base + "/v1/chat/completions", json=payload_v1)
            respuesta.raise_for_status()
            datos = respuesta.json()
            texto_final = (
                datos.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
            errores.append(f"/v1/chat/completions -> {e.response.status_code}")
            respuesta = await cliente.post(base + "/api/chat", json=payload_api)
            try:
                respuesta.raise_for_status()
                datos = respuesta.json()
                texto_final = (datos.get("message", {}).get("content") or "").strip()
            except httpx.HTTPStatusError as e2:
                if e2.response.status_code != 404:
                    raise
                errores.append(f"/api/chat -> {e2.response.status_code}")
                respuesta = await cliente.post(base + "/api/generate", json=payload_generate)
                try:
                    respuesta.raise_for_status()
                    datos = respuesta.json()
                    texto_final = (datos.get("response") or "").strip()
                except httpx.HTTPStatusError as e3:
                    if e3.response.status_code != 404:
                        raise
                    errores.append(f"/api/generate -> {e3.response.status_code}")
                    raise RuntimeError(
                        "No se detectó una API Ollama compatible en Deep Research. "
                        f"Endpoints probados: {', '.join(errores)}"
                    )

    if not texto_final:
        return {}, ""
    try:
        return _extraer_json(texto_final), texto_final
    except ValueError:
        return {}, texto_final


async def buscar_empresa(nombre_empresa: str) -> FichaEmpresa:
    """
    Investiga una empresa con proveedor externo configurado para research.
    Soporte actual: anthropic, openai, gemini.

    No recibe ni devuelve datos del pipeline SGS — solo información pública.
    """
    proveedor = normalizar_proveedor(obtener_proveedor_research_activo(), "anthropic")
    api_key = obtener_api_key_externa(proveedor)
    if proveedor != PROVEEDOR_LOCAL and not api_key:
        raise ValueError(f"API key no configurada para proveedor research '{proveedor}'")
    modelo = obtener_modelo_research(proveedor)
    prompt = _PROMPT.format(nombre=nombre_empresa)

    if proveedor == "anthropic":
        datos, raw = await _investigar_con_anthropic(prompt, api_key, modelo)
    elif proveedor == "openai":
        datos, raw = await _investigar_con_openai(prompt, api_key, modelo)
    elif proveedor == "gemini":
        datos, raw = await _investigar_con_gemini(prompt, api_key, modelo)
    elif proveedor == PROVEEDOR_LOCAL:
        datos, raw = await _investigar_con_ollama(prompt, modelo, obtener_ollama_url_research())
    else:
        raise ValueError(
            f"Proveedor research '{proveedor}' no soportado para deep research en esta versión. "
            "Soportados: anthropic, openai, gemini, ollama."
        )

    return FichaEmpresa(
        nombre=nombre_empresa,
        sector=datos.get("sector"),
        num_empleados=datos.get("num_empleados"),
        facturacion_estimada=datos.get("facturacion_estimada"),
        certificaciones_actuales=datos.get("certificaciones_actuales") or [],
        noticias_relevantes=datos.get("noticias_relevantes") or [],
        pain_points=datos.get("pain_points") or [],
        oportunidades_detectadas=datos.get("oportunidades_detectadas") or [],
        presencia_web=datos.get("presencia_web"),
        fuentes=datos.get("fuentes") or [],
        raw_research=raw,
    )


def formatear_para_prompt(ficha: FichaEmpresa) -> str:
    """
    Convierte la ficha a texto para incluir en el prompt del Agente 2 (Ollama).
    Solo información pública — sin datos del pipeline.
    """
    certs = ", ".join(ficha.certificaciones_actuales) or "Ninguna detectada"
    pain = "\n".join(f"  - {p}" for p in ficha.pain_points) or "  Ninguno detectado"
    opps = "\n".join(f"  - {o}" for o in ficha.oportunidades_detectadas) or "  Sin datos"

    return f"""
INVESTIGACIÓN PÚBLICA — {ficha.nombre}
- Sector: {ficha.sector or 'No identificado'}
- Empleados: {ficha.num_empleados or 'No disponible'}
- Facturación estimada: {ficha.facturacion_estimada or 'No disponible'}
- Web: {ficha.presencia_web or 'No encontrada'}
- Certificaciones actuales: {certs}

Pain points detectados:
{pain}

Oportunidades identificadas:
{opps}
""".strip()
