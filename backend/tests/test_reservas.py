"""Búsqueda, disponibilidad de asientos (sin doble venta), pago simulado, tarifas especiales y reembolsos."""

import asyncio

from tests.conftest import DOC_DEMO
from tests.helpers import comprador, pasajero, salida_futura


async def test_busqueda_con_alias_y_mensaje(client):
    r = await client.get("/api/v1/salidas", params={"origen": "sre", "destino": "santa cruz de la sierra"})
    assert r.status_code == 200
    assert r.json()["ruta"] == "SRE-SCZ"
    assert "Sucre" in r.json()["mensaje"]


async def test_ruta_inexistente(client):
    r = await client.get("/api/v1/salidas", params={"origen": "Santa Cruz", "destino": "La Paz"})
    assert r.status_code == 422
    assert r.json()["error"] == "ruta_no_disponible"
    assert "siempre desde o hacia Sucre" in r.json()["mensaje"]


async def test_ciudad_desconocida(client):
    r = await client.get("/api/v1/salidas", params={"origen": "Sucre", "destino": "Cochabamba"})
    assert r.status_code == 404


async def test_reservar_pagar_y_no_doble_venta(client):
    salida_id, libres = await salida_futura(client, dias=12)
    asiento = libres["SUITE_CAMA"][0]
    datos = {"salida_id": salida_id, "comprador": comprador(), "pasajeros": [pasajero(asiento)]}

    r = await client.post("/api/v1/reservas", json=datos)
    assert r.status_code == 201, r.text
    reserva = r.json()
    assert reserva["estado"] == "pendiente_pago" and reserva["expira_at"]
    codigo = reserva["codigo_reserva"]
    assert not set(codigo) & set("01OIL")

    # El mismo asiento no se puede volver a vender.
    r = await client.post("/api/v1/reservas", json={**datos, "comprador": comprador("7000002")})
    assert r.status_code == 409 and r.json()["error"] == "asiento_ocupado"

    # Tarjeta terminada en 0002: rechazo simulado, la reserva sigue pendiente.
    r = await client.post(
        f"/api/v1/reservas/{codigo}/pagar", json={"metodo": "tarjeta_credito", "numero_tarjeta": "4000000000000002"}
    )
    assert r.status_code == 422 and r.json()["error"] == "pago_rechazado"

    # En línea no se acepta efectivo.
    r = await client.post(f"/api/v1/reservas/{codigo}/pagar", json={"metodo": "efectivo"})
    assert r.status_code == 422

    r = await client.post(
        f"/api/v1/reservas/{codigo}/pagar", json={"metodo": "tarjeta_debito", "numero_tarjeta": "4111 1111 1111 1111"}
    )
    assert r.status_code == 200, r.text
    pagada = r.json()
    assert pagada["estado"] == "pagada"
    assert pagada["pago"]["ultimos4_tarjeta"] == "1111"
    assert pagada["factura"]["numero_factura"] >= 1000
    assert pagada["boletos"][0]["estado"] == "emitido" and pagada["boletos"][0]["codigo_qr"].startswith("MX|")

    # Consultar exige el documento y no revela la reserva con otro documento.
    assert (await client.get(f"/api/v1/reservas/{codigo}", params={"documento": "999999"})).status_code == 404
    assert (await client.get(f"/api/v1/reservas/{codigo.lower()}", params={"documento": "7000001"})).status_code == 200


async def test_venta_concurrente_del_mismo_asiento(client):
    salida_id, libres = await salida_futura(client, dias=13)
    asiento = libres["LEITO_CAMA"][0]

    async def reservar(doc: str):
        return await client.post(
            "/api/v1/reservas",
            json={"salida_id": salida_id, "comprador": comprador(doc), "pasajeros": [pasajero(asiento, doc)]},
        )

    respuestas = await asyncio.gather(*(reservar(f"71000{i:02d}") for i in range(5)))
    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [201, 409, 409, 409, 409]


