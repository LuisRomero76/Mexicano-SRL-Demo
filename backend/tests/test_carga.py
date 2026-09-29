"""Cotización, rastreo público (privacidad), guías de prueba y flujo de bodega."""

import pytest

from tests.conftest import TELEFONO_DEMO


@pytest.mark.parametrize(
    ("params", "total", "tipo"),
    [
        ({"peso_kg": 12}, 46.0, "paquete"),  # 25 + (12 - 5) × 3
        ({"peso_kg": 3}, 25.0, "paquete"),  # dentro del peso base
        ({"peso_kg": 12, "puerta_a_puerta": True}, 66.0, "paquete"),  # + 20
        ({"peso_kg": 40}, 142.5, "carga"),  # 120 + (40 - 31) × 2,5
        ({"peso_kg": 1, "tipo": "sobre"}, 15.0, "sobre"),
    ],
)
async def test_cotizacion(client, params, total, tipo):
    r = await client.get("/api/v1/carga/cotizar", params={"origen": "Sucre", "destino": "Santa Cruz", **params})
    assert r.status_code == 200, r.text
    assert r.json()["total_bs"] == total and r.json()["tipo_envio"] == tipo


@pytest.mark.parametrize(
    ("params", "error"),
    [
        ({"destino": "Santa Cruz", "peso_kg": 35, "tipo": "paquete"}, "peso_excede_paquete"),
        ({"destino": "Santa Cruz", "peso_kg": 20, "tipo": "carga"}, "peso_insuficiente_carga"),
        ({"destino": "Santa Cruz", "peso_kg": 3, "tipo": "sobre"}, "peso_excede_tipo"),
        ({"destino": "Potosí", "peso_kg": 5, "puerta_a_puerta": True}, "sin_puerta_a_puerta"),
        ({"destino": "Sucre", "peso_kg": 5}, "regla_de_negocio"),
    ],
)
async def test_cotizacion_invalida(client, params, error):
    r = await client.get("/api/v1/carga/cotizar", params={"origen": "Sucre", **params})
    assert r.status_code == 422 and r.json()["error"] == error


async def test_rastreo_publico_no_expone_datos_privados(client):
    r = await client.get("/api/v1/encomiendas/rastreo/26000101")
    assert r.status_code == 200
    cuerpo = r.text
    datos = r.json()
    assert datos["estado"] == "lista_para_retiro" and datos["lista_para_retiro"]
    assert datos["oficina_retiro"] == "Bodega Santa Cruz 2" and datos["horario_oficina"]
    assert "4821" not in cuerpo and TELEFONO_DEMO not in cuerpo and "Andrea" not in cuerpo
    assert "precio" not in cuerpo
    fechas = [e["ocurrido_at"] for e in datos["eventos"]]
    assert fechas == sorted(fechas, reverse=True) and fechas[0].endswith("-04:00")


async def test_guias_de_prueba(client):
    estados = {
        "26000102": "en_transito",
        "26000103": "entregada",
        "26000104": "en_reparto",
        "26000105": "lista_para_retiro",
        "26000106": "llegada_a_destino",
    }
    for guia, estado in estados.items():
        assert (await client.get(f"/api/v1/encomiendas/rastreo/{guia}")).json()["estado"] == estado
    r = (await client.get("/api/v1/encomiendas/rastreo/26000106")).json()
    assert r["pago_pendiente_en_destino"] and "pago pendiente" in r["mensaje"]


async def test_guia_inexistente_e_invalida(client):
    r = await client.get("/api/v1/encomiendas/rastreo/26000999")
    assert r.status_code == 404 and "8 dígitos" in r.json()["mensaje"]
    r = await client.get("/api/v1/encomiendas/rastreo/123")
    assert r.status_code == 422 and r.json()["error"] == "guia_invalida"


