"""Esquemas de carga, encomiendas y puerta a puerta."""

import uuid
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

from app.models.enums import (
    CanalVenta,
    EstadoEncomienda,
    EstadoPago,
    EstadoSolicitudPuerta,
    FranjaHoraria,
    MetodoPago,
    ModalidadEntrega,
    PagoEn,
    TipoDocumento,
    TipoEnvio,
    TipoSolicitudPuerta,
)
from app.schemas.common import Esquema, FechaHora, Monto
from app.schemas.ventas import PersonaIn
from app.utils.telefonos import normalizar_e164


def _telefono_obligatorio(v: str) -> str:
    e164 = normalizar_e164(v)
    if not e164:
        raise ValueError("Teléfono inválido")
    return e164


Telefono = Annotated[str, AfterValidator(_telefono_obligatorio)]


class CotizacionOut(BaseModel):
    origen: str
    destino: str
    tipo_envio: TipoEnvio
    peso_kg: float
    puerta_a_puerta: bool
    precio_base_bs: Monto
    kg_adicionales: float
    precio_kg_adicional_bs: Monto
    cargo_peso_adicional_bs: Monto
    recargo_puerta_a_puerta_bs: Monto
    total_bs: Monto
    mensaje: str


class RemitenteIn(PersonaIn):
    telefono: Telefono


class EncomiendaIn(BaseModel):
    tipo_envio: TipoEnvio | None = Field(None, description="Si se omite se deduce del peso")
    remitente: RemitenteIn
    cuenta_corporativa_codigo: str | None = None
    destinatario_nombre: str = Field(min_length=3, max_length=160)
    destinatario_tipo_documento: TipoDocumento | None = TipoDocumento.ci
    destinatario_numero_documento: str | None = Field(None, max_length=20)
    destinatario_telefono: Telefono
    oficina_origen_codigo: str = Field(examples=["SRE-BOD"])
    oficina_destino_codigo: str = Field(examples=["SCZ-BOD2"])
    modalidad_entrega: ModalidadEntrega = ModalidadEntrega.retiro_en_oficina
    direccion_entrega: str | None = Field(None, max_length=250)
    referencia_entrega: str | None = Field(None, max_length=250)
    descripcion_contenido: str = Field(min_length=3, max_length=250)
    cantidad_bultos: int = Field(1, ge=1, le=500)
    peso_kg: float = Field(gt=0, le=20000)
    largo_cm: float | None = Field(None, gt=0)
    ancho_cm: float | None = Field(None, gt=0)
    alto_cm: float | None = Field(None, gt=0)
    valor_declarado_bs: float | None = Field(None, ge=0)
    es_fragil: bool = False
    es_mudanza: bool = False
    pago_en: PagoEn = PagoEn.origen
    metodo_pago: MetodoPago | None = Field(None, description="Obligatorio si pago_en = origen")
    observaciones: str | None = None

    @model_validator(mode="after")
    def _coherencia(self) -> "EncomiendaIn":
        if self.modalidad_entrega == ModalidadEntrega.puerta_a_puerta and not self.direccion_entrega:
            raise ValueError("La entrega puerta a puerta requiere dirección de entrega")
        if self.pago_en == PagoEn.origen and not self.metodo_pago:
            raise ValueError("Indica el método de pago (pago en origen)")
        if self.pago_en == PagoEn.credito_corporativo and not self.cuenta_corporativa_codigo:
            raise ValueError("El crédito corporativo requiere la cuenta corporativa")
        return self


class EventoIn(BaseModel):
    estado: EstadoEncomienda
    descripcion: str | None = Field(None, max_length=250, description="Si se omite se genera un texto amigable")
    oficina_codigo: str | None = None
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    visible_cliente: bool = True


class DespachoIn(BaseModel):
    salida_id: uuid.UUID


class EntregaIn(BaseModel):
    codigo_retiro: str = Field(min_length=4, max_length=4, description="PIN de 4 dígitos del destinatario")
    recibido_por_nombre: str = Field(min_length=3, max_length=160)
    recibido_por_documento: str = Field(min_length=4, max_length=20)
    metodo_pago: MetodoPago | None = Field(None, description="Si hay pago pendiente en destino")


