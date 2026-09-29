"""Contraseñas (argon2) y tokens JWT del personal."""

from datetime import timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.utils.fechas import ahora

_hasher = PasswordHasher()
_ALGORITMO = "HS256"

COOKIE_SESION = "em_session"
SECRETOS_INSEGUROS = {"cambiar", "secret", "changeme", ""}


def secreto_debil(secreto: str) -> bool:
    return secreto in SECRETOS_INSEGUROS or len(secreto) < 32


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def crear_token(usuario_id: str, rol: str) -> tuple[str, int]:
    settings = get_settings()
    expira_en = settings.jwt_expire_minutes * 60
    payload = {
        "sub": usuario_id,
        "rol": rol,
        "iat": ahora(),
        "exp": ahora() + timedelta(seconds=expira_en),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITMO), expira_en


def decodificar_token(token: str) -> dict[str, Any]:
    """Lanza jwt.PyJWTError si el token es inválido o expiró."""
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGORITMO])
