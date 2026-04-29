"""Schemas Pydantic para el módulo Forecast."""

from uuid import UUID
from pydantic import BaseModel


class EscenarioForecast(BaseModel):
    m1: float
    m2: float
    m3: float
    total: float


class ForecastResult(BaseModel):
    usuario_id: str
    usuario_nombre: str
    mes_1: str
    mes_2: str
    mes_3: str
    pipeline_total: float
    pipeline_maduro: float
    baseline_mediana: float
    sbu_dominante: str | None
    wr_sbu: float
    pesimista: EscenarioForecast
    base: EscenarioForecast
    optimista: EscenarioForecast


class ForecastSnapshot(BaseModel):
    id: UUID
    usuario_id: UUID
    usuario_nombre: str
    snapshot_date: str
    mes_1: str
    mes_2: str
    mes_3: str
    pipeline_total: float
    pipeline_maduro: float
    baseline_mediana: float
    sbu_dominante: str | None
    wr_sbu: float
    pesimista_m1: float
    pesimista_m2: float
    pesimista_m3: float
    pesimista_total: float
    base_m1: float
    base_m2: float
    base_m3: float
    base_total: float
    optimista_m1: float
    optimista_m2: float
    optimista_m3: float
    optimista_total: float
    real_m1: float | None
    real_m2: float | None
    real_m3: float | None
    creado_en: str


class CrossSellQueueItem(BaseModel):
    id: UUID | None = None
    cuenta_nombre: str
    sbu_actual: str | None
    productos_won: str | None
    ops_abiertas: int
    pipeline_abierto: float
    oportunidades_top: str | None
    mensaje_comercial: str | None
    preguntas_discovery: str | None
    confianza: str | None
    score: float


class RealUpdate(BaseModel):
    mes: str   # "m1" | "m2" | "m3"
    importe: float


class ForecastEquipoItem(BaseModel):
    usuario_nombre: str
    pipeline_maduro: float
    baseline_mediana: float
    sbu_dominante: str | None
    pesimista_total: float
    base_total: float
    optimista_total: float


class ForecastEquipo(BaseModel):
    comerciales: list[ForecastEquipoItem]
    totales_pesimista: float
    totales_base: float
    totales_optimista: float
