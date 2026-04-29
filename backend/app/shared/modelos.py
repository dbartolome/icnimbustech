"""
Schemas Pydantic compartidos entre módulos.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModeloBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Oportunidad
# =============================================================================

class OportunidadResumen(ModeloBase):
    id: UUID
    nombre: str
    importe: Decimal
    etapa: str
    fecha_creacion: date
    fecha_decision: date | None = None


class OportunidadDetalle(OportunidadResumen):
    external_id: str | None = None
    linea_negocio: str | None = None
    canal_venta: str | None = None
    tipo: str | None = None
    creado_en: datetime
    actualizado_en: datetime


class OportunidadCrear(ModeloBase):
    nombre: str
    importe: Decimal
    etapa: str
    fecha_creacion: date
    fecha_decision: date | None = None
    linea_negocio: str | None = None
    canal_venta: str | None = None
    tipo: str | None = None
    cuenta_id: UUID | None = None
    propietario_id: UUID | None = None
    sbu_id: UUID | None = None
    producto_id: UUID | None = None


class OportunidadActualizar(ModeloBase):
    nombre: str | None = None
    importe: Decimal | None = None
    etapa: str | None = None
    fecha_creacion: date | None = None
    fecha_decision: date | None = None
    linea_negocio: str | None = None
    canal_venta: str | None = None


# =============================================================================
# Paginación
# =============================================================================

class RespuestaPaginada(ModeloBase):
    total: int
    pagina: int
    por_pagina: int
    datos: list
