"""Schemas Pydantic para objetivos comerciales."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ObjetivoComercialCreate(BaseModel):
    cuenta_id: UUID | None = None
    oportunidad_id: UUID | None = None
    tipo_objetivo: str = Field(default="cierre", max_length=40)
    titulo: str = Field(..., min_length=3, max_length=260)
    descripcion: str | None = None
    prioridad: int = Field(default=3, ge=1, le=5)
    fecha_objetivo: date | None = None


class ObjetivoComercialUpdate(BaseModel):
    titulo: str | None = Field(default=None, min_length=3, max_length=260)
    descripcion: str | None = None
    prioridad: int | None = Field(default=None, ge=1, le=5)
    estado: str | None = Field(default=None, max_length=30)
    fecha_objetivo: date | None = None
    score_impacto: Decimal | None = None
    score_confianza: Decimal | None = None


class ObjetivoComercialRead(BaseModel):
    id: UUID
    usuario_id: UUID
    cuenta_id: UUID | None
    cuenta_nombre: str | None = None
    oportunidad_id: UUID | None
    oportunidad_nombre: str | None = None
    tipo_objetivo: str
    origen: str
    titulo: str
    descripcion: str | None
    prioridad: int
    estado: str
    fecha_objetivo: date | None
    score_impacto: Decimal
    score_confianza: Decimal
    cross_sell_ref: str | None
    metadatos: dict
    creado_en: str
    actualizado_en: str


class ObjetivoSugerenciaRead(BaseModel):
    oportunidad_id: UUID
    oportunidad_nombre: str
    cuenta_id: UUID | None
    cuenta_nombre: str | None
    tipo_objetivo: str
    titulo: str
    descripcion: str
    prioridad: int
    score_impacto: Decimal
    score_confianza: Decimal
    cross_sell_ref: str | None


class ObjetivoDetalleRead(BaseModel):
    objetivo: ObjetivoComercialRead
    artefactos: list[dict]

