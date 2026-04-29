"""
Lógica de negocio del módulo IA Copilot.
Soporta Anthropic Claude y Ollama (API OpenAI-compatible).
"""

import json
from dataclasses import dataclass, field
from typing import AsyncIterator

import anthropic
import asyncpg
import httpx

from app.config import configuracion


@dataclass
class ConfigIA:
    proveedor: str = "anthropic"          # "anthropic" | "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_modelo: str = "llama3.2"


async def obtener_modelos_ollama(ollama_url: str) -> list[dict]:
    """
    Devuelve la lista de modelos disponibles en una instancia de Ollama.
    Se ejecuta en backend para evitar CORS en el navegador.
    """
    url = ollama_url.rstrip("/") + "/api/tags"
    async with httpx.AsyncClient(timeout=8.0) as cliente:
        respuesta = await cliente.get(url)
        respuesta.raise_for_status()
        datos = respuesta.json()

    modelos = datos.get("models", [])
    salida: list[dict] = []
    for modelo in modelos:
        nombre = modelo.get("name")
        if not nombre:
            continue
        salida.append(
            {
                "name": nombre,
                "size": int(modelo.get("size", 0) or 0),
            }
        )
    return salida

# Contexto de negocio base (KPIs del pipeline)
_SYSTEM_BASE = """Eres el Copilot de Inteligencia Comercial de SGS España.
Tienes acceso al pipeline comercial completo de la unidad de negocio BA (Business Assurance).

DATOS DEL PIPELINE (actualizados):
- Total oportunidades: ~3.543 activas
- Pipeline activo: ~22,5M€
- Importe ganado: ~3,2M€
- Win Rate global: ~82,6%
- Ticket medio ganado: ~7.200€
- Equipo: 81 comerciales activos

PRODUCTOS PRINCIPALES (por Win Rate):
1. IDI Proyectos — WR 98,1% — 577K€ ganado
2. RBS Social — WR 85,9% — 131K€ ganado
3. ISO/IEC 27001:2022 — WR 85,7% — 201K€ ganado
4. CXM Audits — WR 85,7% — 571K€ ganado
5. ISO 9001:2015 — WR 79,4% — 671K€ ganado (mayor volumen)

{catalogo_section}

{matriz_section}

INSTRUCCIONES:
- Responde siempre en español de España
- Sé conciso y directo, orientado a la toma de decisiones comerciales
- Cuando te pregunten por un servicio SGS, usa el catálogo oficial para describir entregables y normas clave
- Cuando te pregunten por un sector o tipo de cliente, usa la matriz sectorial para identificar certificaciones típicas y pain points
- Si no tienes suficiente información para responder con precisión, indícalo claramente
- Puedes sugerir acciones comerciales concretas basadas en los datos
"""


async def construir_system_prompt(conexion: asyncpg.Connection) -> str:
    """Construye el system prompt enriquecido con el catálogo real de SGS España."""
    try:
        catalogo = await conexion.fetch(
            "SELECT linea, servicio, entregables, normas_clave FROM catalogo_servicios ORDER BY linea"
        )
        matriz = await conexion.fetch(
            "SELECT sector, certificaciones_tipo, pain_points FROM matriz_sectorial ORDER BY sector"
        )

        catalogo_lines = "\n".join(
            f"• {r['linea']}: {r['servicio'][:180]} | Entregables: {(r['entregables'] or '')[:120]} | Normas: {r['normas_clave'] or ''}"
            for r in catalogo
        )
        catalogo_section = f"PORTFOLIO SGS ESPAÑA (catálogo oficial):\n{catalogo_lines}"

        matriz_lines = "\n".join(
            f"• {r['sector']}: certs={r['certificaciones_tipo'][:100]} | pain points={r['pain_points'][:120]}"
            for r in matriz
        )
        matriz_section = f"MATRIZ SECTORIAL (sector → certificaciones → pain points):\n{matriz_lines}"

    except Exception:
        catalogo_section = ""
        matriz_section = ""

    return _SYSTEM_BASE.format(
        catalogo_section=catalogo_section,
        matriz_section=matriz_section,
    )


