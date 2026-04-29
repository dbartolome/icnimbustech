"""
Schemas del módulo Coaching.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class CoachingSesionRespuesta(BaseModel):
    id: UUID
    usuario_id: UUID
    cuenta_id: UUID | None
    tipo: Literal["analisis_notas", "plan_mejora", "feedback_pitch"]
    resultado: dict
    creado_en: datetime


class RecomendacionCoachingRespuesta(BaseModel):
    focos_semana: list[str]
    acciones: list[str]
    metricas_objetivo: dict
