"""
Schemas Pydantic para el módulo de generación de decks de visita.
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import configuracion
from app.modules.ia.proveedores import PROVEEDOR_LOCAL


class TipoDeck(str, Enum):
    primera_visita = "primera_visita"
    seguimiento_oferta = "seguimiento_oferta"
    upselling = "upselling"
    propuesta_tecnica = "propuesta_tecnica"


class EstadoJob(str, Enum):
    pendiente = "pendiente"
    generando_contenido = "generando_contenido"
    construyendo_slides = "construyendo_slides"
    completado = "completado"
    error = "error"


class SolicitudDeck(BaseModel):
    empresa: str = Field(..., min_length=2, max_length=200)
    sector: str = Field(..., min_length=2, max_length=100)
    norma: str = Field(..., min_length=2, max_length=100)
    tipo: TipoDeck
    objetivo_visita: str = Field(..., min_length=5, max_length=500)
    notas_adicionales: str = Field(default="", max_length=1000)
    num_slides: int = Field(default=10, ge=6, le=15)
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT
    # Trazabilidad: vincula el deck a la cuenta donde se genera
    cuenta_id: UUID | None = None


class RespuestaJob(BaseModel):
    job_id: str
    estado: EstadoJob
    progreso: int  # 0-100
    mensaje: str
    archivo: str | None = None  # nombre del archivo cuando está listo
