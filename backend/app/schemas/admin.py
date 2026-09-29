"""Esquemas de autenticación y de la API de operación (personal)."""

import uuid
from datetime import date, time
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.models.enums import (
    CanalVenta,
    EstadoBus,
    EstadoReembolso,
    EstadoSalida,
    EstadoVenta,
    OrigenReembolso,
    RolTripulacion,
    RolUsuario,
    ServicioOficina,
    TipoEnvio,
    TipoOficina,
    TipoVehiculoCarga,
)
from app.schemas.common import Esquema, FechaHora, Monto

# --- Auth --------------------------------------------------------------------------------------


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UsuarioOut(Esquema):
    id: uuid.UUID
    email: str
    nombres: str
    apellidos: str
    rol: RolUsuario
    oficina_id: int | None
    telefono_e164: str | None
    licencia_conducir: str | None = None
    ultimo_login_at: FechaHora | None = None
    activo: bool


class DirectorioOut(BaseModel):
    id: uuid.UUID
    nombre: str
    rol: RolUsuario
    oficina_id: int | None
    licencia_conducir: str | None


def _password_robusta(v: str | None) -> str | None:
    if v is not None and not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
        raise ValueError("La contraseña debe combinar letras y números")
    return v


class UsuarioIn(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=10), AfterValidator(_password_robusta)] = Field(
        description="Mínimo 10 caracteres, con letras y números"
    )
    nombres: str
    apellidos: str
    rol: RolUsuario
    oficina_id: int | None = None
    telefono_e164: str | None = None
    licencia_conducir: str | None = None


class UsuarioUpdate(BaseModel):
    nombres: str | None = None
    apellidos: str | None = None
    rol: RolUsuario | None = None
    oficina_id: int | None = None
    telefono_e164: str | None = None
    licencia_conducir: str | None = None
    activo: bool | None = None
    password: Annotated[str | None, Field(min_length=10), AfterValidator(_password_robusta)] = None


# --- Salidas -----------------------------------------------------------------------------------


class SalidaAdminOut(BaseModel):
    id: uuid.UUID
    codigo: str
    ruta: str
    origen: str
    destino: str
    fecha_hora_salida: FechaHora
    fecha_hora_llegada_estimada: FechaHora
    estado: EstadoSalida
    minutos_demora: int
    motivo_estado: str | None
    bus: str | None
    anden: str | None
    oficina_salida: str | None
    salida_real_at: FechaHora | None
    llegada_real_at: FechaHora | None
    asientos_ocupados: int | None = None
    asientos_total: int | None = None


class GenerarSalidasIn(BaseModel):
    desde: date
    hasta: date


class GenerarSalidasOut(BaseModel):
    creadas: int
    codigos: list[str]


class EstadoSalidaIn(BaseModel):
    estado: EstadoSalida
    minutos_demora: int | None = Field(None, ge=1, le=1440)
    motivo: str | None = Field(None, max_length=250)


class AsignarBusIn(BaseModel):
    bus_id: int


class MiembroTripulacionIn(BaseModel):
    usuario_id: uuid.UUID
    rol: RolTripulacion


class TripulacionIn(BaseModel):
    miembros: list[MiembroTripulacionIn] = Field(min_length=1, max_length=4)


class MiembroTripulacionOut(BaseModel):
    usuario_id: uuid.UUID
    nombre: str
    rol: RolTripulacion
    licencia_conducir: str | None


class PasajeroManifiesto(BaseModel):
    numero_asiento: int
    clase: str
    numero_boleto: str
    pasajero: str
    documento: str
    tipo_pasajero: str
    estado: str
    equipaje_kg: float


class EncomiendaManifiesto(BaseModel):
    numero_guia: str
    tipo_envio: TipoEnvio
    bultos: int
    peso_kg: float
    destino: str
    estado: str


class ManifiestoOut(BaseModel):
    salida: SalidaAdminOut
    tripulacion: list[MiembroTripulacionOut]
    pasajeros: list[PasajeroManifiesto]
    encomiendas: list[EncomiendaManifiesto]
    total_pasajeros: int
    total_encomiendas_kg: float


class PrecioSalidaIn(BaseModel):
    tipo_asiento_id: int
    precio_bs: Decimal = Field(gt=0)


# --- Ventas y reembolsos -----------------------------------------------------------------------


class VentaResumenOut(BaseModel):
    codigo_reserva: str
    estado: EstadoVenta
    canal: CanalVenta
    comprador: str
    total_bs: Monto
    created_at: FechaHora
    pagada_at: FechaHora | None


class ReembolsoIn(BaseModel):
    documento: str = Field(description="Documento del pasajero del boleto")
    motivo: str = Field(min_length=3, max_length=250)


class ReembolsoAdminIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=250)


class ResolverReembolsoIn(BaseModel):
    estado: EstadoReembolso
    nota: str | None = None


