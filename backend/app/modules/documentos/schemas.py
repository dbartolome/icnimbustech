"""
Schemas Pydantic para el módulo Documentos.
"""

from uuid import UUID

from pydantic import BaseModel


class DocumentoRead(BaseModel):
    id: UUID
    nombre_original: str
    tipo_mime: str | None
    tamaño_bytes: int | None
    oportunidad_id: UUID | None
    oportunidad_nombre: str | None
    cuenta_id: UUID | None = None
    cuenta_nombre: str | None = None
    creado_en: str
    tiene_transcripcion: bool = False


class DocumentoCuentaRead(BaseModel):
    id: UUID
    nombre_original: str
    tipo_mime: str | None
    tamaño_bytes: int | None
    creado_en: str
    tiene_texto: bool = False
