"""Gestión del personal."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.core.security import hash_password
from app.models import Usuario
from app.schemas.admin import UsuarioIn, UsuarioUpdate
from app.services import auditoria


async def crear(session: AsyncSession, datos: UsuarioIn, actor: Usuario) -> Usuario:
    email = datos.email.lower()
    if await session.scalar(select(Usuario.id).where(func.lower(Usuario.email) == email)):
        raise Conflicto("Ya existe un usuario con ese email.")
    usuario = Usuario(
        **datos.model_dump(exclude={"password", "email"}),
        email=email,
        password_hash=hash_password(datos.password),
    )
    session.add(usuario)
    await session.flush()
    auditoria.registrar(session, actor, "usuarios.crear", "usuarios", usuario.id, {"email": email, "rol": datos.rol})
    await session.commit()
    return usuario


async def actualizar(session: AsyncSession, usuario_id: uuid.UUID, datos: UsuarioUpdate, actor: Usuario) -> Usuario:
    usuario = await session.get(Usuario, usuario_id)
    if not usuario:
        raise NoEncontrado("No existe ese usuario.")
    cambios = datos.model_dump(exclude_unset=True)
    if usuario.id == actor.id and (
        cambios.get("activo") is False or ("rol" in cambios and cambios["rol"] != actor.rol)
    ):
        raise ReglaNegocio("No puedes desactivarte ni cambiar tu propio rol.")
    if "password" in cambios:
        usuario.password_hash = hash_password(cambios.pop("password"))
        cambios["password"] = "(cambiada)"
    for campo, valor in cambios.items():
        if campo != "password":
            setattr(usuario, campo, valor)
    auditoria.registrar(session, actor, "usuarios.actualizar", "usuarios", usuario.id, cambios)
    await session.commit()
    await session.refresh(usuario)
    return usuario
