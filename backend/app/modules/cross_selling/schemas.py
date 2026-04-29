from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
import uuid
import datetime


class CrossSellingItem(BaseModel):
    id: uuid.UUID
    account_name: str
    sbu: Optional[str] = None
    servicio_actual: Optional[str] = None
    ops_abiertas: Optional[int] = None
    oportunidades_top: Optional[str] = None
    sector_osint: Optional[str] = None
    trigger_activador: Optional[str] = None
    confianza: Optional[str] = None
    ranking_accionable: Optional[int] = None
    mensaje_comercial: Optional[str] = None
    preguntas_discovery: Optional[str] = None
    creado_en: datetime.datetime

    model_config = {"from_attributes": True}


class CrossSellingListado(BaseModel):
    total: int
    datos: list[CrossSellingItem]