async def llamar_ia(
    mensajes: list[dict],
    system: str,
    config: ConfigIA | None = None,
    max_tokens: int = 800,
    temperature: float = 0.3,
) -> str:
    """
    Llamada síncrona (no streaming) a Anthropic o Ollama.
    Función compartida para Voice, Informes y Decks.
    """
    cfg = config or ConfigIA()
    if cfg.proveedor == "ollama":
        payload = {
            "model": cfg.ollama_modelo,
            "stream": False,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, *mensajes] if system else mensajes,
        }
        url = cfg.ollama_url.rstrip("/") + "/v1/chat/completions"
        async with httpx.AsyncClient(timeout=180.0) as cliente:
            r = await cliente.post(url, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    else:
        cliente = anthropic.Anthropic(api_key=configuracion.ANTHROPIC_API_KEY)
        respuesta = cliente.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=mensajes,
        )
        return respuesta.content[0].text


def llamar_ia_sync(
    mensajes: list[dict],
    system: str,
    config: ConfigIA | None = None,
    max_tokens: int = 800,
    temperature: float = 0.3,
) -> str:
    """
    Versión síncrona para BackgroundTasks (Decks, Informes).
    """
    cfg = config or ConfigIA()
    if cfg.proveedor == "ollama":
        payload = {
            "model": cfg.ollama_modelo,
            "stream": False,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, *mensajes] if system else mensajes,
        }
        url = cfg.ollama_url.rstrip("/") + "/v1/chat/completions"
        with httpx.Client(timeout=180.0) as cliente:
            r = cliente.post(url, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    else:
        cliente = anthropic.Anthropic(api_key=configuracion.ANTHROPIC_API_KEY)
        respuesta = cliente.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=mensajes,
        )
        return respuesta.content[0].text


async def chat_streaming(
    mensajes: list[dict],
    conexion: asyncpg.Connection,
    config: ConfigIA | None = None,
) -> AsyncIterator[str]:
    """
    Streaming hacia Anthropic o Ollama según la configuración del cliente.
    """
    cfg = config or ConfigIA()
    system_prompt = await construir_system_prompt(conexion)

    if cfg.proveedor == "ollama":
        async for chunk in _ollama_streaming(mensajes, system_prompt, cfg):
            yield chunk
    else:
        async for chunk in _anthropic_streaming(mensajes, system_prompt):
            yield chunk


async def _anthropic_streaming(
    mensajes: list[dict],
    system_prompt: str,
) -> AsyncIterator[str]:
    cliente = anthropic.Anthropic(api_key=configuracion.ANTHROPIC_API_KEY)
    with cliente.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system_prompt,
        messages=mensajes,
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk


async def _ollama_streaming(
    mensajes: list[dict],
    system_prompt: str,
    cfg: ConfigIA,
) -> AsyncIterator[str]:
    """Ollama API OpenAI-compatible con streaming."""
    payload = {
        "model": cfg.ollama_modelo,
        "stream": True,
        "messages": [{"role": "system", "content": system_prompt}, *mensajes],
    }
    url = cfg.ollama_url.rstrip("/") + "/v1/chat/completions"

    async with httpx.AsyncClient(timeout=120.0) as cliente:
        async with cliente.stream("POST", url, json=payload) as respuesta:
            respuesta.raise_for_status()
            async for linea in respuesta.aiter_lines():
                if not linea or linea == "data: [DONE]":
                    continue
                texto = linea.removeprefix("data: ").strip()
                if not texto:
                    continue
                try:
                    dato = json.loads(texto)
                    delta = dato.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, IndexError, KeyError):
                    continue


async def chat_simple(
    mensajes: list[dict],
    conexion: asyncpg.Connection,
    config: ConfigIA | None = None,
) -> str:
    """Llamada sin streaming — devuelve el texto completo."""
    cfg = config or ConfigIA()
    system_prompt = await construir_system_prompt(conexion)

    if cfg.proveedor == "ollama":
        payload = {
            "model": cfg.ollama_modelo,
            "stream": False,
            "messages": [{"role": "system", "content": system_prompt}, *mensajes],
        }
        url = cfg.ollama_url.rstrip("/") + "/v1/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as cliente:
            r = await cliente.post(url, json=payload)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    else:
        cliente = anthropic.Anthropic(api_key=configuracion.ANTHROPIC_API_KEY)
        respuesta = cliente.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=mensajes,
        )
        return respuesta.content[0].text
