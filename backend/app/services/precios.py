"""Precios de pasajes.

Regla (sección C8 del diseño):
1. Precio adulto = override de la salida (`precios_salida`) o, si no hay, la tarifa vigente a la fecha de la salida.
2. Tarifas especiales: descuento sobre la tarifa máxima referencial; si el precio adulto es menor, se cobra ese.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoEncontrado
from app.models import PoliticaTipoPasajero, PrecioSalida, Salida, TarifaPasaje
from app.models.enums import TipoPasajero
from app.utils.fechas import a_local

CENTAVO = Decimal("0.01")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PrecioBase:
    precio_adulto_bs: Decimal
    precio_maximo_referencial_bs: Decimal
    es_precio_especial_salida: bool


@dataclass(frozen=True)
class PrecioBoleto:
    precio_bs: Decimal
    descuento_bs: Decimal

    @property
    def total_bs(self) -> Decimal:
        return self.precio_bs - self.descuento_bs


async def tarifa_vigente(session: AsyncSession, salida: Salida, tipo_asiento_id: int) -> TarifaPasaje:
    fecha = a_local(salida.fecha_hora_salida).date()
    tarifa = await session.scalar(
        select(TarifaPasaje)
        .where(
            TarifaPasaje.ruta_id == salida.ruta_id,
            TarifaPasaje.tipo_asiento_id == tipo_asiento_id,
            TarifaPasaje.vigente_desde <= fecha,
            or_(TarifaPasaje.vigente_hasta.is_(None), TarifaPasaje.vigente_hasta >= fecha),
        )
        .order_by(TarifaPasaje.vigente_desde.desc())
        .limit(1)
    )
    if not tarifa:
        raise NoEncontrado("No hay tarifa vigente para esa clase en esta salida.", codigo="sin_tarifa")
    return tarifa


async def precio_base(session: AsyncSession, salida: Salida, tipo_asiento_id: int) -> PrecioBase:
    tarifa = await tarifa_vigente(session, salida, tipo_asiento_id)
    override = await session.get(PrecioSalida, (salida.id, tipo_asiento_id))
    return PrecioBase(
        precio_adulto_bs=override.precio_bs if override else tarifa.precio_bs,
        precio_maximo_referencial_bs=tarifa.precio_maximo_referencial_bs,
        es_precio_especial_salida=override is not None,
    )


def aplicar_politica(base: PrecioBase, politica: PoliticaTipoPasajero | None) -> PrecioBoleto:
    """Calcula el precio de un boleto según el tipo de pasajero (función pura, fácil de testear)."""
    porcentaje = politica.descuento_porcentaje if politica else Decimal(0)
    if porcentaje <= 0:
        return PrecioBoleto(precio_bs=base.precio_adulto_bs, descuento_bs=Decimal("0.00"))

    maximo = base.precio_maximo_referencial_bs
    descuento = redondear(maximo * porcentaje / 100)
    if base.precio_adulto_bs <= maximo - descuento:
        # El precio de venta ya es más bajo que la tarifa con descuento de ley: se cobra el menor.
        return PrecioBoleto(precio_bs=base.precio_adulto_bs, descuento_bs=Decimal("0.00"))
    return PrecioBoleto(precio_bs=maximo, descuento_bs=descuento)


async def politicas(session: AsyncSession) -> dict[TipoPasajero, PoliticaTipoPasajero]:
    filas = (await session.scalars(select(PoliticaTipoPasajero))).all()
    return {p.tipo_pasajero: p for p in filas}