async def test_tarifas_especiales_solo_en_boleteria(client, boletero):
    salida_id, libres = await salida_futura(client, dias=14)
    menor = pasajero(
        libres["SUITE_CAMA"][0],
        "15999001",
        tipo_pasajero="menor",
        fecha_nacimiento="2018-03-10",
        permiso_viaje_numero="DNA-12345",
    )
    datos = {"salida_id": salida_id, "comprador": comprador("7000003"), "pasajeros": [menor]}

    r = await client.post("/api/v1/reservas", json=datos)
    assert r.status_code == 422 and r.json()["error"] == "tarifa_solo_boleteria"

    r = await client.post("/api/v1/admin/ventas", json=datos, headers=boletero)
    assert r.status_code == 201, r.text
    boleto = r.json()["boletos"][0]
    assert boleto["tipo_pasajero"] == "menor"
    assert boleto["precio_bs"] == 210 and boleto["descuento_bs"] == 105 and boleto["total_bs"] == 105

    # Boletería puede cobrar en efectivo.
    r = await client.post(
        f"/api/v1/admin/ventas/{r.json()['codigo_reserva']}/cobrar", json={"metodo": "efectivo"}, headers=boletero
    )
    assert r.status_code == 200 and r.json()["estado"] == "pagada"


async def test_menor_sin_permiso_y_edad_incorrecta(client, boletero):
    salida_id, libres = await salida_futura(client, dias=14)
    sin_permiso = pasajero(libres["SUITE_CAMA"][1], "15999002", tipo_pasajero="menor", fecha_nacimiento="2018-03-10")
    r = await client.post(
        "/api/v1/admin/ventas",
        json={"salida_id": salida_id, "comprador": comprador("7000004"), "pasajeros": [sin_permiso]},
        headers=boletero,
    )
    assert r.status_code == 422 and r.json()["error"] == "falta_permiso_viaje"

    mayor = pasajero(libres["SUITE_CAMA"][1], "15999003", tipo_pasajero="adulto_mayor", fecha_nacimiento="1990-01-01")
    r = await client.post(
        "/api/v1/admin/ventas",
        json={"salida_id": salida_id, "comprador": comprador("7000004"), "pasajeros": [mayor]},
        headers=boletero,
    )
    assert r.status_code == 422 and "no corresponde" in r.json()["mensaje"]


async def test_embarazada_mas_de_30_semanas(client):
    salida_id, libres = await salida_futura(client, dias=15)
    p = pasajero(libres["LEITO_CAMA"][0], "7000005", tipo_pasajero="embarazada", semanas_gestacion=32)
    r = await client.post(
        "/api/v1/reservas", json={"salida_id": salida_id, "comprador": comprador("7000005"), "pasajeros": [p]}
    )
    assert r.status_code == 422 and r.json()["error"] == "gestacion_excedida"


async def test_reservas_de_prueba_fijas(client):
    r = await client.get("/api/v1/reservas/MX7K2P", params={"documento": DOC_DEMO})
    assert r.status_code == 200 and r.json()["estado"] == "pagada" and len(r.json()["boletos"]) == 2

    r = await client.get("/api/v1/reservas/MX3T8W", params={"documento": DOC_DEMO})
    assert r.json()["salida"]["estado"] == "demorada" and r.json()["salida"]["minutos_demora"] == 45
    assert "demora de 45 minutos" in r.json()["mensaje"]

    r = await client.get("/api/v1/reservas/MX9H4R", params={"documento": DOC_DEMO})
    assert r.json()["estado"] == "pendiente_pago"


