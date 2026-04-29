"""
Schemas Pydantic del módulo Seguimientos.
"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

TipoSeguimiento = Literal["recordatorio", "proximo_paso", "cadencia"]
EstadoSeguimiento = Literal["pendiente", "completado", "cancelado"]


class SeguimientoCrear(BaseModel):
    oportunidad_id: UUID | None = None
    cuenta_id: UUID | None = None
    usuario_id: UUID | None = None
    tipo: TipoSeguimiento = "proximo_paso"
    titulo: str = Field(min_length=1, max_length=300)
    descripcion: str | None = None
    fecha_vencimiento: date

    @model_validator(mode="after")
    def validar_destino(self) -> "SeguimientoCrear":
        if self.oportunidad_id is None and self.cuenta_id is None:
            raise ValueError("Debes indicar oportunidad_id o cuenta_id.")
        return self


class SeguimientoActualizar(BaseModel):
    tipo: TipoSeguimiento | None = None
    titulo: str | None = Field(default=None, min_length=1, max_length=300)
    descripcion: str | None = None
    fecha_vencimiento: date | None = None
    estado: EstadoSeguimiento | None = None


class SeguimientoRespuesta(BaseModel):
    id: UUID
    oportunidad_id: UUID | None
    cuenta_id: UUID | None
    usuario_id: UUID
    creado_por: UUID
    tipo: TipoSeguimiento
    titulo: str
    descripcion: str | None
    fecha_vencimiento: date
    estado: EstadoSeguimiento
    completado_en: datetime | None
    creado_en: datetime
    actualizado_en: datetime


class SeguimientoListaRespuesta(BaseModel):
    datos: list[SeguimientoRespuesta]
