"""
Schemas Pydantic para el módulo Informes PDF.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from app.config import configuracion
from app.modules.ia.proveedores import PROVEEDOR_LOCAL

TIPOS_INFORME = {
    "ejecutivo_mensual": "Informe ejecutivo mensual",
    "analisis_comercial": "Análisis de comercial",
    "propuesta_cliente": "Propuesta para cliente",
    "revision_pipeline": "Revisión de pipeline",
}


class SolicitudInforme(BaseModel):
    tipo: str = Field(..., pattern="^(ejecutivo_mensual|analisis_comercial|propuesta_cliente|revision_pipeline)$")
    periodo: str | None = Field(default=None, max_length=50)
    destinatario: str | None = Field(default=None, max_length=150)
    contexto: str | None = Field(default=None, max_length=1000)
    proveedor: str = PROVEEDOR_LOCAL
    ollama_url: str = configuracion.OLLAMA_URL
    ollama_modelo: str = configuracion.OLLAMA_MODEL_DEFAULT


class InformeResumen(BaseModel):
    id: UUID
    tipo: str
    titulo: str
    periodo: str | None
    destinatario: str | None
    estado: str
    paginas: int | None
    creado_en: str
    completado_en: str | None


class RespuestaJob(BaseModel):
    job_id: str
    estado: str
    mensaje: str


class EstadoJob(BaseModel):
    job_id: str
    estado: str
    progreso: int          # 0-100
    paso_actual: str | None
    indice: list | None
