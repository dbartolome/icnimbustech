"""
Schemas del módulo Scoring.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ScoringRespuesta(BaseModel):
    oportunidad_id: UUID
    score: int = Field(ge=0, le=100)
    factores: dict
    calculado_en: datetime


class ScoringCriticoItem(BaseModel):
    oportunidad_id: UUID
    nombre: str
    cuenta_nombre: str | None
    score: int = Field(ge=0, le=100)
    etapa: str
    importe: float


class ScoringFeedbackCrear(BaseModel):
    util: bool
    nota: str | None = Field(default=None, max_length=1000)


class ScoringFeedbackRespuesta(BaseModel):
    oportunidad_id: UUID
    feedback: dict