class CobroIn(BaseModel):
    metodo: MetodoPago


class EventoOut(Esquema):
    estado: EstadoEncomienda
    descripcion: str
    ciudad: str | None = None
    ocurrido_at: FechaHora


class RastreoOut(BaseModel):
    """Vista pública: sin nombres, teléfonos, montos ni PIN."""

    numero_guia: str
    tipo_envio: TipoEnvio
    estado: EstadoEncomienda
    estado_legible: str
    ciudad_origen: str
    ciudad_destino: str
    modalidad_entrega: ModalidadEntrega
    lista_para_retiro: bool
    pago_pendiente_en_destino: bool
    oficina_retiro: str | None
    direccion_retiro: str | None
    telefono_oficina: str | None
    horario_oficina: str | None
    cantidad_bultos: int
    fecha_registro: FechaHora
    fecha_estimada_entrega: FechaHora | None
    fecha_entrega: FechaHora | None
    eventos: list[EventoOut]
    mensaje: str


class EncomiendaOut(Esquema):
    id: uuid.UUID
    numero_guia: str
    tipo_envio: TipoEnvio
    estado: EstadoEncomienda
    remitente: str
    destinatario_nombre: str
    destinatario_telefono_e164: str
    oficina_origen: str
    oficina_destino: str
    oficina_origen_codigo: str | None = None
    oficina_destino_codigo: str | None = None
    ciudad_origen: str | None = None
    ciudad_destino: str | None = None
    modalidad_entrega: ModalidadEntrega
    direccion_entrega: str | None
    referencia_entrega: str | None = None
    valor_declarado_bs: Monto | None = None
    vehiculo_carga_id: int | None = None
    descripcion_contenido: str
    cantidad_bultos: int
    peso_kg: float
    es_fragil: bool
    es_mudanza: bool
    precio_bs: Monto
    pago_en: PagoEn
    estado_pago: EstadoPago
    codigo_retiro: str | None
    salida_id: uuid.UUID | None
    fecha_registro: FechaHora
    fecha_estimada_entrega: FechaHora | None
    fecha_entrega: FechaHora | None
    entregado_a_nombre: str | None
    eventos: list[EventoOut]


# --- Puerta a puerta ---------------------------------------------------------------------------


class SolicitudPuertaIn(BaseModel):
    tipo: TipoSolicitudPuerta
    ciudad: str = Field(examples=["Sucre"])
    cliente: PersonaIn
    telefono: Telefono
    direccion: str = Field(min_length=5, max_length=250)
    referencia: str | None = Field(None, max_length=250)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    fecha_programada: date
    peso_estimado_kg: float | None = Field(None, ge=1, description="Desde 1 kg")
    descripcion: str | None = Field(None, max_length=250)
    numero_guia: str | None = Field(None, description="Para entregas: guía de la encomienda")


class SolicitudPuertaUpdate(BaseModel):
    estado: EstadoSolicitudPuerta | None = None
    repartidor_usuario_id: uuid.UUID | None = None
    vehiculo_carga_id: int | None = None


class SolicitudPuertaOut(Esquema):
    id: uuid.UUID
    codigo: str
    tipo: TipoSolicitudPuerta
    ciudad: str
    cliente: str
    contacto_telefono_e164: str
    direccion: str
    referencia: str | None
    fecha_programada: date
    franja: FranjaHoraria
    franja_texto: str
    peso_estimado_kg: float | None
    estado: EstadoSolicitudPuerta
    canal: CanalVenta
    costo_bs: Monto | None
    numero_guia: str | None
    mensaje: str


class SolicitudPuertaAdminOut(SolicitudPuertaOut):
    """Vista interna: incluye la asignación de repartidor y vehículo."""

    descripcion: str | None = None
    repartidor_usuario_id: uuid.UUID | None = None
    repartidor: str | None = None
    vehiculo_carga_id: int | None = None
    vehiculo: str | None = None
