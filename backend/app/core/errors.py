"""Errores de dominio y su traducción a respuestas HTTP.

Los servicios lanzan estas excepciones; los routers no manejan errores a mano.
Formato de respuesta: {"error": "codigo", "mensaje": "texto para el usuario", "detalle": {...}}
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class DomainError(Exception):
    status_code = 400
    codigo = "error"

    def __init__(self, mensaje: str, *, codigo: str | None = None, detalle: dict[str, Any] | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        if codigo:
            self.codigo = codigo
        self.detalle = detalle


class NoEncontrado(DomainError):
    status_code = 404
    codigo = "no_encontrado"


class Conflicto(DomainError):
    status_code = 409
    codigo = "conflicto"


class ReglaNegocio(DomainError):
    status_code = 422
    codigo = "regla_de_negocio"


class NoAutorizado(DomainError):
    status_code = 401
    codigo = "no_autenticado"


class Prohibido(DomainError):
    status_code = 403
    codigo = "prohibido"


class DemasiadosIntentos(DomainError):
    status_code = 429
    codigo = "demasiados_intentos"


def _respuesta(status: int, codigo: str, mensaje: str, detalle: Any = None) -> JSONResponse:
    cuerpo: dict[str, Any] = {"error": codigo, "mensaje": mensaje}
    if detalle is not None:
        cuerpo["detalle"] = detalle
    headers: dict[str, str] = {}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    if status == 429 and isinstance(detalle, dict) and "reintentar_en_segundos" in detalle:
        headers["Retry-After"] = str(detalle["reintentar_en_segundos"])
    return JSONResponse(status_code=status, content=cuerpo, headers=headers or None)


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _dominio(_: Request, exc: DomainError) -> JSONResponse:
        return _respuesta(exc.status_code, exc.codigo, exc.mensaje, exc.detalle)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        errores = [
            {"campo": ".".join(str(p) for p in e["loc"][1:]) or e["loc"][0], "mensaje": e["msg"]} for e in exc.errors()
        ]
        return _respuesta(422, "datos_invalidos", "Revisa los datos enviados.", errores)

    @app.exception_handler(IntegrityError)
    async def _integridad(_: Request, exc: IntegrityError) -> JSONResponse:
        # Última línea de defensa: las reglas se validan antes en los servicios.
        restriccion = getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)
        return _respuesta(
            409,
            "conflicto",
            "La operación entra en conflicto con datos existentes.",
            {"restriccion": restriccion} if restriccion else None,
        )
