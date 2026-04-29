"""
Registro y utilidades de proveedores IA.

Objetivo:
- Separar claramente IA externa (research) de IA local (operación).
- Centralizar resolución de API keys por proveedor.
"""

import json
from urllib.parse import urlparse

import asyncpg

from app.config import configuracion

PROVEEDORES_EXTERNOS = (
    "anthropic",
    "openai",
    "gemini",
)

PROVEEDOR_LOCAL = "ollama"
PROVEEDORES_DEEP_RESEARCH_SOPORTADOS = {"anthropic", "openai", "gemini", "ollama"}
SERVICIOS_IA_OPERATIVOS = ("copilot", "voice", "informes", "decks", "cross_selling", "importacion")


def normalizar_proveedor(valor: str | None, por_defecto: str) -> str:
    proveedor = (valor or por_defecto).strip().lower()
    return proveedor or por_defecto


_HOSTNAMES_DOCKER_INTERNOS = {"localhost", "127.0.0.1", "0.0.0.0", "ollama", "host.docker.internal"}

def _es_ip_privada(host: str) -> bool:
    """True si el host es una dirección no enrutable desde el VPS de producción."""
    if host in _HOSTNAMES_DOCKER_INTERNOS:
        return True
    # Rangos RFC-1918 (LAN dev: 192.168.x.x, 10.x.x.x, 172.16-31.x.x)
    partes = host.split(".")
    if len(partes) == 4:
        try:
            p = [int(x) for x in partes]
            if p[0] == 10:
                return True
            if p[0] == 172 and 16 <= p[1] <= 31:
                return True
            if p[0] == 192 and p[1] == 168:
                return True
        except ValueError:
            pass
    return False


def normalizar_ollama_url_operacional(url: str | None) -> str:
    """
    En producción (Docker), localhost/127.0.0.1 y cualquier IP privada de LAN
    apuntan al dev local, no al servicio Ollama del VPS.
    Se fuerza siempre la URL interna Docker configurada en OLLAMA_URL.
    """
    candidata = (url or "").strip().rstrip("/") or configuracion.OLLAMA_URL
    try:
        parsed = urlparse(candidata)
        host = (parsed.hostname or "").lower()
        if _es_ip_privada(host):
            return configuracion.OLLAMA_URL.rstrip("/")
    except Exception:
        return configuracion.OLLAMA_URL.rstrip("/")
    return candidata


_proveedor_research_activo = normalizar_proveedor(
    configuracion.IA_RESEARCH_PROVIDER, "anthropic"
)
_api_keys_runtime: dict[str, str] = {}
_modelos_research_runtime: dict[str, str] = {}
_ollama_url_research_runtime: str = normalizar_ollama_url_operacional(configuracion.OLLAMA_URL)
_operacional_configs_runtime: dict[str, dict[str, str]] = {
    servicio: {
        "proveedor": PROVEEDOR_LOCAL,
        "ollama_url": normalizar_ollama_url_operacional(configuracion.OLLAMA_URL),
        "ollama_modelo": configuracion.OLLAMA_MODEL_DEFAULT,
    }
    for servicio in SERVICIOS_IA_OPERATIVOS
}


def obtener_api_key_externa(proveedor: str) -> str:
    p = normalizar_proveedor(proveedor, "anthropic")
    if _api_keys_runtime.get(p):
        return _api_keys_runtime[p]
    if p == "anthropic":
        return configuracion.ANTHROPIC_API_KEY
    if p == "openai":
        return configuracion.OPENAI_API_KEY
    if p == "gemini":
        return configuracion.GEMINI_API_KEY
    return ""


def proveedor_externo_configurado(proveedor: str) -> bool:
    return bool(obtener_api_key_externa(proveedor))


def proveedor_research_configurado(proveedor: str) -> bool:
    p = normalizar_proveedor(proveedor, "anthropic")
    if p == PROVEEDOR_LOCAL:
        return True
    return proveedor_externo_configurado(p)


def modelo_por_defecto_research(proveedor: str) -> str:
    p = normalizar_proveedor(proveedor, "anthropic")
    if p == PROVEEDOR_LOCAL:
        return configuracion.OLLAMA_MODEL_DEFAULT
    if p == "anthropic":
        return configuracion.IA_RESEARCH_MODEL_ANTHROPIC or configuracion.IA_RESEARCH_MODEL
    if p == "openai":
        return configuracion.IA_RESEARCH_MODEL_OPENAI or configuracion.IA_RESEARCH_MODEL
    if p == "gemini":
        return configuracion.IA_RESEARCH_MODEL_GEMINI or configuracion.IA_RESEARCH_MODEL
    return configuracion.IA_RESEARCH_MODEL


