"""Esquemas de reservas, boletos y pagos de pasajes."""

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import (
    CanalVenta,
    EstadoBoleto,
    EstadoPago,
    EstadoSalida,
    EstadoVenta,
    MetodoPago,
    TipoDocumento,
    TipoEquipaje,
    TipoPasajero,
)
from app.schemas.common import Esquema, FechaHora, Monto
from app.utils.telefonos import normalizar_e164


class PersonaIn(BaseModel):
    tipo_documento: TipoDocumento = TipoDocumento.ci
    numero_documento: str = Field(min_length=4, max_length=20, examples=["7654321"])
    complemento: str | None = Field(None, max_length=5)
    extension: str | None = Field(None, max_length=3, examples=["CH"])
    nombres: str = Field(min_length=2, max_length=80)
    apellidos: str = Field(min_length=2, max_length=80)

    @field_validator("numero_documento", "complemento", "extension")
    @classmethod
    def _limpiar(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else None

    @field_validator("nombres", "apellidos")
    @classmethod
    def _titulo(cls, v: str) -> str:
        return " ".join(p.capitalize() for p in v.split())


class CompradorIn(PersonaIn):
    telefono: str = Field(description="Celular del comprador", examples=["+591 70000001"])
    email: EmailStr | None = Field(None, description="Para enviar el e-ticket")
    nit_facturacion: str | None = Field(None, max_length=20)
    razon_social_facturacion: str | None = Field(None, max_length=150)

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v: str) -> str:
        e164 = normalizar_e164(v)
        if not e164:
            raise ValueError("Teléfono inválido")
        return e164


class PasajeroIn(PersonaIn):
    numero_asiento: int = Field(ge=1, examples=[14])
    tipo_pasajero: TipoPasajero = TipoPasajero.adulto
    fecha_nacimiento: date | None = Field(None, description="Obligatoria para menores y adultos mayores")
    telefono: str | None = None
    email: EmailStr | None = None
    viaja_con_perro_guia: bool = Field(False, description="Única excepción a la prohibición de mascotas")
    semanas_gestacion: int | None = Field(None, ge=1, le=42, description="Solo embarazadas (máximo 30)")
    permiso_viaje_numero: str | None = Field(
        None, max_length=40, description="Permiso de Viaje de la Defensoría (menores)"
    )

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v: str | None) -> str | None:
        return normalizar_e164(v) if v else None


class ReservaIn(BaseModel):
    salida_id: uuid.UUID
    comprador: CompradorIn
    pasajeros: list[PasajeroIn] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def _asientos_unicos(self) -> "ReservaIn":
        numeros = [p.numero_asiento for p in self.pasajeros]
        if len(numeros) != len(set(numeros)):
            raise ValueError("Hay asientos repetidos en la reserva")
        return self


class PagoIn(BaseModel):
    metodo: MetodoPago
    numero_tarjeta: str | None = Field(
        None,
        description="Solo tarjetas. Simulación: nunca se guarda; una tarjeta terminada en 0002 es rechazada.",
        examples=["4111111111111111"],
    )
    nit_facturacion: str | None = Field(None, max_length=20)
    razon_social_facturacion: str | None = Field(None, max_length=150)

    @model_validator(mode="after")
    def _tarjeta(self) -> "PagoIn":
        if self.metodo in (MetodoPago.tarjeta_credito, MetodoPago.tarjeta_debito):
            digitos = "".join(c for c in (self.numero_tarjeta or "") if c.isdigit())
            if not 13 <= len(digitos) <= 19:
                raise ValueError("Número de tarjeta inválido")
            self.numero_tarjeta = digitos
        else:
            self.numero_tarjeta = None
        return self


class EquipajeIn(BaseModel):
    tipo: TipoEquipaje = TipoEquipaje.bodega
    peso_kg: float = Field(gt=0, le=100)
    piezas: int = Field(1, ge=1, le=10)
    descripcion: str | None = Field(None, max_length=150)


