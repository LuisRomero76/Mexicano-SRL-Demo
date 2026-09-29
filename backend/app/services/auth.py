"""Autenticación del personal."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoAutorizado
from app.core.security import crear_token, hash_password, verify_password
from app.models import Usuario
from app.utils.fechas import ahora

# Hash de referencia: iguala el tiempo de respuesta cuando el email no existe.
_HASH_FICTICIO = hash_password("usuario-inexistente")


async def login(session: AsyncSession, email: str, password: str) -> tuple[Usuario, str, int]:
    usuario = await session.scalar(select(Usuario).where(func.lower(Usuario.email) == email.strip().lower()))
    valido = verify_password(password, usuario.password_hash if usuario else _HASH_FICTICIO)
    if not usuario or not valido or not usuario.activo:
        raise NoAutorizado("Email o contraseña incorrectos.", codigo="credenciales_invalidas")
    usuario.ultimo_login_at = ahora()
    await session.commit()
    token, expira_en = crear_token(str(usuario.id), usuario.rol)
    return usuario, token, expira_en
