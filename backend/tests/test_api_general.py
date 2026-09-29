"""Catálogos, datos reales, FAQ, autenticación, permisos y operación."""

from tests.conftest import PASSWORD_DEMO


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json()["base_de_datos"]["ok"]


async def test_datos_reales_de_la_empresa(client):
    e = (await client.get("/api/v1/empresa")).json()
    assert e["whatsapp_central_e164"] == "59171420823" and e["whatsapp_url"] == "https://wa.me/59171420823"
    assert e["url_compra_pasajes"] == "https://elmexicano.pagoseguro.cloud/#/sale-tickets"


async def test_oficinas_reales_con_horario(client):
    oficinas = (await client.get("/api/v1/oficinas", params={"ciudad": "potosi"})).json()
    assert [o["codigo"] for o in oficinas] == ["PTS-BOD"]
    assert oficinas[0]["direccion"] == "Av. Las Banderas s/n" and oficinas[0]["horario_texto"] == "Lun–Sáb 08:00–18:00"
    todas = (await client.get("/api/v1/oficinas")).json()
    assert len(todas) == 14


async def test_rutas_y_paradas(client):
    rutas = {r["codigo"]: r for r in (await client.get("/api/v1/rutas")).json()}
    assert set(rutas) == {"SRE-SCZ", "SCZ-SRE", "SRE-TJA", "TJA-SRE", "SRE-LPZ", "LPZ-SRE"}
    assert rutas["SRE-SCZ"]["distancia_km"] == 661 and rutas["SRE-SCZ"]["duracion_texto"] == "14 h"
    assert [p["ciudad"] for p in rutas["SRE-TJA"]["paradas"]] == ["Potosí", "Camargo"]


async def test_tipos_de_asiento_con_comodidades_reales(client):
    tipos = {t["codigo"]: t for t in (await client.get("/api/v1/tipos-asiento")).json()}
    assert tipos["SUITE_CAMA"]["inclinacion_grados"] == 180 and tipos["LEITO_CAMA"]["planta"] == "baja"
    assert "tv_individual" in {c["codigo"] for c in tipos["SUITE_CAMA"]["comodidades"]}
    assert "tv_cabina" in {c["codigo"] for c in tipos["LEITO_CAMA"]["comodidades"]}


async def test_politicas(client):
    p = (await client.get("/api/v1/politicas")).json()
    assert p["equipaje_bodega_kg"] == 20 and p["equipaje_mano_kg"] == 5 and p["reembolso_porcentaje_cliente"] == 85
    menor = next(t for t in p["tipos_pasajero"] if t["tipo_pasajero"] == "menor")
    assert menor["descuento_porcentaje"] == 50 and menor["solo_boleteria"]


async def test_faqs_reales_y_busqueda(client):
    categorias = (await client.get("/api/v1/faqs")).json()
    assert sum(len(c["preguntas"]) for c in categorias) == 13
    r = (await client.get("/api/v1/faqs/buscar", params={"q": "¿puedo llevar a mi perro?"})).json()
    assert r["resultados"][0]["slug"] == "mascotas"
    r = (await client.get("/api/v1/faqs/buscar", params={"q": "devolución del pasaje"})).json()
    assert r["resultados"][0]["slug"] == "reembolsos"


async def test_login_y_permisos(client, boletero):
    r = await client.post("/api/v1/auth/login", data={"username": "admin@elmexicanosrl.com", "password": "mala"})
    assert r.status_code == 401 and r.json()["error"] == "credenciales_invalidas"
    r = await client.post("/api/v1/auth/login", data={"username": "ADMIN@elmexicanosrl.com", "password": PASSWORD_DEMO})
    assert r.status_code == 200
    assert (await client.get("/api/v1/admin/reportes/ocupacion")).status_code == 401
    assert (await client.get("/api/v1/admin/reportes/ocupacion", headers=boletero)).status_code == 403
    assert (await client.get("/api/v1/auth/me", headers=boletero)).json()["rol"] == "boletero"


async def test_crud_generico_y_auditoria(client, admin):
    r = await client.get("/api/v1/admin/oficinas", params={"tipo": "boleteria", "limit": 50}, headers=admin)
    assert r.status_code == 200 and r.json()["total"] == 6
    r = await client.patch("/api/v1/admin/parametros/reserva_expira_minutos", json={"valor": 20}, headers=admin)
    assert r.status_code == 200 and r.json()["valor"] == 20
    await client.patch("/api/v1/admin/parametros/reserva_expira_minutos", json={"valor": 15}, headers=admin)
    audit = (await client.get("/api/v1/admin/auditoria", params={"tabla": "parametros_negocio"}, headers=admin)).json()
    assert audit["total"] >= 2


async def test_manifiesto_y_tripulacion(client, supervisor):
    r = await client.get("/api/v1/admin/salidas", params={"estado": "en_ruta", "limit": 1}, headers=supervisor)
    salidas = r.json()["items"]
    if not salidas:  # depende de la hora a la que corren los tests
        r = await client.get("/api/v1/admin/salidas", params={"estado": "llegada", "limit": 1}, headers=supervisor)
        salidas = r.json()["items"]
    m = (await client.get(f"/api/v1/admin/salidas/{salidas[0]['id']}/manifiesto", headers=supervisor)).json()
    assert {t["rol"] for t in m["tripulacion"]} == {"conductor", "conductor_relevo"}
    assert m["total_pasajeros"] == len(m["pasajeros"])


async def test_cambio_de_bus_con_conflicto(client, supervisor):
    salidas = (
        await client.get("/api/v1/admin/salidas", params={"ruta": "SRE-SCZ", "limit": 12}, headers=supervisor)
    ).json()
    futura = next(s for s in salidas["items"] if s["estado"] == "programada")
    otra = next(s for s in salidas["items"] if s["estado"] == "programada" and s["codigo"] != futura["codigo"])
    buses = {b["numero_interno"]: b["id"] for b in (await client.get("/api/v1/admin/buses", headers=supervisor)).json()}
    # El bus de reserva (M-14) está libre: el cambio mueve a los pasajeros por número de asiento.
    r = await client.put(
        f"/api/v1/admin/salidas/{futura['id']}/bus", json={"bus_id": buses["M-14"]}, headers=supervisor
    )
    assert r.status_code == 200 and r.json()["bus"] == "M-14"
    # En mantenimiento no se puede asignar.
    r = await client.put(f"/api/v1/admin/salidas/{otra['id']}/bus", json={"bus_id": buses["M-13"]}, headers=supervisor)
    assert r.status_code == 422


async def test_reportes(client, supervisor):
    ventas = (await client.get("/api/v1/admin/reportes/ventas", headers=supervisor)).json()
    assert ventas["ventas"] > 0 and ventas["por_canal"]
    enc = (await client.get("/api/v1/admin/reportes/encomiendas", headers=supervisor)).json()
    assert enc["por_estado"]["entregada"] >= 1
