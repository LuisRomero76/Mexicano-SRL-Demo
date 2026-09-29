"""Módulo D — Clientes y venta de pasajes."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, pg_enum
from app.models.enums import (
    CanalVenta,
    EstadoBoleto,
    EstadoVenta,
    TipoDocumento,
    TipoEquipaje,
    TipoPasajero,
)
from app.models.flota import Asiento, TipoAsiento
from app.models.rutas import Salida


class Cliente(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "clientes"
    __table_args__ = (
        UniqueConstraint("tipo_documento", "numero_documento", "complemento", postgresql_nulls_not_distinct=True),
    )

    tipo_documento: Mapped[TipoDocumento] = mapped_column(pg_enum(TipoDocumento), server_default=TipoDocumento.ci.value)
    numero_documento: Mapped[str] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(5))
    extension: Mapped[str | None] = mapped_column(String(3))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    fecha_nacimiento: Mapped[date | None]
    telefono_e164: Mapped[str | None] = mapped_column(String(15), index=True)
    email: Mapped[str | None] = mapped_column(String(150))
    nit_facturacion: Mapped[str | None] = mapped_column(String(20))
    razon_social_facturacion: Mapped[str | None] = mapped_column(String(150))
    cuenta_corporativa_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cuentas_corporativas.id"))
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"


class VentaPasaje(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "ventas_pasaje"
    __table_args__ = (
        CheckConstraint("total_bs = subtotal_bs - descuento_bs", name="total_cuadra"),
        Index("ix_ventas_pasaje_estado_expira_at", "estado", "expira_at"),
    )

    codigo_reserva: Mapped[str] = mapped_column(String(8), unique=True)
    comprador_cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    canal: Mapped[CanalVenta] = mapped_column(pg_enum(CanalVenta), server_default=CanalVenta.web.value)
    estado: Mapped[EstadoVenta] = mapped_column(pg_enum(EstadoVenta), server_default=EstadoVenta.pendiente_pago.value)
    subtotal_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    descuento_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    total_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    expira_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pagada_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vendida_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    oficina_venta_id: Mapped[int | None] = mapped_column(ForeignKey("oficinas.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)

    comprador: Mapped[Cliente] = relationship()
    boletos: Mapped[list["Boleto"]] = relationship(back_populates="venta", order_by="Boleto.numero_asiento")


class Boleto(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "boletos"
    __table_args__ = (
        CheckConstraint("descuento_bs >= 0 AND descuento_bs <= precio_bs", name="descuento_valido"),
        CheckConstraint(
            "semanas_gestacion IS NULL OR semanas_gestacion BETWEEN 1 AND 30",
            name="semanas_gestacion_valida",
        ),
        Index(
            "uq_boletos_asiento_activo",
            "salida_id",
            "numero_asiento",
            unique=True,
            postgresql_where=text("estado IN ('reservado', 'emitido', 'abordado')"),
        ),
    )

    numero_boleto: Mapped[str] = mapped_column(String(12), unique=True)
    venta_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ventas_pasaje.id"), index=True)
    salida_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("salidas.id"), index=True)
    asiento_id: Mapped[int] = mapped_column(ForeignKey("asientos.id"))
    numero_asiento: Mapped[int] = mapped_column(SmallInteger)
    tipo_asiento_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("tipos_asiento.id"))
    pasajero_cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    tipo_pasajero: Mapped[TipoPasajero] = mapped_column(pg_enum(TipoPasajero), server_default=TipoPasajero.adulto.value)
    precio_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    descuento_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    estado: Mapped[EstadoBoleto] = mapped_column(pg_enum(EstadoBoleto), server_default=EstadoBoleto.reservado.value)
    es_electronico: Mapped[bool] = mapped_column(server_default=text("true"))
    codigo_qr: Mapped[str | None] = mapped_column(String(100))
    viaja_con_perro_guia: Mapped[bool] = mapped_column(server_default=text("false"))
    semanas_gestacion: Mapped[int | None] = mapped_column(SmallInteger)
    permiso_viaje_numero: Mapped[str | None] = mapped_column(String(40))
    menor_acompanado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clientes.id"))
    boleto_origen_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("boletos.id"))
    abordado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    venta: Mapped[VentaPasaje] = relationship(back_populates="boletos")
    salida: Mapped[Salida] = relationship()
    asiento: Mapped[Asiento] = relationship()
    tipo_asiento: Mapped[TipoAsiento] = relationship()
    pasajero: Mapped[Cliente] = relationship(foreign_keys=[pasajero_cliente_id])
    equipajes: Mapped[list["Equipaje"]] = relationship(back_populates="boleto")

    @property
    def total_bs(self) -> Decimal:
        return self.precio_bs - self.descuento_bs


class Equipaje(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "equipajes"
    __table_args__ = (CheckConstraint("peso_kg > 0", name="peso_positivo"),)

    boleto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("boletos.id"), index=True)
    etiqueta: Mapped[str] = mapped_column(String(15), unique=True)
    tipo: Mapped[TipoEquipaje] = mapped_column(pg_enum(TipoEquipaje), server_default=TipoEquipaje.bodega.value)
    piezas: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    peso_permitido_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), server_default="20")
    exceso_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), server_default="0")
    cargo_exceso_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    descripcion: Mapped[str | None] = mapped_column(String(150))

    boleto: Mapped[Boleto] = relationship(back_populates="equipajes")
