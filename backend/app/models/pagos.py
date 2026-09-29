"""Módulo E — Pagos, facturas y reembolsos."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, pg_enum
from app.models.enums import (
    EstadoFactura,
    EstadoPago,
    EstadoReembolso,
    MetodoPago,
    OrigenReembolso,
)


class Pago(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint("monto_bs > 0", name="monto_positivo"),
        CheckConstraint(
            "num_nonnulls(venta_pasaje_id, encomienda_id, solicitud_puerta_id) = 1",
            name="un_solo_concepto",
        ),
    )

    venta_pasaje_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ventas_pasaje.id"), index=True)
    encomienda_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encomiendas.id"), index=True)
    solicitud_puerta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("solicitudes_puerta_a_puerta.id"), index=True
    )
    metodo: Mapped[MetodoPago] = mapped_column(pg_enum(MetodoPago))
    monto_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estado: Mapped[EstadoPago] = mapped_column(pg_enum(EstadoPago), server_default=EstadoPago.pendiente.value)
    proveedor: Mapped[str | None] = mapped_column(String(40))
    transaccion_externa_id: Mapped[str | None] = mapped_column(String(80))
    qr_payload: Mapped[str | None] = mapped_column(Text)
    ultimos4_tarjeta: Mapped[str | None] = mapped_column(String(4))
    pagado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cobrado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))

    factura: Mapped["Factura | None"] = relationship(back_populates="pago")


class Factura(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "facturas"

    pago_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pagos.id"), unique=True)
    numero_factura: Mapped[int] = mapped_column(BigInteger, unique=True)
    cuf: Mapped[str | None] = mapped_column(String(100))
    nit_ci_cliente: Mapped[str] = mapped_column(String(20))
    razon_social_cliente: Mapped[str] = mapped_column(String(150))
    monto_total_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_emision: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    estado: Mapped[EstadoFactura] = mapped_column(pg_enum(EstadoFactura), server_default=EstadoFactura.valida.value)
    url_pdf: Mapped[str | None] = mapped_column(String(300))

    pago: Mapped[Pago] = relationship(back_populates="factura")


class Reembolso(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "reembolsos"
    __table_args__ = (
        CheckConstraint("monto_bs >= 0 AND monto_bs <= monto_original_bs", name="monto_valido"),
        CheckConstraint("porcentaje_retencion BETWEEN 0 AND 100", name="retencion_valida"),
    )

    pago_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pagos.id"), index=True)
    boleto_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("boletos.id"), index=True)
    origen: Mapped[OrigenReembolso] = mapped_column(
        pg_enum(OrigenReembolso), server_default=OrigenReembolso.solicitud_cliente.value
    )
    monto_original_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    porcentaje_retencion: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default="0")
    monto_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    motivo: Mapped[str] = mapped_column(String(250))
    estado: Mapped[EstadoReembolso] = mapped_column(
        pg_enum(EstadoReembolso), server_default=EstadoReembolso.solicitado.value, index=True
    )
    solicitado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_limite_pago: Mapped[date | None]
    resuelto_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resuelto_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))

    pago: Mapped[Pago] = relationship()
