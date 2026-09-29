"""Módulo B — Flota."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pg_enum
from app.models.enums import EstadoBus, PlantaBus, PosicionAsiento, TipoVehiculoCarga

tipo_asiento_comodidades = Table(
    "tipo_asiento_comodidades",
    Base.metadata,
    Column("tipo_asiento_id", SmallInteger, ForeignKey("tipos_asiento.id", ondelete="CASCADE"), primary_key=True),
    Column("comodidad_id", SmallInteger, ForeignKey("comodidades.id", ondelete="CASCADE"), primary_key=True),
)


class TipoAsiento(TimestampMixin, Base):
    __tablename__ = "tipos_asiento"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(50))
    planta: Mapped[PlantaBus] = mapped_column(pg_enum(PlantaBus))
    inclinacion_grados: Mapped[int] = mapped_column(SmallInteger)
    descripcion: Mapped[str | None] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(SmallInteger, server_default="0")

    comodidades: Mapped[list["Comodidad"]] = relationship(secondary=tipo_asiento_comodidades, order_by="Comodidad.id")


class Comodidad(TimestampMixin, Base):
    __tablename__ = "comodidades"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))
    icono: Mapped[str | None] = mapped_column(String(40))


class Bus(TimestampMixin, Base):
    __tablename__ = "buses"
    __table_args__ = (CheckConstraint("anio BETWEEN 1990 AND 2100", name="anio_valido"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_interno: Mapped[str] = mapped_column(String(10), unique=True)
    placa: Mapped[str] = mapped_column(String(10), unique=True)
    marca: Mapped[str | None] = mapped_column(String(40))
    modelo: Mapped[str | None] = mapped_column(String(60))
    anio: Mapped[int | None] = mapped_column(SmallInteger)
    pisos: Mapped[int] = mapped_column(SmallInteger, server_default="2")
    capacidad_total: Mapped[int] = mapped_column(SmallInteger)
    estado: Mapped[EstadoBus] = mapped_column(pg_enum(EstadoBus), server_default=EstadoBus.operativo.value)
    gps_dispositivo_id: Mapped[str | None] = mapped_column(String(50))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    asientos: Mapped[list["Asiento"]] = relationship(
        back_populates="bus", cascade="all, delete-orphan", order_by="Asiento.numero"
    )


class Asiento(TimestampMixin, Base):
    __tablename__ = "asientos"
    __table_args__ = (UniqueConstraint("bus_id", "numero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="CASCADE"))
    numero: Mapped[int] = mapped_column(SmallInteger)
    tipo_asiento_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("tipos_asiento.id"))
    planta: Mapped[PlantaBus] = mapped_column(pg_enum(PlantaBus))
    fila: Mapped[int] = mapped_column(SmallInteger)
    columna: Mapped[int] = mapped_column(SmallInteger)
    posicion: Mapped[PosicionAsiento] = mapped_column(pg_enum(PosicionAsiento))
    habilitado: Mapped[bool] = mapped_column(server_default=text("true"))

    bus: Mapped[Bus] = relationship(back_populates="asientos")
    tipo_asiento: Mapped[TipoAsiento] = relationship()


class VehiculoCarga(TimestampMixin, Base):
    __tablename__ = "vehiculos_carga"

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(10), unique=True)
    tipo: Mapped[TipoVehiculoCarga] = mapped_column(pg_enum(TipoVehiculoCarga))
    capacidad_kg: Mapped[int]
    ciudad_base_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    gps_dispositivo_id: Mapped[str | None] = mapped_column(String(50))
    ultima_latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    ultima_longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    ultima_posicion_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))
