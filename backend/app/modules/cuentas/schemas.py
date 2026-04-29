"""
Schemas Pydantic para el módulo Mis Cuentas.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class OportunidadEnCuenta(BaseModel):
    id: UUID
    nombre: str
    importe: Decimal
    etapa: str
    fecha_creacion: str
    fecha_decision: str | None


class CuentaResumen(BaseModel):
    id: UUID
    nombre: str
    total_oportunidades: int
    oportunidades_activas: int
    pipeline_activo: Decimal
    importe_ganado: Decimal
    win_rate: Decimal
    ultima_actividad: str | None


class CuentaDetalle(BaseModel):
    id: UUID
    nombre: str
    total_oportunidades: int
    oportunidades_activas: int
    pipeline_activo: Decimal
    importe_ganado: Decimal
    win_rate: Decimal
    oportunidades: list[OportunidadEnCuenta]


class ListaCuentas(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    datos: list[CuentaResumen]


# ── Clientes (vista global — manager/admin) ───────────────────────────────

class OportunidadEnCliente(BaseModel):
    id: UUID
    nombre: str
    importe: Decimal
    etapa: str
    fecha_creacion: str
    fecha_decision: str | None
    propietario_nombre: str | None
    sbu_nombre: str | None
    producto_nombre: str | None


class ClienteResumen(BaseModel):
    id: UUID
    nombre: str
    total_oportunidades: int
    oportunidades_activas: int
    pipeline_activo: Decimal
    importe_ganado: Decimal
    win_rate: Decimal
    ultima_actividad: str | None
    comerciales: list[str]
    sbus: list[str]


class ClienteDetalle(BaseModel):
    id: UUID
    nombre: str
    total_oportunidades: int
    oportunidades_activas: int
    pipeline_activo: Decimal
    importe_ganado: Decimal
    win_rate: Decimal
    comerciales: list[str]
    sbus: list[str]
    oportunidades: list[OportunidadEnCliente]


class ListaClientes(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    datos: list[ClienteResumen]
