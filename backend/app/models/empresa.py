"""Módulo A — Empresa, red de oficinas y configuración."""

from datetime import date, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import ServicioOficina, TipoOficina


class Empresa(TimestampMixin, Base):
    __tablename__ = "empresa"
    __table_args__ = (CheckConstraint("id = 1", name="fila_unica"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    razon_social: Mapped[str] = mapped_column(String(150))
    nombre_comercial: Mapped[str] = mapped_column(String(100))
    nit: Mapped[str | None] = mapped_column(String(20))
    ente_regulador: Mapped[str | None] = mapped_column(String(200))
    sitio_web: Mapped[str | None] = mapped_column(String(200))
    url_compra_pasajes: Mapped[str | None] = mapped_column(String(300))
    url_rastreo_carga: Mapped[str | None] = mapped_column(String(300))
    facebook_url: Mapped[str | None] = mapped_column(String(300))
    email_contacto: Mapped[str | None] = mapped_column(String(150))
    telefono_central_e164: Mapped[str | None] = mapped_column(String(15))
    telefono_atencion_cliente_e164: Mapped[str | None] = mapped_column(String(15))
    whatsapp_central_e164: Mapped[str | None] = mapped_column(String(15))
    color_marca: Mapped[str | None] = mapped_column(String(7))
    eslogan: Mapped[str | None] = mapped_column(String(200))
    descripcion: Mapped[str | None] = mapped_column(Text)
    terminos_condiciones: Mapped[str | None] = mapped_column(Text)
    moneda: Mapped[str] = mapped_column(String(3), server_default="BOB")
    zona_horaria: Mapped[str] = mapped_column(String(40), server_default="America/La_Paz")


class Ciudad(TimestampMixin, Base):
    __tablename__ = "ciudades"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(3), unique=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    departamento: Mapped[str] = mapped_column(String(40))
    es_destino_pasajeros: Mapped[bool] = mapped_column(server_default=text("false"))
    es_destino_carga: Mapped[bool] = mapped_column(server_default=text("false"))
    tiene_puerta_a_puerta: Mapped[bool] = mapped_column(server_default=text("false"))
    whatsapp_puerta_a_puerta_e164: Mapped[str | None] = mapped_column(String(15))
    alias_busqueda: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    oficinas: Mapped[list["Oficina"]] = relationship(back_populates="ciudad")


class Oficina(TimestampMixin, Base):
    __tablename__ = "oficinas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[TipoOficina] = mapped_column(pg_enum(TipoOficina), index=True)
    direccion: Mapped[str] = mapped_column(String(250))
    referencia: Mapped[str | None] = mapped_column(String(250))
    telefono_e164: Mapped[str | None] = mapped_column(String(15))
    whatsapp_e164: Mapped[str | None] = mapped_column(String(15))
    email: Mapped[str | None] = mapped_column(String(150))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    url_mapa: Mapped[str | None] = mapped_column(String(300))
    es_principal: Mapped[bool] = mapped_column(server_default=text("false"))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    ciudad: Mapped[Ciudad] = relationship(back_populates="oficinas")
    horarios: Mapped[list["HorarioOficina"]] = relationship(
        back_populates="oficina", cascade="all, delete-orphan", order_by="HorarioOficina.dia_semana"
    )


class HorarioOficina(TimestampMixin, Base):
    __tablename__ = "horarios_oficina"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 1 AND 7", name="dia_semana_valido"),
        CheckConstraint("hora_cierre > hora_apertura", name="rango_horas"),
        UniqueConstraint("oficina_id", "servicio", "dia_semana", "hora_apertura"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    oficina_id: Mapped[int] = mapped_column(ForeignKey("oficinas.id", ondelete="CASCADE"))
    servicio: Mapped[ServicioOficina] = mapped_column(
        pg_enum(ServicioOficina), server_default=ServicioOficina.general.value
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger)
    hora_apertura: Mapped[time]
    hora_cierre: Mapped[time]
    observacion: Mapped[str | None] = mapped_column(String(150))

    oficina: Mapped[Oficina] = relationship(back_populates="horarios")


class Feriado(TimestampMixin, Base):
    __tablename__ = "feriados"
    __table_args__ = (UniqueConstraint("fecha", "departamento", postgresql_nulls_not_distinct=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date]
    nombre: Mapped[str] = mapped_column(String(100))
    departamento: Mapped[str | None] = mapped_column(String(40))


class ParametroNegocio(TimestampMixin, Base):
    __tablename__ = "parametros_negocio"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[Any] = mapped_column(JSONB)
    descripcion: Mapped[str | None] = mapped_column(String(250))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
