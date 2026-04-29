"""
Conexión a PostgreSQL mediante asyncpg con pool de conexiones.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from app.config import configuracion

_pool: asyncpg.Pool | None = None


async def iniciar_pool() -> None:
    """Crea el pool de conexiones al arrancar la aplicación.
    En entornos Docker recién inicializados, PostgreSQL puede tardar
    más que el healthcheck básico en aceptar conexiones reales.
    """
    global _pool
    # asyncpg no entiende el prefijo postgresql+asyncpg — lo normalizamos
    dsn = configuracion.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    ultimo_error: Exception | None = None
    for intento in range(1, 31):
        try:
            _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
            return
        except (
            asyncpg.CannotConnectNowError,
            asyncpg.ConnectionDoesNotExistError,
            asyncpg.TooManyConnectionsError,
            OSError,
        ) as exc:
            ultimo_error = exc
            await asyncio.sleep(2)

    if ultimo_error is not None:
        raise ultimo_error


async def cerrar_pool() -> None:
    """Cierra el pool al apagar la aplicación."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def obtener_pool() -> asyncpg.Pool:
    """Devuelve el pool para uso en BackgroundTasks (fuera del ciclo de request)."""
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está inicializado.")
    return _pool


async def obtener_conexion() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependencia de FastAPI que proporciona una conexión del pool
    y la devuelve automáticamente al terminar el request.
    """
    if _pool is None:
        raise RuntimeError("El pool de base de datos no está inicializado.")
    async with _pool.acquire() as conexion:
        yield conexion
