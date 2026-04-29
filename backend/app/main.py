"""
Punto de entrada de la aplicación FastAPI.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth.router import router as router_auth
from app.config import configuracion
from app.database import cerrar_pool, iniciar_pool, obtener_pool
from app.modules.dashboard.router import router as router_dashboard
from app.modules.pipeline.router import router as router_pipeline
from app.modules.equipo.router import router as router_equipo
from app.modules.productos.router import router as router_productos
from app.modules.alertas.router import router as router_alertas
from app.modules.importacion.router import router as router_importacion
from app.modules.ia.router import router as router_ia
from app.modules.ia.proveedores import cargar_config_research_desde_db
from app.modules.voice.router import router as router_voice
from app.modules.documentos_jobs.router import router as router_documentos_jobs
from app.modules.decks.router import router as router_decks
from app.modules.perfil.router import router as router_perfil
from app.modules.cuentas.router import router as router_cuentas
from app.modules.notas.router import router as router_notas
from app.modules.documentos.router import router as router_documentos
from app.modules.informes.router import router as router_informes
from app.modules.usuarios.router import router as router_usuarios
from app.modules.cross_selling.router import router as router_cross_selling
from app.modules.forecast.router import router as router_forecast
from app.modules.investigacion.router import router as router_investigacion
from app.modules.propuesta.router import router as router_propuesta
from app.modules.seguimientos.router import router as router_seguimientos
from app.modules.scoring.router import router as router_scoring
from app.modules.reuniones.router import router as router_reuniones
from app.modules.coaching.router import router as router_coaching
from app.modules.calidad_ia.router import router as router_calidad_ia
from app.modules.historial.router import router as router_historial, router_compartir_publico
from app.modules.plantillas.router import router as router_plantillas
from app.modules.artefactos.router import router as router_artefactos
from app.modules.objetivos.router import router as router_objetivos
from app.modules.scoring import servicio as scoring_servicio

# =============================================================================
# Rate limiter
# =============================================================================

limitador = Limiter(key_func=get_remote_address)
logger = logging.getLogger(__name__)


# =============================================================================
# Ciclo de vida de la aplicación
# =============================================================================

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    await iniciar_pool()
    pool = await obtener_pool()
    await cargar_config_research_desde_db(pool)
    tarea_scoring = asyncio.create_task(_job_scoring_periodico())
    yield
    tarea_scoring.cancel()
    try:
        await tarea_scoring
    except asyncio.CancelledError:
        pass
    await cerrar_pool()


async def _job_scoring_periodico() -> None:
    while True:
        try:
            pool = await obtener_pool()
            async with pool.acquire() as conexion:
                await scoring_servicio.recalcular_scores_pipeline(conexion)
                await scoring_servicio.detectar_caida_score(conexion)
        except Exception:
            logger.exception("Fallo en job periódico de scoring.")

        await asyncio.sleep(24 * 60 * 60)


# =============================================================================
# Aplicación
# =============================================================================

app = FastAPI(
    title="SGS España — Inteligencia Comercial",
    version="1.1.0",
    docs_url="/docs" if configuracion.ENVIRONMENT == "development" else None,
    redoc_url=None,
    lifespan=ciclo_de_vida,
)

app.state.limiter = limitador
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# =============================================================================
# CORS
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=configuracion.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# =============================================================================
# Middleware: headers de seguridad (ASGI puro — sin BaseHTTPMiddleware)
# =============================================================================

class SecurityHeadersMiddleware:
    """Middleware ASGI puro para inyectar headers de seguridad.
    No usa BaseHTTPMiddleware para evitar conflictos con asyncpg en tests.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_con_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ]
                if configuracion.ENVIRONMENT == "production":
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_con_headers)


app.add_middleware(SecurityHeadersMiddleware)


# =============================================================================
# Routers
# =============================================================================

app.include_router(router_auth)
app.include_router(router_dashboard)
app.include_router(router_pipeline)
app.include_router(router_equipo)
app.include_router(router_productos)
app.include_router(router_alertas)
app.include_router(router_importacion)
app.include_router(router_ia)
app.include_router(router_voice)
app.include_router(router_decks)
app.include_router(router_perfil)
app.include_router(router_documentos_jobs)
app.include_router(router_cuentas)
app.include_router(router_notas)
app.include_router(router_documentos)
app.include_router(router_informes)
app.include_router(router_usuarios)
app.include_router(router_cross_selling)
app.include_router(router_forecast)
app.include_router(router_investigacion)
app.include_router(router_propuesta)
app.include_router(router_seguimientos)
app.include_router(router_scoring)
app.include_router(router_reuniones)
app.include_router(router_coaching)
app.include_router(router_calidad_ia)
app.include_router(router_historial)
app.include_router(router_compartir_publico)   # público, sin auth
app.include_router(router_plantillas)
app.include_router(router_artefactos)
app.include_router(router_objetivos)


# =============================================================================
# Health check
# =============================================================================

@app.get("/health", tags=["sistema"])
async def health_check():
    return {"estado": "ok", "version": "1.1.0"}