class ReembolsoOut(Esquema):
    id: uuid.UUID
    origen: OrigenReembolso
    estado: EstadoReembolso
    monto_original_bs: Monto
    porcentaje_retencion: float
    monto_bs: Monto
    motivo: str
    solicitado_at: FechaHora
    fecha_limite_pago: date | None
    resuelto_at: FechaHora | None
    numero_boleto: str | None = None
    pasajero: str | None = None
    codigo_reserva: str | None = None
    salida: str | None = None


# --- Catálogos (CRUD) --------------------------------------------------------------------------


class OficinaIn(BaseModel):
    ciudad_id: int
    codigo: str = Field(max_length=10)
    nombre: str
    tipo: TipoOficina
    direccion: str
    referencia: str | None = None
    telefono_e164: str | None = None
    whatsapp_e164: str | None = None
    email: EmailStr | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    url_mapa: str | None = None
    es_principal: bool = False
    es_dato_demo: bool = True
    activo: bool = True


class OficinaUpdate(BaseModel):
    nombre: str | None = None
    tipo: TipoOficina | None = None
    direccion: str | None = None
    referencia: str | None = None
    telefono_e164: str | None = None
    whatsapp_e164: str | None = None
    email: EmailStr | None = None
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    url_mapa: str | None = None
    es_principal: bool | None = None
    es_dato_demo: bool | None = None
    activo: bool | None = None


class OficinaAdminOut(Esquema):
    id: int
    ciudad_id: int
    codigo: str
    nombre: str
    tipo: TipoOficina
    direccion: str
    referencia: str | None
    telefono_e164: str | None
    whatsapp_e164: str | None
    url_mapa: str | None
    es_principal: bool
    es_dato_demo: bool
    activo: bool


class HorarioIn(BaseModel):
    servicio: ServicioOficina = ServicioOficina.general
    dia_semana: int = Field(ge=1, le=7)
    hora_apertura: time
    hora_cierre: time
    observacion: str | None = None


class BusIn(BaseModel):
    numero_interno: str = Field(max_length=10)
    placa: str = Field(pattern=r"^\d{3,4}[A-Z]{3}$", examples=["4521KDB"])
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = Field(None, ge=1990, le=2100)
    estado: EstadoBus = EstadoBus.operativo


class BusUpdate(BaseModel):
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = Field(None, ge=1990, le=2100)
    estado: EstadoBus | None = None
    activo: bool | None = None


class BusOut(Esquema):
    id: int
    numero_interno: str
    placa: str
    marca: str | None
    modelo: str | None
    anio: int | None
    pisos: int
    capacidad_total: int
    estado: EstadoBus
    activo: bool


class VehiculoIn(BaseModel):
    placa: str
    tipo: TipoVehiculoCarga
    capacidad_kg: int = Field(gt=0)
    ciudad_base_id: int | None = None


class VehiculoUpdate(BaseModel):
    capacidad_kg: int | None = Field(None, gt=0)
    ciudad_base_id: int | None = None
    ultima_latitud: Decimal | None = None
    ultima_longitud: Decimal | None = None
    activo: bool | None = None


class VehiculoOut(Esquema):
    id: int
    placa: str
    tipo: TipoVehiculoCarga
    capacidad_kg: int
    ciudad_base_id: int | None
    ultima_latitud: Decimal | None
    ultima_longitud: Decimal | None
    ultima_posicion_at: FechaHora | None
    activo: bool


class RutaUpdate(BaseModel):
    distancia_km: int | None = Field(None, gt=0)
    duracion_estimada_min: int | None = Field(None, gt=0)
    cargo_exceso_equipaje_kg_bs: Decimal | None = Field(None, ge=0)
    descripcion: str | None = None
    activo: bool | None = None


class RutaAdminOut(Esquema):
    id: int
    codigo: str
    origen_ciudad_id: int
    destino_ciudad_id: int
    distancia_km: int
    duracion_estimada_min: int
    cargo_exceso_equipaje_kg_bs: Monto
    descripcion: str | None
    activo: bool


class PlantillaIn(BaseModel):
    ruta_id: int
    hora_salida: time
    dias_semana: list[int] = Field(default=[1, 2, 3, 4, 5, 6, 7], min_length=1)
    oficina_salida_id: int | None = None
    vigente_desde: date
    vigente_hasta: date | None = None
    es_dato_demo: bool = True


class PlantillaUpdate(BaseModel):
    dias_semana: list[int] | None = None
    oficina_salida_id: int | None = None
    vigente_hasta: date | None = None
    activo: bool | None = None


class PlantillaOut(Esquema):
    id: int
    ruta_id: int
    hora_salida: time
    dias_semana: list[int]
    oficina_salida_id: int | None
    vigente_desde: date
    vigente_hasta: date | None
    activo: bool


class TarifaPasajeIn(BaseModel):
    ruta_id: int
    tipo_asiento_id: int
    precio_bs: Decimal = Field(gt=0)
    precio_maximo_referencial_bs: Decimal = Field(gt=0)
    vigente_desde: date
    vigente_hasta: date | None = None
    es_dato_demo: bool = True


class TarifaPasajeUpdate(BaseModel):
    precio_bs: Decimal | None = Field(None, gt=0)
    precio_maximo_referencial_bs: Decimal | None = Field(None, gt=0)
    vigente_hasta: date | None = None


