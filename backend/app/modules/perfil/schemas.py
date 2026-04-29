"""
Schemas Pydantic para el módulo Mi Perfil.
"""

from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class SbuPrincipal(str, Enum):
    certification = "Certification"
    technical_consulting = "Technical Consulting"
    esg_solutions = "ESG Solutions"
    training = "Training"
    rbs = "Responsible Business Services"
    second_party = "Second Party"


class UnidadObjetivo(str, Enum):
    eur = "EUR"
    pct = "PCT"
    ops = "OPS"
    cuentas = "CUENTAS"


# ── Perfil ────────────────────────────────────────────────────────────────────

class PerfilRead(BaseModel):
    usuario_id: UUID
    email: str
    nombre_completo: str
    rol: str
    telefono: str | None
    zona: str | None
    sbu_principal: str | None
    avatar_url: str | None
    manager_id: UUID | None


class PerfilUpdate(BaseModel):
    nombre_completo: str | None = Field(default=None, min_length=2, max_length=150)
    telefono: str | None = Field(default=None, max_length=30)
    zona: str | None = Field(default=None, max_length=100)
    sbu_principal: SbuPrincipal | None = None
    avatar_url: str | None = Field(default=None, max_length=500)


class PerfilStats(BaseModel):
    pipeline_activo: Decimal
    win_rate: Decimal
    oportunidades_abiertas: int
    oportunidades_ganadas: int
    oportunidades_perdidas: int
    ticket_medio: Decimal


# ── Objetivos ─────────────────────────────────────────────────────────────────

class ObjetivoRead(BaseModel):
    id: UUID
    nombre: str
    valor_actual: Decimal
    valor_meta: Decimal
    unidad: str
    periodo: str
    progreso_pct: float


class ObjetivoCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    valor_actual: Decimal = Field(default=Decimal("0"), ge=0)
    valor_meta: Decimal = Field(..., gt=0)
    unidad: UnidadObjetivo
    periodo: str = Field(..., min_length=4, max_length=20)


class ObjetivoUpdate(BaseModel):
    valor_actual: Decimal = Field(..., ge=0)


# ── Notificaciones ────────────────────────────────────────────────────────────

class NotificacionesConfig(BaseModel):
    alertas_pipeline: bool
    briefing_diario: bool
    alerta_win_rate: bool
    hora_briefing: str  # "HH:MM"
    umbral_win_rate: Decimal
    voz_tts: str
    duracion_podcast_min: int


class NotificacionesUpdate(BaseModel):
    alertas_pipeline: bool | None = None
    briefing_diario: bool | None = None
    alerta_win_rate: bool | None = None
    hora_briefing: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    umbral_win_rate: Decimal | None = Field(default=None, ge=0, le=100)
    voz_tts: str | None = Field(default=None, max_length=50)
    duracion_podcast_min: int | None = Field(default=None, ge=1, le=30)
