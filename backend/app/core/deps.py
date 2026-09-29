"""Dependencias de FastAPI: sesión de BD y autenticación del personal.

La sesión viaja en una cookie httpOnly (navegador) o en `Authorization: Bearer` (clientes de API).
Con la cookie, las operaciones que modifican datos exigen la cabecera `X-Requested-With`, que un
formulario de otro sitio no puede enviar sin preflight de CORS (defensa CSRF junto con SameSite).
"""

import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import NoAutorizado, Prohibido
from app.core.security import COOKIE_SESION, decodificar_token
from app.models import Usuario
from app.models.enums import RolUsuario

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
_METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


async def get_usuario_actual(request: Request, session: SessionDep, bearer: str | None = Depends(_oauth2)) -> Usuario:
    token = bearer
    if not token:
        token = request.cookies.get(COOKIE_SESION)
        if (
            token
            and request.method not in _METODOS_SEGUROS
            and request.headers.get("x-requested-with") != ("XMLHttpRequest")
        ):
            raise Prohibido("Solicitud rechazada por seguridad (falta X-Requested-With).", codigo="csrf")
    if not token:
        raise NoAutorizado("Debes iniciar sesión.")
    try:
        payload = decodificar_token(token)
        usuario_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise NoAutorizado("Sesión inválida o expirada.") from exc
    usuario = await session.get(Usuario, usuario_id)
    if not usuario or not usuario.activo:
        raise NoAutorizado("Usuario inactivo o inexistente.")
    return usuario


UsuarioActual = Annotated[Usuario, Depends(get_usuario_actual)]

TODO_EL_PERSONAL = tuple(RolUsuario)


def requiere_roles(*roles: RolUsuario) -> Callable:
    """Permite el acceso a los roles indicados; `admin` siempre tiene acceso."""
    permitidos = {RolUsuario.admin, *roles}

    async def _verificar(usuario: UsuarioActual) -> Usuario:
        if usuario.rol not in permitidos:
            raise Prohibido("No tienes permiso para esta operación.")
        return usuario

    return _verificar


class Paginacion:
    def __init__(
        self,
        limit: int = Query(20, ge=1, le=100, description="Cantidad de resultados"),
        offset: int = Query(0, ge=0, description="Resultados a saltar"),
    ):
        self.limit = limit
        self.offset = offset


PaginacionDep = Annotated[Paginacion, Depends()]