class TarifaPasajeOut(Esquema):
    id: int
    ruta_id: int
    tipo_asiento_id: int
    precio_bs: Monto
    precio_maximo_referencial_bs: Monto
    vigente_desde: date
    vigente_hasta: date | None
    es_dato_demo: bool


class TarifaCargaIn(BaseModel):
    origen_ciudad_id: int
    destino_ciudad_id: int
    tipo_envio: TipoEnvio
    peso_min_kg: Decimal = Field(ge=0)
    peso_max_kg: Decimal | None = None
    precio_base_bs: Decimal = Field(gt=0)
    precio_kg_adicional_bs: Decimal = Field(0, ge=0)
    recargo_puerta_a_puerta_bs: Decimal = Field(0, ge=0)
    vigente_desde: date
    vigente_hasta: date | None = None
    es_dato_demo: bool = True


class TarifaCargaUpdate(BaseModel):
    peso_max_kg: Decimal | None = None
    precio_base_bs: Decimal | None = Field(None, gt=0)
    precio_kg_adicional_bs: Decimal | None = Field(None, ge=0)
    recargo_puerta_a_puerta_bs: Decimal | None = Field(None, ge=0)
    vigente_hasta: date | None = None


class TarifaCargaOut(Esquema):
    id: int
    origen_ciudad_id: int
    destino_ciudad_id: int
    tipo_envio: TipoEnvio
    peso_min_kg: float
    peso_max_kg: float | None
    precio_base_bs: Monto
    precio_kg_adicional_bs: Monto
    recargo_puerta_a_puerta_bs: Monto
    vigente_desde: date
    vigente_hasta: date | None


class FaqIn(BaseModel):
    categoria_id: int
    slug: str = Field(pattern=r"^[a-z0-9-]+$")
    pregunta: str
    respuesta: str
    respuesta_corta_voz: str | None = Field(None, max_length=400)
    palabras_clave: list[str] | None = None
    orden: int = 0
    es_dato_demo: bool = True


class FaqUpdate(BaseModel):
    pregunta: str | None = None
    respuesta: str | None = None
    respuesta_corta_voz: str | None = Field(None, max_length=400)
    palabras_clave: list[str] | None = None
    orden: int | None = None
    es_dato_demo: bool | None = None
    activo: bool | None = None


class FaqAdminOut(Esquema):
    id: int
    categoria_id: int
    slug: str
    pregunta: str
    respuesta: str
    respuesta_corta_voz: str | None
    palabras_clave: list[str] | None
    orden: int
    es_dato_demo: bool
    activo: bool


class PaginaUpdate(BaseModel):
    titulo: str | None = None
    meta_descripcion: str | None = None
    contenido_md: str | None = None


class ParametroOut(Esquema):
    clave: str
    valor: Any
    descripcion: str | None
    es_dato_demo: bool


class ParametroUpdate(BaseModel):
    valor: Any
    es_dato_demo: bool | None = None


class FeriadoIn(BaseModel):
    fecha: date
    nombre: str
    departamento: str | None = None


class CuentaCorporativaIn(BaseModel):
    codigo: str = Field(max_length=10)
    razon_social: str
    nit: str
    contacto_nombre: str | None = None
    contacto_telefono_e164: str | None = None
    contacto_email: EmailStr | None = None
    limite_credito_bs: Decimal = Field(0, ge=0)
    dias_credito: int = Field(30, ge=0)


class CuentaCorporativaUpdate(BaseModel):
    razon_social: str | None = None
    contacto_nombre: str | None = None
    contacto_telefono_e164: str | None = None
    contacto_email: EmailStr | None = None
    limite_credito_bs: Decimal | None = Field(None, ge=0)
    saldo_pendiente_bs: Decimal | None = Field(None, ge=0)
    dias_credito: int | None = Field(None, ge=0)
    activo: bool | None = None


class CuentaCorporativaOut(Esquema):
    id: uuid.UUID
    codigo: str
    razon_social: str
    nit: str
    contacto_nombre: str | None
    contacto_telefono_e164: str | None
    limite_credito_bs: Monto
    saldo_pendiente_bs: Monto
    dias_credito: int
    activo: bool


class ClienteOut(Esquema):
    id: uuid.UUID
    tipo_documento: str
    numero_documento: str
    complemento: str | None
    extension: str | None
    nombres: str
    apellidos: str
    fecha_nacimiento: date | None
    telefono_e164: str | None
    email: str | None


class AuditoriaOut(Esquema):
    id: int
    usuario_id: uuid.UUID | None
    accion: str
    tabla: str
    registro_id: str
    cambios: dict[str, Any] | None
    created_at: FechaHora
    usuario: str | None = None


class BotConsultaOut(Esquema):
    id: int
    tool: str
    caller_id: str | None
    parametros: dict[str, Any] | None
    encontrado: bool
    coincide_caller: bool | None
    resultado: dict[str, Any] | None
    codigo_http: int
    latencia_ms: int
    created_at: FechaHora


class AsignarVehiculoIn(BaseModel):
    vehiculo_id: int
