"""
Clase base para todos los agentes IA del sistema.

Reglas:
- Los agentes NO se llaman entre sí directamente — pasa por el Orchestrator.
- Los agentes SÍ pueden llamar skills directamente.
- run() es el único punto de entrada público.
- Cada agente define su propio proveedor de IA (forzado, no configurable por el usuario).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import asyncpg

from app.config import configuracion


@dataclass
class ResultadoAgente:
    exito: bool
    datos: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ConfigAgente:
    """
    Configuración de IA para un agente específico.
    El proveedor lo fija el agente, no el usuario.
    """
    proveedor: str                          # "anthropic" | "ollama"
    ollama_url: str = ""
    ollama_modelo: str = ""
    temperatura: float = 0.2
    max_tokens: int = 2000
    usar_web_search: bool = False

    def __post_init__(self):
        if not self.ollama_url:
            self.ollama_url = configuracion.OLLAMA_URL
        if not self.ollama_modelo:
            self.ollama_modelo = configuracion.OLLAMA_MODEL_DEFAULT
    temperatura: float = 0.2
    max_tokens: int = 2000
    usar_web_search: bool = False           # solo Agente 1


class AgentBase(ABC):
    """
    Interfaz común para todos los agentes del sistema multi-agente SGS.
    """

    nombre: str = "agente_base"

    @abstractmethod
    async def run(
        self,
        entrada: dict[str, Any],
        conexion: asyncpg.Connection,
    ) -> ResultadoAgente:
        """
        Ejecuta el agente. Siempre devuelve ResultadoAgente.
        Nunca lanza excepciones — los errores van en ResultadoAgente.exito=False.
        """
        ...

    async def _actualizar_estado_db(
        self,
        tabla: str,
        job_id: str,
        estado: str,
        conexion: asyncpg.Connection,
        **campos_extra: Any,
    ) -> None:
        """Actualiza el estado de un job en DB de forma genérica."""
        sets = ["estado = $2"]
        params: list[Any] = [job_id, estado]
        n = 3

        for campo, valor in campos_extra.items():
            sets.append(f"{campo} = ${n}")
            params.append(valor)
            n += 1

        sets.append(f"actualizado_en = now()")

        await conexion.execute(
            f"UPDATE {tabla} SET {', '.join(sets)} WHERE id = $1",
            *params,
        )
