"""
Schemas del módulo de artefactos IA.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class FuenteVersionCrear(BaseModel):
    fuente_artefacto_id: UUID | None = None
    fuente_tipo: str = "artefacto"
    fuente_ref: str | None = None
    peso: float | None = None


class VersionArtefactoCrear(BaseModel):
    prompt: str | None = None
    resultado_texto: str | None = None
    resultado_json: dict = Field(default_factory=dict)
    storage_key: str | None = None
    modelo: str | None = None
    plantilla_id: UUID | None = None
    metadatos: dict = Field(default_factory=dict)
    fuentes: list[FuenteVersionCrear] = Field(default_factory=list)


class ArtefactoVersionRead(BaseModel):
    id: UUID
    artefacto_id: UUID
    version_num: int
    es_actual: bool
    prompt: str | None
    resultado_texto: str | None
    resultado_json: dict
    storage_key: str | None
    modelo: str | None
    plantilla_id: UUID | None
    metadatos: dict
    creado_en: str


class ArtefactoRead(BaseModel):
    id: UUID
    tipo: str
    subtipo: str
    entidad_tipo: str | None
    entidad_id: UUID | None
    cuenta_id: UUID | None
    usuario_id: UUID
    titulo: str
    estado: str
    version_actual: int
    origen_tabla: str | None = None
    origen_id: str | None = None
    metadatos: dict
    creado_en: str
    actualizado_en: str
    eliminado_en: str | None = None


class ArtefactoDetalleRead(BaseModel):
    artefacto: ArtefactoRead
    version_actual: ArtefactoVersionRead | None = None
    total_versiones: int = 0