async def test_reembolso_85_por_ciento(client):
    salida_id, libres = await salida_futura(client, dias=16)
    datos = {
        "salida_id": salida_id,
        "comprador": comprador("7000006"),
        "pasajeros": [pasajero(libres["SUITE_CAMA"][0], "7000006")],
    }
    codigo = (await client.post("/api/v1/reservas", json=datos)).json()["codigo_reserva"]
    pagada = (await client.post(f"/api/v1/reservas/{codigo}/pagar", json={"metodo": "qr"})).json()
    boleto = pagada["boletos"][0]

    r = await client.post(
        f"/api/v1/boletos/{boleto['numero_boleto']}/reembolso",
        json={"documento": "7000006", "motivo": "Cambio de planes"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["monto_bs"] == round(boleto["total_bs"] * 0.85, 2)
    assert r.json()["porcentaje_retencion"] == 15

    # El asiento queda libre otra vez.
    detalle = (await client.get(f"/api/v1/salidas/{salida_id}")).json()
    asiento = next(a for a in detalle["asientos"] if a["numero"] == boleto["numero_asiento"])
    assert asiento["estado"] == "libre"


async def test_cancelacion_de_salida_reembolsa_100(client, supervisor):
    salida_id, libres = await salida_futura(client, "La Paz", "Sucre", dias=18)
    datos = {
        "salida_id": salida_id,
        "comprador": comprador("7000007"),
        "pasajeros": [pasajero(libres["LEITO_CAMA"][0], "7000007")],
    }
    codigo = (await client.post("/api/v1/reservas", json=datos)).json()["codigo_reserva"]
    await client.post(f"/api/v1/reservas/{codigo}/pagar", json={"metodo": "tigo_money"})

    r = await client.post(f"/api/v1/admin/salidas/{salida_id}/estado", json={"estado": "cancelada"}, headers=supervisor)
    assert r.status_code == 422  # falta el motivo
    r = await client.post(
        f"/api/v1/admin/salidas/{salida_id}/estado",
        json={"estado": "cancelada", "motivo": "Paro de transporte"},
        headers=supervisor,
    )
    assert r.status_code == 200 and r.json()["estado"] == "cancelada"

    reserva = (await client.get(f"/api/v1/reservas/{codigo}", params={"documento": "7000007"})).json()
    assert reserva["estado"] == "reembolsada" and reserva["boletos"][0]["estado"] == "reembolsado"
    reembolsos = (await client.get("/api/v1/admin/reembolsos", headers=supervisor)).json()["items"]
    assert any(x["origen"] == "cancelacion_empresa" and x["porcentaje_retencion"] == 0 for x in reembolsos)

    # Una salida cancelada no se vuelve a abrir.
    r = await client.post(
        f"/api/v1/admin/salidas/{salida_id}/estado", json={"estado": "programada"}, headers=supervisor
    )
    assert r.status_code == 422


async def test_expiracion_libera_asientos(client):
    from sqlalchemy import update

    from app.core.db import SessionLocal
    from app.models import VentaPasaje
    from app.services import reservas
    from app.utils.fechas import ahora

    salida_id, libres = await salida_futura(client, dias=17)
    asiento = libres["SUITE_CAMA"][0]
    datos = {"salida_id": salida_id, "comprador": comprador("7000008"), "pasajeros": [pasajero(asiento, "7000008")]}
    codigo = (await client.post("/api/v1/reservas", json=datos)).json()["codigo_reserva"]
    async with SessionLocal() as s:
        await s.execute(update(VentaPasaje).where(VentaPasaje.codigo_reserva == codigo).values(expira_at=ahora()))
        await s.commit()
        assert await reservas.expirar_vencidas(s) >= 1
    r = await client.get(f"/api/v1/reservas/{codigo}", params={"documento": "7000008"})
    assert r.json()["estado"] == "expirada"
    r = await client.post("/api/v1/reservas", json={**datos, "comprador": comprador("7000009")})
    assert r.status_code == 201


async def test_datos_invalidos(client):
    r = await client.post("/api/v1/reservas", json={"salida_id": "no-es-uuid", "comprador": {}, "pasajeros": []})
    assert r.status_code == 422 and r.json()["error"] == "datos_invalidos"
    assert isinstance(r.json()["detalle"], list)
