"""Cálculo de precios: override de salida vs. tarifa vigente y descuentos sobre la tarifa máxima."""

from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.services.precios import PrecioBase, aplicar_politica
from app.utils.fechas import hoy
from tests.helpers import salida_futura

BASE = PrecioBase(
    precio_adulto_bs=Decimal("180.00"), precio_maximo_referencial_bs=Decimal("210.00"), es_precio_especial_salida=False
)


def politica(pct: str):
    return SimpleNamespace(descuento_porcentaje=Decimal(pct))


def test_adulto_paga_precio_de_venta():
    p = aplicar_politica(BASE, politica("0"))
    assert (p.precio_bs, p.descuento_bs, p.total_bs) == (Decimal("180.00"), Decimal("0.00"), Decimal("180.00"))


def test_menor_50_por_ciento_sobre_tarifa_maxima():
    p = aplicar_politica(BASE, politica("50"))
    assert (p.precio_bs, p.descuento_bs, p.total_bs) == (Decimal("210.00"), Decimal("105.00"), Decimal("105.00"))


def test_adulto_mayor_20_por_ciento_sobre_tarifa_maxima():
    p = aplicar_politica(BASE, politica("20"))
    assert p.total_bs == Decimal("168.00")


def test_si_el_precio_de_venta_es_menor_se_cobra_el_menor():
    promo = PrecioBase(Decimal("150.00"), Decimal("210.00"), True)
    p = aplicar_politica(promo, politica("20"))  # 210 - 20% = 168 > 150
    assert (p.precio_bs, p.descuento_bs) == (Decimal("150.00"), Decimal("0.00"))


async def test_precio_especial_de_salida_prevalece_sobre_tarifa(client):
    """Los martes Sucre ↔ Santa Cruz tienen precio promocional (precios_salida) en los seeds."""
    dias = next(d for d in range(3, 10) if (hoy() + timedelta(days=d)).isoweekday() == 2)
    salida_id, _ = await salida_futura(client, dias=dias)
    precios = {p["tipo_asiento"]: p for p in (await client.get(f"/api/v1/salidas/{salida_id}")).json()["precios"]}
    assert precios["SUITE_CAMA"]["precio_bs"] == 160 and precios["SUITE_CAMA"]["es_precio_especial"]

    salida_id, _ = await salida_futura(client, dias=dias + 1)  # miércoles: tarifa vigente
    precios = {p["tipo_asiento"]: p for p in (await client.get(f"/api/v1/salidas/{salida_id}")).json()["precios"]}
    assert precios["SUITE_CAMA"]["precio_bs"] == 180 and not precios["SUITE_CAMA"]["es_precio_especial"]