def obtener_modelo_research(proveedor: str) -> str:
    p = normalizar_proveedor(proveedor, "anthropic")
    return _modelos_research_runtime.get(p) or modelo_por_defecto_research(p)


def obtener_proveedor_research_activo() -> str:
    return _proveedor_research_activo


def obtener_ollama_url_research() -> str:
    return normalizar_ollama_url_operacional(_ollama_url_research_runtime)


def establecer_proveedor_research_activo(proveedor: str) -> str:
    global _proveedor_research_activo
    p = normalizar_proveedor(proveedor, "anthropic")
    _proveedor_research_activo = p
    return _proveedor_research_activo


def establecer_config_research_runtime(
    proveedor: str,
    modelo: str | None = None,
    api_key: str | None = None,
    ollama_url: str | None = None,
) -> str:
    global _ollama_url_research_runtime
    p = establecer_proveedor_research_activo(proveedor)
    if modelo is not None and modelo.strip():
        _modelos_research_runtime[p] = modelo.strip()
    if p == PROVEEDOR_LOCAL:
        _api_keys_runtime.pop(p, None)
    elif api_key is not None and api_key.strip():
        _api_keys_runtime[p] = api_key.strip()
    if ollama_url is not None and ollama_url.strip():
        _ollama_url_research_runtime = normalizar_ollama_url_operacional(ollama_url)
    return p


def estado_proveedores() -> dict:
    proveedores_research = [*PROVEEDORES_EXTERNOS, PROVEEDOR_LOCAL]
    externos = {
        p: {
            "configurado": proveedor_research_configurado(p),
            "deep_research_soportado": p in PROVEEDORES_DEEP_RESEARCH_SOPORTADOS,
            "modelo_activo": obtener_modelo_research(p),
            "api_key_runtime": bool(_api_keys_runtime.get(p)),
        }
        for p in proveedores_research
    }
    return {
        "research": {
            "proveedor_por_defecto_env": normalizar_proveedor(
                configuracion.IA_RESEARCH_PROVIDER, "anthropic"
            ),
            "proveedor_activo": obtener_proveedor_research_activo(),
            "modelo_por_defecto": configuracion.IA_RESEARCH_MODEL,
            "ollama_url_por_defecto": configuracion.OLLAMA_URL,
            "ollama_url_activa": obtener_ollama_url_research(),
            "externos": externos,
            "persistencia": "db",
        },
        "operacional": {
            "proveedor_fijo": PROVEEDOR_LOCAL,
            "ollama_url_por_defecto": configuracion.OLLAMA_URL,
            "ollama_modelo_por_defecto": configuracion.OLLAMA_MODEL_DEFAULT,
            "configs": obtener_configs_operacionales(),
        },
    }


def obtener_configs_operacionales() -> dict[str, dict[str, str]]:
    return {
        k: {
            "proveedor": v["proveedor"],
            "ollama_url": v["ollama_url"],
            "ollama_modelo": v["ollama_modelo"],
        }
        for k, v in _operacional_configs_runtime.items()
    }


def establecer_config_operacional_runtime(
    servicio: str,
    ollama_url: str | None = None,
    ollama_modelo: str | None = None,
) -> dict[str, str]:
    s = (servicio or "").strip().lower()
    if s not in SERVICIOS_IA_OPERATIVOS:
        raise ValueError(f"Servicio IA operativo no soportado: {servicio}")

    cfg = _operacional_configs_runtime[s]
    cfg["proveedor"] = PROVEEDOR_LOCAL
    if ollama_url and ollama_url.strip():
        cfg["ollama_url"] = normalizar_ollama_url_operacional(ollama_url)
    if ollama_modelo and ollama_modelo.strip():
        cfg["ollama_modelo"] = ollama_modelo.strip()
    return cfg


