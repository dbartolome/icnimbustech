"""
Lógica de negocio del módulo Voice Studio.
Genera un script de briefing comercial para lectura en voz alta.
"""

from app.modules.ia.proveedores import PROVEEDORES_EXTERNOS, proveedor_externo_configurado
from app.modules.ia.servicio import ConfigIA, llamar_ia

SYSTEM_PROMPT_BRIEFING = """Eres un experto en comunicación comercial de SGS España.
Tu misión es generar briefings de audio profesionales y concisos para el equipo directivo.

ESTILO:
- Lenguaje ejecutivo, directo y claro
- Estructura: apertura, situación actual, puntos clave, cierre con acción
- Duración objetivo: 2-3 minutos de lectura (300-450 palabras)
- Tono profesional pero cercano
- Usa cifras concretas y porcentajes
- Responde SIEMPRE en español de España
- NO uses markdown, asteriscos ni símbolos — solo texto plano para lectura fluida
"""

PROMPT_BRIEFING = """Genera un briefing de voz para el equipo directivo de SGS España BA con estos datos del pipeline comercial:

SITUACIÓN ACTUAL:
- Pipeline activo: 22,5 millones de euros
- Importe cerrado ganado: 3,2 millones de euros
- Win Rate global: 82,6%
- Oportunidades activas: 3.543
- Ticket medio ganado: 7.200 euros
- Equipo comercial: 81 personas activas

PRODUCTOS DESTACADOS:
- IDI Proyectos: win rate 98,1% — producto líder en conversión
- ISO 9001:2015: 671.000 euros ganados — mayor volumen del portfolio
- CXM Audits: win rate 85,7% — 571.000 euros ganados
- IFS Food V8: win rate 70,8% — área de mejora identificada

TOP COMERCIALES:
- Ana María Silva: 738.000 euros ganados, WR 68,2%
- Rocío Carolina García: 562.000 euros, WR 100%
- Fernando Armenteros: 504.000 euros, WR 100%

CONTEXTO:
- Fecha del briefing: hoy
- Período analizado: pipeline acumulado 2024-2025

El briefing debe ser fluido para lectura en voz alta, sin pausas artificiales ni marcadores de formato."""


async def generar_script_briefing(foco: str = "general", config: ConfigIA | None = None) -> str:
    """
    Genera el script del briefing usando la IA configurada (Anthropic o Ollama).
    foco: 'general' | 'productos' | 'equipo' | 'pipeline'
    """
    cfg = config or ConfigIA()
    if cfg.proveedor in PROVEEDORES_EXTERNOS and not proveedor_externo_configurado(cfg.proveedor):
        raise ValueError(f"API key no configurada para proveedor '{cfg.proveedor}'.")

    prompt = PROMPT_BRIEFING
    if foco == "productos":
        prompt += "\n\nFoco especial en el análisis de productos y normas — profundiza en el win rate por producto."
    elif foco == "equipo":
        prompt += "\n\nFoco especial en el rendimiento del equipo comercial — destaca a los mejores y oportunidades de mejora."
    elif foco == "pipeline":
        prompt += "\n\nFoco especial en el estado del funnel y las etapas con más volumen en riesgo."

    return await llamar_ia(
        mensajes=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT_BRIEFING,
        config=cfg,
        max_tokens=800,
    )
