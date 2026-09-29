"""Reglas reales de puerta a puerta: Sucre y Santa Cruz, lunes a viernes, franja según el tipo."""

from app.utils.fechas import hoy
from tests.conftest import proximo_dia_habil, proximo_sabado


def solicitud(**extra) -> dict:
    return {
        "tipo": "recojo",
        "ciudad": "Sucre",
        "cliente": {"numero_documento": "9000001", "nombres": "Pedro", "apellidos": "Coca"},
        "telefono": "70055566",
        "direccion": "Calle Bolívar 123",
        "fecha_programada": proximo_dia_habil(hoy(), saltar=1).isoformat(),
        "peso_estimado_kg": 3,
        **extra,
    }


async def test_recojo_valido_asigna_franja_de_tarde(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud())
    assert r.status_code == 201, r.text
    assert r.json()["franja"] == "tarde_14_17" and r.json()["codigo"].startswith("PP-")
    assert r.json()["costo_bs"] == 20


async def test_entrega_asigna_franja_de_manana(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud(tipo="entrega", ciudad="santa cruz"))
    assert r.status_code == 201 and r.json()["franja"] == "manana_08_12"


async def test_fin_de_semana_rechazado(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud(fecha_programada=proximo_sabado(hoy()).isoformat()))
    assert r.status_code == 422 and r.json()["error"] == "dia_no_habil"


async def test_feriado_rechazado(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud(fecha_programada="2026-11-02"))
    assert r.status_code == 422 and "feriado" in r.json()["mensaje"]


async def test_ciudad_sin_servicio(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud(ciudad="Tarija"))
    assert r.status_code == 422 and r.json()["error"] == "sin_puerta_a_puerta"


async def test_peso_minimo(client):
    r = await client.post("/api/v1/puerta-a-puerta", json=solicitud(peso_estimado_kg=0.5))
    assert r.status_code == 422
