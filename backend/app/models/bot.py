"""Módulo J — Integración con el agente de voz (ElevenLabs): API keys y registro de consultas."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiKey(Base):
    """Credencial de un cliente de máquina. Solo se guarda el SHA-256 de la key, nunca la key."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    prefijo: Mapped[str] = mapped_column(String(12))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{bot:read}'"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))
    ultimo_uso_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revocada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BotConsultaLog(Base):
    __tablename__ = "bot_consultas_log"
    __table_args__ = (
        Index("ix_bot_consultas_log_created_at", text("created_at DESC")),
        Index("ix_bot_consultas_log_tool_created_at", "tool", "created_at"),
        Index("ix_bot_consultas_log_caller_id", "caller_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    api_key_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("api_keys.id", ondelete="SET NULL"))
    tool: Mapped[str] = mapped_column(String(60))
    caller_id: Mapped[str | None] = mapped_column(String(15))
    parametros: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    encontrado: Mapped[bool]
    coincide_caller: Mapped[bool | None]
    resultado: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    codigo_http: Mapped[int] = mapped_column(SmallInteger)
    latencia_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
