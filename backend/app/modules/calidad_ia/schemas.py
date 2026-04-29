"""
Schemas del módulo Calidad IA.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

TipoEntregable = Literal["pdf", "pptx", "deck", "briefing"]


class CheckCalidad(BaseModel):
    ok: bool
    msg: str
    bloquea: bool = False


class ValidacionCalidadRespuesta(BaseModel):
    cuenta_id: UUID
    tipo_entregable: TipoEntregable
    valido: bool
    nivel: Literal["ok", "warning", "error"]
    checks: list[CheckCalidad]


class ForzarExportacionCrear(BaseModel):
    tipo_entregable: TipoEntregable
    motivo: str | None = None
