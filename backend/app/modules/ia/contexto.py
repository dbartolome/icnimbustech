"""
Utilidades para validar y resolver el contexto de ejecución de IA.

Contexto soportado:
- cuenta / cliente (alias de cuenta)
- producto
- oportunidad
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import asyncpg

TIPOS_CONTEXTO_IA = {"cuenta", "cliente", "producto", "oportunidad"}


@dataclass(frozen=True)
class ContextoIA:
    tipo: str
    contexto_id: UUID
    cuenta_id: UUID | None
    nombre: str


def normalizar_tipo_contexto(tipo: str | None) -> str:
    valor = (tipo or "cuenta").strip().lower()
    if valor not in TIPOS_CONTEXTO_IA:
        permitidos = ", ".join(sorted(TIPOS_CONTEXTO_IA))
        raise ValueError(f"contexto_tipo inválido: {valor}. Permitidos: {permitidos}.")
    return valor


async def resolver_contexto(
    conexion: asyncpg.Connection,
    *,
    contexto_tipo: str | None,
    contexto_id: UUID | None,
    cuenta_id_por_defecto: UUID | None = None,
) -> ContextoIA:
    tipo = normalizar_tipo_contexto(contexto_tipo)
    if contexto_id is None:
        if tipo in {"cuenta", "cliente"} and cuenta_id_por_defecto is not None:
            contexto_id = cuenta_id_por_defecto
        else:
            raise ValueError("contexto_id es obligatorio para el contexto indicado.")

    if tipo in {"cuenta", "cliente"}:
        fila = await conexion.fetchrow(
            """
            SELECT id, nombre
            FROM cuentas
            WHERE id = $1 AND eliminado_en IS NULL
            """,
            contexto_id,
        )
        if not fila:
            raise ValueError(f"No existe la cuenta/cliente {contexto_id}.")
        return ContextoIA(tipo=tipo, contexto_id=contexto_id, cuenta_id=contexto_id, nombre=fila["nombre"])

    if tipo == "producto":
        fila = await conexion.fetchrow(
            """
            SELECT id, nombre
            FROM productos
            WHERE id = $1
            """,
            contexto_id,
        )
        if not fila:
            raise ValueError(f"No existe el producto {contexto_id}.")
        return ContextoIA(
            tipo=tipo,
            contexto_id=contexto_id,
            cuenta_id=cuenta_id_por_defecto,
            nombre=fila["nombre"],
        )

    fila = await conexion.fetchrow(
        """
        SELECT id, nombre, cuenta_id
        FROM oportunidades
        WHERE id = $1 AND eliminado_en IS NULL
        """,
        contexto_id,
    )
    if not fila:
        raise ValueError(f"No existe la oportunidad {contexto_id}.")
    cuenta_relacionada = fila["cuenta_id"] or cuenta_id_por_defecto
    return ContextoIA(
        tipo=tipo,
        contexto_id=contexto_id,
        cuenta_id=cuenta_relacionada,
        nombre=fila["nombre"],
    )
