"""Importa todos los modelos para registrarlos en `Base.metadata` (Alembic los necesita)."""

from app.models.base import Base
from app.models.carga import (
    CuentaCorporativa,
    Encomienda,
    EncomiendaEvento,
    SolicitudPuertaAPuerta,
    TarifaCarga,
)
from app.models.contenido import Faq, FaqCategoria, PaginaContenido
from app.models.empresa import Ciudad, Empresa, Feriado, HorarioOficina, Oficina, ParametroNegocio
from app.models.flota import Asiento, Bus, Comodidad, TipoAsiento, VehiculoCarga, tipo_asiento_comodidades
from app.models.pagos import Factura, Pago, Reembolso
from app.models.rutas import (
    PlantillaHorario,
    PoliticaTipoPasajero,
    PrecioSalida,
    Ruta,
    RutaParada,
    Salida,
    SalidaTripulacion,
    TarifaPasaje,
)
from app.models.usuarios import Auditoria, Usuario
from app.models.ventas import Boleto, Cliente, Equipaje, VentaPasaje

__all__ = [
    "Asiento",
    "Auditoria",
    "Base",
    "Boleto",
    "Bus",
    "Ciudad",
    "Cliente",
    "Comodidad",
    "CuentaCorporativa",
    "Empresa",
    "Encomienda",
    "EncomiendaEvento",
    "Equipaje",
    "Factura",
    "Faq",
    "FaqCategoria",
    "Feriado",
    "HorarioOficina",
    "Oficina",
    "Pago",
    "PaginaContenido",
    "ParametroNegocio",
    "PlantillaHorario",
    "PoliticaTipoPasajero",
    "PrecioSalida",
    "Reembolso",
    "Ruta",
    "RutaParada",
    "Salida",
    "SalidaTripulacion",
    "SolicitudPuertaAPuerta",
    "TarifaCarga",
    "TarifaPasaje",
    "TipoAsiento",
    "Usuario",
    "VehiculoCarga",
    "VentaPasaje",
    "tipo_asiento_comodidades",
]
