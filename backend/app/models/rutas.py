"""Módulo C — Rutas, itinerarios, salidas y tarifas."""

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, pg_enum
from app.models.empresa import Ciudad, Oficina
from app.models.enums import EstadoSalida, RolTripulacion, TipoPasajero
from app.models.flota import Bus, TipoAsiento


class Ruta(TimestampMixin, Base):
    __tablename__ = "rutas"
    __table_args__ = (
        CheckConstraint("origen_ciudad_id <> destino_ciudad_id", name="origen_distinto_destino"),
        UniqueConstraint("origen_ciudad_id", "destino_ciudad_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    origen_ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    destino_ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    distancia_km: Mapped[int] = mapped_column(SmallInteger)
    duracion_estimada_min: Mapped[int] = mapped_column(SmallInteger)
    cargo_exceso_equipaje_kg_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    descripcion: Mapped[str | None] = mapped_column(String(250))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    origen: Mapped[Ciudad] = relationship(foreign_keys=[origen_ciudad_id])
    destino: Mapped[Ciudad] = relationship(foreign_keys=[destino_ciudad_id])
    paradas: Mapped[list["RutaParada"]] = relationship(
        back_populates="ruta", cascade="all, delete-orphan", order_by="RutaParada.orden"
    )


class RutaParada(TimestampMixin, Base):
    __tablename__ = "ruta_paradas"
    __table_args__ = (
        UniqueConstraint("ruta_id", "orden"),
        UniqueConstraint("ruta_id", "ciudad_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("rutas.id", ondelete="CASCADE"))
    ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    orden: Mapped[int] = mapped_column(SmallInteger)
    km_desde_origen: Mapped[int] = mapped_column(SmallInteger)
    minutos_desde_origen: Mapped[int] = mapped_column(SmallInteger)
    permite_carga: Mapped[bool] = mapped_column(server_default=text("true"))
    permite_pasajeros: Mapped[bool] = mapped_column(server_default=text("false"))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))

    ruta: Mapped[Ruta] = relationship(back_populates="paradas")
    ciudad: Mapped[Ciudad] = relationship()


class PlantillaHorario(TimestampMixin, Base):
    __tablename__ = "plantillas_horario"
    __table_args__ = (UniqueConstraint("ruta_id", "hora_salida", "vigente_desde"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("rutas.id"))
    hora_salida: Mapped[time]
    dias_semana: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger), server_default=text("'{1,2,3,4,5,6,7}'"))
    oficina_salida_id: Mapped[int | None] = mapped_column(ForeignKey("oficinas.id"))
    vigente_desde: Mapped[date]
    vigente_hasta: Mapped[date | None]
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))

    ruta: Mapped[Ruta] = relationship()


class Salida(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "salidas"
    __table_args__ = (
        CheckConstraint("minutos_demora >= 0", name="demora_no_negativa"),
        CheckConstraint("fecha_hora_llegada_estimada > fecha_hora_salida", name="llegada_despues_de_salida"),
        Index("ix_salidas_ruta_id_fecha_hora_salida", "ruta_id", "fecha_hora_salida"),
        Index("ix_salidas_bus_id_fecha_hora_salida", "bus_id", "fecha_hora_salida"),
    )

    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("rutas.id"))
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas_horario.id"))
    bus_id: Mapped[int | None] = mapped_column(ForeignKey("buses.id"))
    oficina_salida_id: Mapped[int | None] = mapped_column(ForeignKey("oficinas.id"))
    fecha_hora_salida: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_hora_llegada_estimada: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    anden: Mapped[str | None] = mapped_column(String(10))
    estado: Mapped[EstadoSalida] = mapped_column(
        pg_enum(EstadoSalida), server_default=EstadoSalida.programada.value, index=True
    )
    minutos_demora: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    motivo_estado: Mapped[str | None] = mapped_column(String(250))
    salida_real_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    llegada_real_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))

    ruta: Mapped[Ruta] = relationship()
    bus: Mapped[Bus | None] = relationship()
    oficina_salida: Mapped[Oficina | None] = relationship()
    tripulacion: Mapped[list["SalidaTripulacion"]] = relationship(back_populates="salida", cascade="all, delete-orphan")
    precios: Mapped[list["PrecioSalida"]] = relationship(cascade="all, delete-orphan")


class SalidaTripulacion(TimestampMixin, Base):
    __tablename__ = "salida_tripulacion"

    salida_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salidas.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    rol: Mapped[RolTripulacion] = mapped_column(pg_enum(RolTripulacion))

    salida: Mapped[Salida] = relationship(back_populates="tripulacion")
    usuario: Mapped["Usuario"] = relationship()  # noqa: F821


class TarifaPasaje(TimestampMixin, Base):
    __tablename__ = "tarifas_pasaje"
    __table_args__ = (
        CheckConstraint("precio_bs > 0 AND precio_bs <= precio_maximo_referencial_bs", name="precio_valido"),
        CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia_valida"),
        UniqueConstraint("ruta_id", "tipo_asiento_id", "vigente_desde"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ruta_id: Mapped[int] = mapped_column(ForeignKey("rutas.id"))
    tipo_asiento_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("tipos_asiento.id"))
    precio_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_maximo_referencial_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    vigente_desde: Mapped[date]
    vigente_hasta: Mapped[date | None]
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))

    ruta: Mapped[Ruta] = relationship()
    tipo_asiento: Mapped[TipoAsiento] = relationship()


class PrecioSalida(TimestampMixin, Base):
    __tablename__ = "precios_salida"
    __table_args__ = (CheckConstraint("precio_bs > 0", name="precio_positivo"),)

    salida_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salidas.id", ondelete="CASCADE"), primary_key=True)
    tipo_asiento_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("tipos_asiento.id"), primary_key=True)
    precio_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class PoliticaTipoPasajero(TimestampMixin, Base):
    __tablename__ = "politicas_tipo_pasajero"
    __table_args__ = (CheckConstraint("descuento_porcentaje BETWEEN 0 AND 100", name="descuento_valido"),)

    tipo_pasajero: Mapped[TipoPasajero] = mapped_column(pg_enum(TipoPasajero), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    solo_boleteria: Mapped[bool] = mapped_column(server_default=text("false"))
    edad_min: Mapped[int | None] = mapped_column(SmallInteger)
    edad_max: Mapped[int | None] = mapped_column(SmallInteger)
    requisito: Mapped[str | None] = mapped_column(String(250))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
