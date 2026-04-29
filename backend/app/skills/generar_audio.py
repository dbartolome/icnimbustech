"""
Skill: generar_audio

Genera un script de briefing de audio personalizado para una cuenta específica,
usando los datos reales de su propuesta_comercial en DB.

A diferencia del Voice Studio genérico (datos hardcodeados), este script
habla de la empresa concreta, sus productos recomendados y sus escenarios reales.
"""

import json
import asyncpg
from uuid import UUID

from app.agents.base import ConfigAgente
from app.config import configuracion


def _parse_jsonb(valor, default):
    """Normaliza un campo JSONB que puede venir como dict/list, str JSON o None."""
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except (json.JSONDecodeError, ValueError):
            pass
    return default


def _limpiar_texto_audio(texto: str) -> str:
    """
    Limpia artefactos de markdown para devolver texto plano apto para TTS/UI.
    """
    if not texto:
        return ""
    limpio = texto.replace("**", "").replace("__", "").replace("```", "")
    return "\n".join(linea.strip() for linea in limpio.splitlines() if linea.strip()).strip()

_SYSTEM = """Eres un experto en comunicación comercial de SGS España.
Genera briefings de audio profesionales y concisos para el equipo comercial.

ESTILO:
- Lenguaje ejecutivo, directo y cercano
- Estructura: apertura con nombre de empresa, situación actual, productos recomendados, escenarios, próximos pasos
- Duración objetivo MVP: 45-70 segundos de lectura (110-160 palabras)
- Usa cifras concretas y porcentajes
- Responde en español de España
- NO uses markdown, asteriscos ni símbolos — solo texto plano fluido para lectura en voz alta
- Dirígete al comercial en segunda persona: "Tu próxima visita a...", "El escenario más probable para ti..."
"""


async def generar_audio_cuenta(
    cuenta_id: UUID,
    conexion: asyncpg.Connection,
    config: ConfigAgente | None = None,
    instrucciones_extra: str | None = None,
) -> str:
    """
    Genera un script de audio personalizado para una cuenta específica.
    Lee la propuesta_comercial más reciente de la DB.
    Usa Ollama local (datos confidenciales) o Anthropic si no hay Ollama configurado.
    """
    # 1. Leer propuesta comercial
    propuesta = await conexion.fetchrow(
        """
        SELECT pc.productos_recomendados, pc.escenario_optimista, pc.escenario_medio,
               pc.escenario_pesimista, pc.plan_de_accion, pc.argumentario_general,
               c.nombre AS nombre_cuenta,
               ie.sector, ie.num_empleados, ie.certificaciones_actuales, ie.pain_points
        FROM propuestas_comerciales pc
        JOIN cuentas c ON c.id = pc.cuenta_id
        LEFT JOIN investigaciones_empresa ie ON ie.id = pc.investigacion_id
        WHERE pc.cuenta_id = $1 AND pc.estado = 'completada'
        ORDER BY pc.creado_en DESC
        LIMIT 1
        """,
        cuenta_id,
    )

    if not propuesta:
        raise ValueError(f"Sin propuesta completada para la cuenta {cuenta_id}")

    # 2. Construir prompt con datos reales (normalizar JSONB → Python)
    productos = _parse_jsonb(propuesta["productos_recomendados"], [])
    productos_txt = ", ".join(
        p.get("producto", "") for p in productos[:3] if isinstance(p, dict)
    ) or "Por definir"

    esc_opt = _parse_jsonb(propuesta["escenario_optimista"], {})
    esc_med = _parse_jsonb(propuesta["escenario_medio"], {})
    plan = _parse_jsonb(propuesta["plan_de_accion"], [])
    primera_accion = plan[0].get("accion", "Contactar con el cliente") if plan and isinstance(plan[0], dict) else "Contactar con el cliente"

    certs_actuales = _parse_jsonb(propuesta["certificaciones_actuales"], [])
    certs_txt = ", ".join(certs_actuales) if isinstance(certs_actuales, list) else "Ninguna detectada"

    pain_points = _parse_jsonb(propuesta["pain_points"], [])
    pain_txt = pain_points[0] if isinstance(pain_points, list) and pain_points else "No identificados"

    bloque_plantilla = (
        f"\nINSTRUCCIONES DE PLANTILLA (PRIORITARIAS):\n{instrucciones_extra}\n"
        if instrucciones_extra
        else ""
    )

    prompt = f"""Genera un briefing de voz personalizado para el comercial de SGS España que va a visitar la empresa "{propuesta['nombre_cuenta']}".

DATOS DE LA EMPRESA:
- Sector: {propuesta['sector'] or 'No identificado'}
- Empleados: {propuesta['num_empleados'] or 'No disponible'}
- Certificaciones actuales: {certs_txt}
- Principal pain point detectado: {pain_txt}

PROPUESTA SGS PARA ESTA EMPRESA:
- Productos recomendados: {productos_txt}
- Escenario optimista: {esc_opt.get('importe', 0):,.0f}€ en {esc_opt.get('plazo_meses', 6)} meses ({esc_opt.get('probabilidad', 0)}% prob.)
- Escenario más probable: {esc_med.get('importe', 0):,.0f}€ en {esc_med.get('plazo_meses', 9)} meses ({esc_med.get('probabilidad', 0)}% prob.)
- Primera acción recomendada: {primera_accion}

ARGUMENTARIO BASE:
{propuesta['argumentario_general'] or 'No disponible'}
{bloque_plantilla}

Genera el briefing de audio en formato breve (máximo 160 palabras). Debe sonar natural al escucharlo, como si un colega experimentado te estuviera poniendo al día antes de entrar a la reunión."""

    return await _llamar_ia(prompt, config)


async def _llamar_ia(prompt: str, config: ConfigAgente | None) -> str:
    import httpx

    if config and config.proveedor == "ollama":
        base = config.ollama_url.rstrip("/")
        msgs = [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ]
        timeout = httpx.Timeout(45.0, connect=8.0)

        async with httpx.AsyncClient(timeout=timeout) as cliente:
            # 1. /v1/chat/completions (OpenAI-compatible)
            try:
                r = await cliente.post(base + "/v1/chat/completions", json={
                    "model": config.ollama_modelo, "stream": False, "max_tokens": 260, "messages": msgs,
                })
                if r.status_code != 404:
                    r.raise_for_status()
                    return _limpiar_texto_audio(r.json()["choices"][0]["message"]["content"])
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    raise

            # 2. /api/chat (nativo Ollama)
            try:
                r = await cliente.post(base + "/api/chat", json={
                    "model": config.ollama_modelo, "stream": False,
                    "messages": msgs, "options": {"num_predict": 260},
                })
                if r.status_code != 404:
                    r.raise_for_status()
                    return _limpiar_texto_audio(r.json().get("message", {}).get("content", ""))
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 404:
                    raise

            # 3. /api/generate (Ollama antiguo)
            r = await cliente.post(base + "/api/generate", json={
                "model": config.ollama_modelo, "stream": False,
                "system": _SYSTEM, "prompt": prompt, "options": {"num_predict": 260},
            })
            r.raise_for_status()
            return _limpiar_texto_audio(r.json().get("response", ""))

    # Por defecto: Anthropic
    import anthropic
    cliente = anthropic.Anthropic(api_key=configuracion.ANTHROPIC_API_KEY)
    respuesta = cliente.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=260,
        temperature=0.6,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return _limpiar_texto_audio(respuesta.content[0].text)
