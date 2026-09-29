"""Esquemas de catálogos públicos: empresa, ciudades, rutas, flota, oficinas, políticas y contenido."""

from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field

from app.models.enums import PlantaBus, TipoOficina, TipoPasajero
from app.schemas.common import Esquema, Monto
from app.utils.telefonos import formato_legible, url_whatsapp


class EmpresaOut(Esquema):
    razon_social: str
    nombre_comercial: str
    nit: str | None
    ente_regulador: str | None
    sitio_web: str | None
    url_compra_pasajes: str | None
    url_rastreo_carga: str | None
    facebook_url: str | None
    email_contacto: str | None
    telefono_central_e164: str | None
    telefono_atencion_cliente_e164: str | None
    whatsapp_central_e164: str | None
    color_marca: str | None
    eslogan: str | None
    descripcion: str | None
    moneda: str
    zona_horaria: str

    @computed_field
    @property
    def whatsapp_url(self) -> str | None:
        return url_whatsapp(self.whatsapp_central_e164)


class CiudadOut(Esquema):
    id: int
    codigo: str
    nombre: str
    departamento: str
    es_destino_pasajeros: bool
    es_destino_carga: bool
    tiene_puerta_a_puerta: bool
    whatsapp_puerta_a_puerta_e164: str | None


class ParadaOut(BaseModel):
    ciudad: str
    orden: int
    km_desde_origen: int
    minutos_desde_origen: int
    permite_pasajeros: bool


class RutaOut(BaseModel):
    id: int
    codigo: str
    origen: str
    destino: str
    distancia_km: int
    duracion_estimada_min: int
    duracion_texto: str
    cargo_exceso_equipaje_kg_bs: Monto
    precio_desde_bs: Monto | None = None
    horarios: list[str] = []
    paradas: list[ParadaOut]


class ComodidadOut(Esquema):
    codigo: str
    nombre: str
    icono: str | None


class TipoAsientoOut(Esquema):
    id: int
    codigo: str
    nombre: str
    planta: PlantaBus
    inclinacion_grados: int
    descripcion: str | None
    comodidades: list[ComodidadOut]


class OficinaOut(BaseModel):
    oficina_id: int
    codigo: str
    nombre: str
    tipo: TipoOficina
    ciudad: str
    direccion: str
    referencia: str | None
    telefono_e164: str | None
    whatsapp_e164: str | None
    url_mapa: str | None
    horario_texto: str | None

    @computed_field
    @property
    def telefono(self) -> str | None:
        return formato_legible(self.telefono_e164)


class HorarioOut(Esquema):
    servicio: str
    dia_semana: int
    hora_apertura: time
    hora_cierre: time


class OficinaDetalleOut(Esquema):
    id: int
    codigo: str
    nombre: str
    tipo: TipoOficina
    direccion: str
    referencia: str | None
    telefono_e164: str | None
    whatsapp_e164: str | None
    email: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    url_mapa: str | None
    es_principal: bool
    horarios: list[HorarioOut]


class PoliticaPasajeroOut(Esquema):
    tipo_pasajero: TipoPasajero
    nombre: str
    descuento_porcentaje: float
    solo_boleteria: bool
    edad_min: int | None
    edad_max: int | None
    requisito: str | None


class PoliticasOut(BaseModel):
    tipos_pasajero: list[PoliticaPasajeroOut]
    equipaje_bodega_kg: float
    equipaje_mano_kg: float
    reembolso_porcentaje_cliente: float
    reembolso_horas_minimas: int
    reembolso_porcentaje_cancelacion_empresa: float
    reembolso_dias_habiles_max: int
    embarazo_semanas_max: int
    reserva_expira_minutos: int
    boletos_max_por_venta: int
    mascotas: str = Field("No se permiten mascotas en cabina ni en bodega, salvo perros lazarillos junto a su dueño.")
    medios_de_pago_en_linea: list[str] = ["qr", "tarjeta_debito", "tarjeta_credito", "tigo_money"]


class FeriadoOut(Esquema):
    id: int
    fecha: date
    nombre: str
    departamento: str | None


# --- Contenido ---------------------------------------------------------------------------------


class FaqOut(Esquema):
    slug: str
    pregunta: str
    respuesta: str
    respuesta_corta_voz: str | None


class FaqCategoriaOut(BaseModel):
    id: int | None = None
    codigo: str
    nombre: str
    preguntas: list[FaqOut]


class FaqBusquedaOut(BaseModel):
    consulta: str
    resultados: list[FaqOut]
    mensaje: str


class PaginaOut(Esquema):
    slug: str
    titulo: str
    meta_descripcion: str | None
    contenido_md: str
    url_original: str | None
