"""
Schemas Pydantic para el módulo Notas de Voz.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class NotaCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    transcripcion: str = Field(..., min_length=1)
    duracion_seg: int | None = Field(default=None, ge=1)
    oportunidad_id: UUID | None = None


class NotaRead(BaseModel):
    id: UUID
    titulo: str
    transcripcion: str
    duracion_seg: int | None
    oportunidad_id: UUID | None
    oportunidad_nombre: str | None
    creado_en: str
