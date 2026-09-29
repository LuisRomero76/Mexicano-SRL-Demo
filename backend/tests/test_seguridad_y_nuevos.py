"""Sesión por cookie + CSRF, límite de intentos, cabeceras de seguridad y endpoints para el frontend."""

from datetime import timedelta

import pytest

from app.core.config import get_settings
from app.core.ratelimit import Limitador, limitador
from app.utils.fechas import hoy
from tests.conftest import PASSWORD_DEMO


async def test_login_con_cookie_y_csrf(client):
    import httpx

    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as navegador:
        r = await navegador.post(
            "/api/v1/auth/login", data={"username": "supervisor@elmexicanosrl.com", "password": PASSWORD_DEMO}
        )
        assert r.status_code == 200
        cookie = r.headers["set-cookie"].lower()
        assert "em_session=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
        assert "path=/api" in cookie
        # La cookie se envía sola: GET permitido sin cabecera extra.
        assert (await navegador.get("/api/v1/auth/me")).status_code == 200
        # Escritura con cookie sin X-Requested-With: rechazada (CSRF).
        r = await navegador.patch("/api/v1/admin/parametros/boletos_max_por_venta", json={"valor": 6})
        assert r.status_code == 403 and r.json()["error"] == "csrf"
        r = await navegador.post(
            "/api/v1/admin/salidas/generar",
            json={"desde": hoy().isoformat(), "hasta": hoy().isoformat()},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        assert r.status_code == 201
        # Cerrar sesión borra la cookie.
        r = await navegador.post("/api/v1/auth/logout")
        assert r.status_code == 204
        navegador.cookies.clear()
        assert (await navegador.get("/api/v1/auth/me")).status_code == 401


async def test_cabeceras_de_seguridad(client):
    r = await client.get("/api/v1/empresa")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    r = await client.get("/api/v1/reservas/MX7K2P", params={"documento": "0"})
    assert r.headers["cache-control"] == "no-store"


def test_limitador_bloquea_y_libera():
    lim = Limitador()
    assert [lim.registrar("x", 3, 60) for _ in range(3)] == [0, 0, 0]
    assert lim.registrar("x", 3, 60) > 0
    assert lim.registrar("otra-ip", 3, 60) == 0


async def test_login_limita_intentos(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    limitador.reiniciar()
    try:
        codigos = []
        for _ in range(11):
            r = await client.post("/api/v1/auth/login", data={"username": "nadie@x.com", "password": "mala"})
            codigos.append(r.status_code)
        assert codigos[:10] == [401] * 10 and codigos[10] == 429
        assert int(r.headers["retry-after"]) > 0
    finally:
        limitador.reiniciar()


async def test_calendario_y_proximas(client):
    r = await client.get("/api/v1/salidas/calendario", params={"origen": "Sucre", "destino": "Santa Cruz"})
    assert r.status_code == 200
    dias = r.json()["dias"]
    assert len(dias) == 7 and dias[0]["fecha"] == hoy().isoformat()
    futuros = [d for d in dias[2:] if d["disponible"]]
    assert futuros and all(d["precio_desde_bs"] >= 130 for d in futuros)

    r = await client.get("/api/v1/salidas/proximas", params={"limite": 5})
    assert r.status_code == 200 and 1 <= len(r.json()) <= 5
    assert all(s["estado"] != "llegada" for s in r.json())


async def test_rutas_con_precio_desde_y_feriados(client):
    rutas = {r["codigo"]: r for r in (await client.get("/api/v1/rutas")).json()}
    assert rutas["SRE-SCZ"]["precio_desde_bs"] == 150 and rutas["SRE-TJA"]["precio_desde_bs"] == 120
    r = await client.get("/api/v1/feriados", params={"desde": "2026-11-01", "hasta": "2026-11-30"})
    fechas = {f["fecha"] for f in r.json()}
    assert "2026-11-02" in fechas and "2026-11-10" in fechas


async def test_resumen_del_tablero_para_cualquier_rol(client, boletero):
    r = await client.get("/api/v1/admin/reportes/resumen", headers=boletero)
    assert r.status_code == 200
    datos = r.json()
    assert len(datos["ventas_7_dias"]) == 7
    assert {"salidas_hoy", "novedades", "encomiendas_por_estado", "ocupacion_hoy_pct"} <= set(datos)
    assert any(n["estado"] == "demorada" for n in datos["novedades"])


async def test_directorio_y_ocupacion_en_listado(client, bodega, supervisor):
    r = await client.get("/api/v1/admin/usuarios/directorio", params={"rol": "repartidor"}, headers=bodega)
    assert r.status_code == 200 and len(r.json()) == 2 and "email" not in r.json()[0]
    r = await client.get(
        "/api/v1/admin/salidas", params={"fecha": (hoy() + timedelta(days=2)).isoformat()}, headers=supervisor
    )
    item = r.json()["items"][0]
    assert item["asientos_total"] == 48 and item["asientos_ocupados"] is not None


async def test_busqueda_de_encomiendas(client, bodega):
    r = await client.get("/api/v1/admin/encomiendas", params={"q": "2600010"}, headers=bodega)
    assert r.status_code == 200 and r.json()["total"] >= 6


async def test_reembolsos_con_detalle(client, supervisor):
    items = (await client.get("/api/v1/admin/reembolsos", headers=supervisor)).json()["items"]
    assert items and all(i["numero_boleto"] and i["pasajero"] and i["codigo_reserva"] for i in items)


@pytest.mark.parametrize("password", ["corta1", "sinnumerosaqui"])
async def test_politica_de_contrasenas(client, admin, password):
    r = await client.post(
        "/api/v1/admin/usuarios",
        json={
            "email": "nuevo@elmexicanosrl.com",
            "password": password,
            "nombres": "A",
            "apellidos": "B",
            "rol": "soporte",
        },
        headers=admin,
    )
    assert r.status_code == 422


async def test_vistas_internas_para_el_panel(client, supervisor, bodega):
    # Encomienda: códigos de oficina y ciudades para filtrar salidas al despachar.
    r = await client.get("/api/v1/admin/encomiendas/26000101", headers=bodega)
    assert r.status_code == 200
    e = r.json()
    assert e["ciudad_origen"] and e["ciudad_destino"] and e["oficina_origen_codigo"]
    # Puerta a puerta: la vista interna incluye la asignación; la pública no.
    r = await client.get("/api/v1/admin/puerta-a-puerta", headers=bodega, params={"limit": 5})
    assert r.status_code == 200
    if r.json()["items"]:
        assert "repartidor" in r.json()["items"][0]
    # Auditoría: nombre del usuario y lista de tablas.
    r = await client.get("/api/v1/admin/auditoria", headers=supervisor, params={"limit": 5})
    assert r.status_code == 200 and "usuario" in r.json()["items"][0]
    r = await client.get("/api/v1/admin/auditoria/tablas", headers=supervisor)
    assert r.status_code == 200 and isinstance(r.json(), list)
    # Categorías de FAQ con id (el panel las usa al crear preguntas).
    r = await client.get("/api/v1/faqs")
    assert all(c["id"] for c in r.json())


async def test_supervisor_edita_paginas(client, supervisor, boletero):
    r = await client.put("/api/v1/admin/paginas/terminos", headers=boletero, json={"titulo": "X"})
    assert r.status_code == 403
    original = (await client.get("/api/v1/paginas/terminos")).json()["titulo"]
    r = await client.put("/api/v1/admin/paginas/terminos", headers=supervisor, json={"titulo": original})
    assert r.status_code == 200