async def _asegurar_tabla_ia_configuracion(conexion: asyncpg.Connection) -> None:
    await conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS ia_configuracion (
            id SMALLINT PRIMARY KEY CHECK (id = 1),
            research_proveedor VARCHAR(50) NOT NULL DEFAULT 'anthropic',
            research_ollama_url TEXT NOT NULL DEFAULT 'http://localhost:11434',
            research_modelos JSONB NOT NULL DEFAULT '{}'::jsonb,
            research_api_keys JSONB NOT NULL DEFAULT '{}'::jsonb,
            operational_configs JSONB NOT NULL DEFAULT '{}'::jsonb,
            actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    await conexion.execute(
        """
        INSERT INTO ia_configuracion (id, research_ollama_url)
        VALUES (1, $1)
        ON CONFLICT (id) DO NOTHING
        """,
        configuracion.OLLAMA_URL,
    )
    await conexion.execute(
        """
        ALTER TABLE ia_configuracion
        ADD COLUMN IF NOT EXISTS operational_configs JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )


async def cargar_config_research_desde_db(pool: asyncpg.Pool) -> None:
    """
    Carga la configuración research persistida y la aplica en runtime.
    Si la tabla no existe todavía, mantiene valores por defecto de entorno.
    """
    global _proveedor_research_activo, _ollama_url_research_runtime
    try:
        async with pool.acquire() as conexion:
            await _asegurar_tabla_ia_configuracion(conexion)
            fila = await conexion.fetchrow(
                """
                SELECT research_proveedor, research_ollama_url, research_modelos, research_api_keys, operational_configs
                FROM ia_configuracion
                WHERE id = 1
                """
            )
    except asyncpg.UndefinedTableError:
        return

    if not fila:
        return

    _proveedor_research_activo = normalizar_proveedor(
        fila["research_proveedor"], _proveedor_research_activo
    )
    _ollama_url_research_runtime = normalizar_ollama_url_operacional(
        fila["research_ollama_url"] or configuracion.OLLAMA_URL
    )

    modelos = fila["research_modelos"] or {}
    if isinstance(modelos, str):
        try:
            modelos = json.loads(modelos)
        except json.JSONDecodeError:
            modelos = {}

    keys = fila["research_api_keys"] or {}
    if isinstance(keys, str):
        try:
            keys = json.loads(keys)
        except json.JSONDecodeError:
            keys = {}

    _modelos_research_runtime.clear()
    _modelos_research_runtime.update(
        {normalizar_proveedor(k, "anthropic"): str(v).strip() for k, v in dict(modelos).items() if str(v).strip()}
    )

    _api_keys_runtime.clear()
    _api_keys_runtime.update(
        {normalizar_proveedor(k, "anthropic"): str(v).strip() for k, v in dict(keys).items() if str(v).strip()}
    )

    operacionales = fila["operational_configs"] or {}
    if isinstance(operacionales, str):
        try:
            operacionales = json.loads(operacionales)
        except json.JSONDecodeError:
            operacionales = {}

    for servicio in SERVICIOS_IA_OPERATIVOS:
        valor = dict(operacionales).get(servicio) or {}
        if not isinstance(valor, dict):
            continue
        _operacional_configs_runtime[servicio] = {
            "proveedor": PROVEEDOR_LOCAL,
            "ollama_url": normalizar_ollama_url_operacional(
                str(valor.get("ollama_url") or configuracion.OLLAMA_URL)
            ),
            "ollama_modelo": str(valor.get("ollama_modelo") or configuracion.OLLAMA_MODEL_DEFAULT).strip(),
        }


async def guardar_config_research_en_db(conexion: asyncpg.Connection) -> None:
    """
    Persiste el estado runtime actual de research.
    """
    await _asegurar_tabla_ia_configuracion(conexion)
    await conexion.execute(
        """
        INSERT INTO ia_configuracion (
            id, research_proveedor, research_ollama_url, research_modelos, research_api_keys, operational_configs, actualizado_en
        ) VALUES (1, $1, $2, $3::jsonb, $4::jsonb, $5::jsonb, now())
        ON CONFLICT (id) DO UPDATE SET
            research_proveedor = EXCLUDED.research_proveedor,
            research_ollama_url = EXCLUDED.research_ollama_url,
            research_modelos = EXCLUDED.research_modelos,
            research_api_keys = EXCLUDED.research_api_keys,
            operational_configs = EXCLUDED.operational_configs,
            actualizado_en = now()
        """,
        _proveedor_research_activo,
        _ollama_url_research_runtime,
        json.dumps(_modelos_research_runtime),
        json.dumps(_api_keys_runtime),
        json.dumps(obtener_configs_operacionales()),
    )


async def guardar_config_operacional_en_db(conexion: asyncpg.Connection) -> None:
    await guardar_config_research_en_db(conexion)
