"""Aplicación FastAPI: réplica del backend de Transportes El Mexicano S.R.L."""

import asyncio
import contextlib
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import bot as bot_api
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.core.errors import registrar_manejadores
from app.core.security import secreto_debil
from app.services.jobs import expirar_reservas_periodicamente
from app.utils.fechas import ahora

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("elmexicano")

if secreto_debil(settings.jwt_secret):
    if settings.is_production:
        raise RuntimeError("JWT_SECRET es débil: usa al menos 32 caracteres aleatorios en producción.")
    log.warning('JWT_SECRET es débil; genera uno con: python -c "import secrets; print(secrets.token_urlsafe(48))"')

_CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    tarea = None
    if settings.job_expirar_reservas_segundos > 0:
        tarea = asyncio.create_task(expirar_reservas_periodicamente(settings.job_expirar_reservas_segundos))
    yield
    if tarea:
        tarea.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await tarea
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend réplica (demo) de **Transportes El Mexicano S.R.L.**: venta de pasajes de bus, "
        "rutas e itinerarios, carga y encomiendas, puerta a puerta y centro de ayuda.\n\n"
        "Fechas en hora de Bolivia (America/La_Paz) y montos en bolivianos (Bs)."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.middleware("http")
async def cabeceras_de_seguridad(request: Request, call_next):
    respuesta = await call_next(request)
    for nombre, valor in _CABECERAS_SEGURIDAD.items():
        respuesta.headers.setdefault(nombre, valor)
    if request.url.path.startswith(
        ("/api/v1/admin", "/api/v1/auth", "/api/v1/reservas", "/api/v1/boletos", "/api/bot")
    ):
        respuesta.headers["Cache-Control"] = "no-store"
    if settings.cookie_secure:
        respuesta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return respuesta


registrar_manejadores(app)
app.include_router(api_router)
app.include_router(bot_api.router)


@app.get("/health", tags=["Sistema"], summary="Estado del servicio y de la base de datos")
async def health() -> JSONResponse:
    inicio = time.perf_counter()
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        bd = {"ok": True, "latencia_ms": round((time.perf_counter() - inicio) * 1000, 1)}
    except Exception as exc:  # noqa: BLE001 - el health check debe responder siempre
        bd = {"ok": False, "error": type(exc).__name__}
    estado = 200 if bd["ok"] else 503
    return JSONResponse(
        status_code=estado,
        content={"estado": "ok" if bd["ok"] else "degradado", "hora": ahora().isoformat(), "base_de_datos": bd},
    )


@app.get("/ping", tags=["Sistema"], summary="Responde sin consultar la base (para monitores y keep-alive)")
async def ping() -> dict[str, bool]:
    return {"ok": True}