class AbordajeIn(BaseModel):
    codigo: str = Field(description="Número de boleto (B26001000) o contenido del QR")


# --- Salidas -----------------------------------------------------------------------------------


class ClaseDisponible(BaseModel):
    tipo_asiento_id: int
    codigo: str
    nombre: str
    precio_bs: Monto | None
    precio_maximo_referencial_bs: Monto | None
    asientos_libres: int
    asientos_total: int


class SalidaResumen(BaseModel):
    id: uuid.UUID
    codigo: str
    origen: str
    destino: str
    fecha_hora_salida: FechaHora
    fecha_hora_llegada_estimada: FechaHora
    estado: EstadoSalida
    minutos_demora: int
    anden: str | None
    bus: str | None
    vendible: bool
    clases: list[ClaseDisponible]


class BusquedaSalidasOut(BaseModel):
    ruta: str
    origen: str
    destino: str
    fecha: date
    distancia_km: int
    duracion_estimada_min: int
    salidas: list[SalidaResumen]
    mensaje: str


class AsientoMapa(BaseModel):
    numero: int
    planta: str
    fila: int
    columna: int
    posicion: str
    tipo_asiento: str
    estado: str = Field(description="libre | ocupado | no_disponible")


class PrecioClase(BaseModel):
    tipo_asiento: str
    nombre: str
    precio_bs: Monto
    precio_maximo_referencial_bs: Monto
    es_precio_especial: bool


class SalidaDetalleOut(BaseModel):
    salida: SalidaResumen
    precios: list[PrecioClase]
    asientos: list[AsientoMapa]


# --- Reservas ----------------------------------------------------------------------------------


class BoletoOut(Esquema):
    numero_boleto: str
    numero_asiento: int
    clase: str
    pasajero: str
    documento: str
    tipo_pasajero: TipoPasajero
    precio_bs: Monto
    descuento_bs: Monto
    total_bs: Monto
    estado: EstadoBoleto
    codigo_qr: str | None
    viaja_con_perro_guia: bool


class SalidaDeReserva(BaseModel):
    id: uuid.UUID
    codigo: str
    origen: str
    destino: str
    fecha_hora_salida: FechaHora
    fecha_hora_llegada_estimada: FechaHora
    estado: EstadoSalida
    minutos_demora: int
    anden: str | None
    oficina_salida: str | None
    direccion_salida: str | None


class FacturaOut(Esquema):
    numero_factura: int
    cuf: str | None
    nit_ci_cliente: str
    razon_social_cliente: str
    monto_total_bs: Monto
    fecha_emision: FechaHora


class PagoOut(Esquema):
    id: uuid.UUID
    metodo: MetodoPago
    monto_bs: Monto
    estado: EstadoPago
    ultimos4_tarjeta: str | None
    qr_payload: str | None
    pagado_at: FechaHora | None


class ReservaOut(BaseModel):
    codigo_reserva: str
    estado: EstadoVenta
    canal: CanalVenta
    comprador: str
    subtotal_bs: Monto
    descuento_bs: Monto
    total_bs: Monto
    expira_at: FechaHora | None
    pagada_at: FechaHora | None
    salida: SalidaDeReserva
    boletos: list[BoletoOut]
    pago: PagoOut | None = None
    factura: FacturaOut | None = None
    mensaje: str


class EquipajeOut(Esquema):
    etiqueta: str
    tipo: TipoEquipaje
    piezas: int
    peso_kg: float
    peso_permitido_kg: float
    exceso_kg: float
    cargo_exceso_bs: Monto
    descripcion: str | None


class DiaCalendario(BaseModel):
    fecha: date
    salidas: int
    precio_desde_bs: Monto | None
    disponible: bool


class CalendarioOut(BaseModel):
    ruta: str
    origen: str
    destino: str
    dias: list[DiaCalendario]
