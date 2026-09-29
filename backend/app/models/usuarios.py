"""Módulo H — Usuarios internos y auditoría."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, pg_enum
from app.models.empresa import Oficina
from app.models.enums import RolUsuario


class Usuario(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "usuarios"

    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    telefono_e164: Mapped[str | None] = mapped_column(String(15))
    rol: Mapped[RolUsuario] = mapped_column(pg_enum(RolUsuario), index=True)
    oficina_id: Mapped[int | None] = mapped_column(ForeignKey("oficinas.id"))
    licencia_conducir: Mapped[str | None] = mapped_column(String(20))
    ultimo_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    oficina: Mapped[Oficina | None] = relationship()

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class Auditoria(Base):
    __tablename__ = "auditoria"
    __table_args__ = (
        Index("ix_auditoria_tabla_registro", "tabla", "registro_id"),
        Index("ix_auditoria_created_at", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(60))
    tabla: Mapped[str] = mapped_column(String(60))
    registro_id: Mapped[str] = mapped_column(String(40))
    cambios: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