async def test_flujo_de_bodega(client, bodega, supervisor):
    nueva = {
        "remitente": {"numero_documento": "8000001", "nombres": "Rosa", "apellidos": "Flores", "telefono": "70011122"},
        "destinatario_nombre": "Luis Pérez",
        "destinatario_numero_documento": "8000002",
        "destinatario_telefono": "70033344",
        "oficina_origen_codigo": "SRE-BOD",
        "oficina_destino_codigo": "SCZ-BOD1",
        "descripcion_contenido": "Ropa",
        "peso_kg": 8,
        "pago_en": "destino",
    }
    assert (await client.post("/api/v1/admin/encomiendas", json=nueva)).status_code == 401
    r = await client.post("/api/v1/admin/encomiendas", json=nueva, headers=bodega)
    assert r.status_code == 201, r.text
    enc = r.json()
    guia, pin = enc["numero_guia"], enc["codigo_retiro"]
    assert len(guia) == 8 and enc["estado"] == "recibida_en_origen" and enc["precio_bs"] == 34.0
    assert enc["estado_pago"] == "pendiente" and enc["destinatario_telefono_e164"] == "59170033344"

    # No se puede saltar estados.
    r = await client.post(
        f"/api/v1/admin/encomiendas/{guia}/eventos", json={"estado": "lista_para_retiro"}, headers=bodega
    )
    assert r.status_code == 422 and r.json()["error"] == "transicion_invalida"

    # Despacho en un bus que va de Sucre a Santa Cruz y paso por los estados.
    salidas = (
        await client.get("/api/v1/salidas", params={"origen": "Sucre", "destino": "Santa Cruz", "fecha": _manana()})
    ).json()
    salida_id = salidas["salidas"][0]["id"]
    r = await client.post(f"/api/v1/admin/encomiendas/{guia}/despachar", json={"salida_id": salida_id}, headers=bodega)
    assert r.status_code == 200 and r.json()["salida_id"] == salida_id
    for estado in ("en_transito", "llegada_a_destino", "lista_para_retiro"):
        r = await client.post(f"/api/v1/admin/encomiendas/{guia}/eventos", json={"estado": estado}, headers=supervisor)
        assert r.status_code == 200, r.text

    entrega = {
        "codigo_retiro": "0000" if pin != "0000" else "1111",
        "recibido_por_nombre": "Luis Pérez",
        "recibido_por_documento": "8000002",
    }
    r = await client.post(f"/api/v1/admin/encomiendas/{guia}/entregar", json=entrega, headers=supervisor)
    assert r.status_code == 422 and r.json()["error"] == "codigo_retiro_incorrecto"

    entrega["codigo_retiro"] = pin
    r = await client.post(f"/api/v1/admin/encomiendas/{guia}/entregar", json=entrega, headers=supervisor)
    assert r.status_code == 422 and r.json()["error"] == "pago_pendiente"

    r = await client.post(
        f"/api/v1/admin/encomiendas/{guia}/entregar", json={**entrega, "metodo_pago": "efectivo"}, headers=supervisor
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "entregada" and r.json()["estado_pago"] == "aprobado"

    publico = (await client.get(f"/api/v1/encomiendas/rastreo/{guia}")).json()
    assert publico["estado"] == "entregada" and len(publico["eventos"]) == 6  # el despacho es interno


async def test_despacho_en_salida_que_no_conecta(client, bodega):
    nueva = {
        "remitente": {"numero_documento": "8000003", "nombres": "Ana", "apellidos": "Soliz", "telefono": "70011123"},
        "destinatario_nombre": "Juan Poma",
        "destinatario_telefono": "70033345",
        "oficina_origen_codigo": "SRE-BOD",
        "oficina_destino_codigo": "PTS-BOD",
        "descripcion_contenido": "Documentos",
        "peso_kg": 0.5,
        "tipo_envio": "sobre",
        "metodo_pago": "qr",
    }
    guia = (await client.post("/api/v1/admin/encomiendas", json=nueva, headers=bodega)).json()["numero_guia"]
    salidas = (
        await client.get("/api/v1/salidas", params={"origen": "Sucre", "destino": "La Paz", "fecha": _manana()})
    ).json()
    r = await client.post(
        f"/api/v1/admin/encomiendas/{guia}/despachar", json={"salida_id": salidas["salidas"][0]["id"]}, headers=bodega
    )
    assert r.status_code == 422 and r.json()["error"] == "salida_no_conecta"
    # Potosí es parada de Sucre → Tarija.
    salidas = (
        await client.get("/api/v1/salidas", params={"origen": "Sucre", "destino": "Tarija", "fecha": _manana()})
    ).json()
    r = await client.post(
        f"/api/v1/admin/encomiendas/{guia}/despachar", json={"salida_id": salidas["salidas"][-1]["id"]}, headers=bodega
    )
    assert r.status_code == 200


def _manana() -> str:
    from datetime import timedelta

    from app.utils.fechas import hoy

    return (hoy() + timedelta(days=2)).isoformat()
