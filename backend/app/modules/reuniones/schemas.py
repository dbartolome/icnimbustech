"""
Schemas del módulo Reuniones.
"""

from pydantic import BaseModel


class FichaReunionRespuesta(BaseModel):
    cuenta: dict
    investigacion: dict
    propuesta: dict
    pipeline: dict
    seguimientos: list[dict]
    score_medio: int
    materiales: dict


class PreguntasReunionRespuesta(BaseModel):
    preguntas: list[str]
