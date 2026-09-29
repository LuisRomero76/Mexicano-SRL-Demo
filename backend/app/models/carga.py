"""Módulo F — Carga y encomiendas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin, pg_enum
from app.models.empresa import Ciudad, Oficina
from app.models.enums import (
    CanalVenta,
    EstadoEncomienda,
    EstadoPago,
    EstadoSolicitudPuerta,
    FranjaHoraria,
    ModalidadEntrega,
    PagoEn,
    TipoDocumento,
    TipoEnvio,
    TipoSolicitudPuerta,
)
from app.models.ventas import Cliente


class CuentaCorporativa(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "cuentas_corporativas"

    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    razon_social: Mapped[str] = mapped_column(String(150))
    nit: Mapped[str] = mapped_column(String(20), unique=True)
    contacto_nombre: Mapped[str | None] = mapped_column(String(100))
    contacto_telefono_e164: Mapped[str | None] = mapped_column(String(15))
    contacto_email: Mapped[str | None] = mapped_column(String(150))
    limite_credito_bs: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    saldo_pendiente_bs: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    dias_credito: Mapped[int] = mapped_column(SmallInteger, server_default="30")
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))


class TarifaCarga(TimestampMixin, Base):
    __tablename__ = "tarifas_carga"
    __table_args__ = (
        CheckConstraint("peso_max_kg IS NULL OR peso_max_kg >= peso_min_kg", name="rango_peso"),
        # Una tarifa por tramo de peso y fecha de vigencia (también sirve de índice de búsqueda).
        UniqueConstraint("origen_ciudad_id", "destino_ciudad_id", "tipo_envio", "peso_min_kg", "vigente_desde"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origen_ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    destino_ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    tipo_envio: Mapped[TipoEnvio] = mapped_column(pg_enum(TipoEnvio))
    peso_min_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    peso_max_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    precio_base_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    precio_kg_adicional_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    recargo_puerta_a_puerta_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    vigente_desde: Mapped[date]
    vigente_hasta: Mapped[date | None]
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))


class Encomienda(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "encomiendas"
    __table_args__ = (
        CheckConstraint(
            "(tipo_envio IN ('sobre', 'paquete') AND peso_kg <= 30) OR (tipo_envio = 'carga' AND peso_kg > 30)",
            name="peso_segun_tipo",
        ),
        CheckConstraint("peso_kg > 0", name="peso_positivo"),
        CheckConstraint("cantidad_bultos >= 1", name="bultos_positivos"),
        CheckConstraint("oficina_origen_id <> oficina_destino_id", name="oficinas_distintas"),
        CheckConstraint(
            "modalidad_entrega = 'retiro_en_oficina' OR direccion_entrega IS NOT NULL",
            name="direccion_si_puerta_a_puerta",
        ),
    )

    numero_guia: Mapped[str] = mapped_column(String(10), unique=True)
    tipo_envio: Mapped[TipoEnvio] = mapped_column(pg_enum(TipoEnvio))
    remitente_cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    cuenta_corporativa_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cuentas_corporativas.id"))
    destinatario_nombre: Mapped[str] = mapped_column(String(160))
    destinatario_tipo_documento: Mapped[TipoDocumento | None] = mapped_column(pg_enum(TipoDocumento))
    destinatario_numero_documento: Mapped[str | None] = mapped_column(String(20))
    destinatario_telefono_e164: Mapped[str] = mapped_column(String(15), index=True)
    oficina_origen_id: Mapped[int] = mapped_column(ForeignKey("oficinas.id"))
    oficina_destino_id: Mapped[int] = mapped_column(ForeignKey("oficinas.id"))
    modalidad_entrega: Mapped[ModalidadEntrega] = mapped_column(
        pg_enum(ModalidadEntrega), server_default=ModalidadEntrega.retiro_en_oficina.value
    )
    direccion_entrega: Mapped[str | None] = mapped_column(String(250))
    referencia_entrega: Mapped[str | None] = mapped_column(String(250))
    descripcion_contenido: Mapped[str] = mapped_column(String(250))
    cantidad_bultos: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    largo_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    ancho_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    alto_cm: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    valor_declarado_bs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    es_fragil: Mapped[bool] = mapped_column(server_default=text("false"))
    es_mudanza: Mapped[bool] = mapped_column(server_default=text("false"))
    precio_bs: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    pago_en: Mapped[PagoEn] = mapped_column(pg_enum(PagoEn), server_default=PagoEn.origen.value)
    estado_pago: Mapped[EstadoPago] = mapped_column(pg_enum(EstadoPago), server_default=EstadoPago.pendiente.value)
    estado: Mapped[EstadoEncomienda] = mapped_column(
        pg_enum(EstadoEncomienda), server_default=EstadoEncomienda.registrada.value, index=True
    )
    salida_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("salidas.id"), index=True)
    vehiculo_carga_id: Mapped[int | None] = mapped_column(ForeignKey("vehiculos_carga.id"))
    codigo_retiro: Mapped[str | None] = mapped_column(String(4))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_estimada_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entregado_a_nombre: Mapped[str | None] = mapped_column(String(160))
    entregado_a_documento: Mapped[str | None] = mapped_column(String(20))
    registrada_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    observaciones: Mapped[str | None] = mapped_column(Text)
    es_dato_demo: Mapped[bool] = mapped_column(server_default=text("true"))

    remitente: Mapped[Cliente] = relationship()
    oficina_origen: Mapped[Oficina] = relationship(foreign_keys=[oficina_origen_id])
    oficina_destino: Mapped[Oficina] = relationship(foreign_keys=[oficina_destino_id])
    eventos: Mapped[list["EncomiendaEvento"]] = relationship(
        back_populates="encomienda",
        cascade="all, delete-orphan",
        order_by="EncomiendaEvento.ocurrido_at",
    )


class EncomiendaEvento(Base):
    __tablename__ = "encomienda_eventos"
    __table_args__ = (
        Index(
            "ix_encomienda_eventos_encomienda_ocurrido",
            "encomienda_id",
            text("ocurrido_at DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    encomienda_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("encomiendas.id", ondelete="CASCADE"))
    estado: Mapped[EstadoEncomienda] = mapped_column(pg_enum(EstadoEncomienda))
    oficina_id: Mapped[int | None] = mapped_column(ForeignKey("oficinas.id"))
    ciudad_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    descripcion: Mapped[str] = mapped_column(String(250))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    ocurrido_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    registrado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    visible_cliente: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    encomienda: Mapped[Encomienda] = relationship(back_populates="eventos")
    ciudad: Mapped[Ciudad | None] = relationship()
    oficina: Mapped[Oficina | None] = relationship()


class SolicitudPuertaAPuerta(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "solicitudes_puerta_a_puerta"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'recojo' AND franja = 'tarde_14_17') OR (tipo = 'entrega' AND franja = 'manana_08_12')",
            name="franja_segun_tipo",
        ),
        CheckConstraint("EXTRACT(ISODOW FROM fecha_programada) BETWEEN 1 AND 5", name="dia_habil"),
        CheckConstraint("peso_estimado_kg IS NULL OR peso_estimado_kg >= 1", name="peso_minimo"),
        Index("ix_solicitudes_puerta_ciudad_fecha", "ciudad_id", "fecha_programada"),
    )

    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    tipo: Mapped[TipoSolicitudPuerta] = mapped_column(pg_enum(TipoSolicitudPuerta))
    ciudad_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ciudades.id"))
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes.id"), index=True)
    contacto_telefono_e164: Mapped[str] = mapped_column(String(15))
    direccion: Mapped[str] = mapped_column(String(250))
    referencia: Mapped[str | None] = mapped_column(String(250))
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    fecha_programada: Mapped[date]
    franja: Mapped[FranjaHoraria] = mapped_column(pg_enum(FranjaHoraria))
    peso_estimado_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    descripcion: Mapped[str | None] = mapped_column(String(250))
    encomienda_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("encomiendas.id"))
    vehiculo_carga_id: Mapped[int | None] = mapped_column(ForeignKey("vehiculos_carga.id"))
    repartidor_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    estado: Mapped[EstadoSolicitudPuerta] = mapped_column(
        pg_enum(EstadoSolicitudPuerta), server_default=EstadoSolicitudPuerta.solicitada.value
    )
    canal: Mapped[CanalVenta] = mapped_column(pg_enum(CanalVenta), server_default=CanalVenta.whatsapp_chat.value)
    costo_bs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    ciudad: Mapped[Ciudad] = relationship()
    cliente: Mapped[Cliente] = relationship()
