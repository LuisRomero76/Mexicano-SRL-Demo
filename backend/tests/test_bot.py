"""API del agente de voz: autenticación por X-Bot-Key, privacidad por caller_id, mensajes para voz y registro."""

import json
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.ratelimit import limitador
from app.models import BotConsultaLog
from app.services import api_keys
from app.utils.fechas import hoy
from tests.conftest import TELEFONO_DEMO, proximo_dia_habil, proximo_sabado

OTRO_TELEFONO = "59179999999"


@pytest.fixture(scope="session")
async def claves():
    async with SessionLocal() as session:
        rw = await api_keys.crear_o_rotar(session, "tests-rw", [api_keys.SCOPE_LECTURA, api_keys.SCOPE_ESCRITURA])
        ro = await api_keys.crear_o_rotar(session, "tests-ro", [api_keys.SCOPE_LECTURA])
    return {"rw": {"X-Bot-Key": rw}, "ro": {"X-Bot-Key": ro}}


def _pequena(r) -> dict:
    assert r.status_code == 200, r.text
    assert len(r.content) < 1024, f"respuesta de {len(r.content)} bytes: {r.text}"
    cuerpo = r.json()
    assert cuerpo["mensaje"]
    assert "_coincide" not in cuerpo
    return cuerpo


def _sin_privados(cuerpo: dict) -> None:
    for campo in (
        "remitente",
        "destinatario",
        "monto_pendiente_bs",
        "total_bs",
        "ultimos_eventos",
        "direccion_entrega",
    ):
        assert campo not in cuerpo, campo
    texto = json.dumps(cuerpo, ensure_ascii=False).lower()
    for prohibido in ("4821", "3072", "bolivianos"):  # PIN de las guías 101 y 105, montos
        assert prohibido not in texto, prohibido


# --- Autenticación ---------------------------------------------------------------------------


async def test_sin_key_o_key_invalida_es_401(client):
    r = await client.get("/api/bot/empresa")
    assert r.status_code == 401 and r.json()["error"] == "bot_key_requerida"
    r = await client.get("/api/bot/empresa", headers={"X-Bot-Key": "emk_no-existe"})
    assert r.status_code == 401 and r.json()["error"] == "bot_key_invalida"


async def test_key_de_solo_lectura_no_puede_escribir(client, claves):
    r = await client.post("/api/bot/puerta-a-puerta", headers=claves["ro"], json={})
    assert r.status_code == 403 and r.json()["error"] == "bot_scope_insuficiente"


async def test_limite_por_api_key(client, claves, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    monkeypatch.setattr(get_settings(), "bot_rate_limit_por_minuto", 3)
    limitador.reiniciar()
    try:
        codigos = [(await client.get("/api/bot/empresa", headers=claves["ro"])).status_code for _ in range(4)]
        assert codigos == [200, 200, 200, 429]
        # El límite es por key, no por IP: otra key sigue respondiendo.
        assert (await client.get("/api/bot/empresa", headers=claves["rw"])).status_code == 200
    finally:
        limitador.reiniciar()


async def test_key_revocada_deja_de_funcionar(client):
    async with SessionLocal() as session:
        clave = await api_keys.crear_o_rotar(session, "tests-revocar", [api_keys.SCOPE_LECTURA])
    assert (await client.get("/api/bot/empresa", headers={"X-Bot-Key": clave})).status_code == 200
    async with SessionLocal() as session:
        assert await api_keys.revocar(session, "tests-revocar")
    assert (await client.get("/api/bot/empresa", headers={"X-Bot-Key": clave})).status_code == 401


# --- Encomiendas y privacidad ----------------------------------------------------------------


@pytest.mark.parametrize("caller", [TELEFONO_DEMO, "+" + TELEFONO_DEMO, TELEFONO_DEMO[3:], f"+591 {TELEFONO_DEMO[3:]}"])
async def test_guia_con_el_caller_del_destinatario_da_datos_completos(client, claves, caller):
    r = await client.get("/api/bot/encomiendas/26000101", headers=claves["ro"], params={"caller_id": caller})
    c = _pequena(r)
    assert c["encontrado"] and c["datos_completos"]
    assert c["estado"] == "lista_para_retiro" and c["lista_para_retiro"]
    assert c["remitente"] and c["destinatario"] and len(c["ultimos_eventos"]) <= 3
    assert "Tu encomienda" in c["mensaje"] and "código de retiro" in c["mensaje"]
    assert "4821" not in r.text  # el PIN nunca se dice por teléfono


async def test_guia_con_otro_caller_solo_da_el_estado(client, claves):
    r = await client.get("/api/bot/encomiendas/26000101", headers=claves["ro"], params={"caller_id": OTRO_TELEFONO})
    c = _pequena(r)
    assert c["encontrado"] and not c["datos_completos"]
    assert c["estado"] == "lista_para_retiro"
    assert c["oficina_retiro"]  # la oficina es información pública
    assert "llama desde el número registrado" in c["mensaje"]
    _sin_privados(c)


async def test_guia_de_otro_numero_con_el_caller_demo(client, claves):
    r = await client.get("/api/bot/encomiendas/26000105", headers=claves["ro"], params={"caller_id": TELEFONO_DEMO})
    c = _pequena(r)
    assert c["encontrado"] and not c["datos_completos"] and c["estado"] == "lista_para_retiro"
    _sin_privados(c)


async def test_sin_caller_se_trata_como_desconocido(client, claves):
    for valor in (None, "", "anonymous", "{{system__caller_id}}"):
        params = {"caller_id": valor} if valor is not None else {}
        c = _pequena(await client.get("/api/bot/encomiendas/26000106", headers=claves["ro"], params=params))
        assert not c["datos_completos"] and c["pago_pendiente"]
        _sin_privados(c)


async def test_pago_pendiente_con_monto_solo_para_el_caller(client, claves):
    c = _pequena(
        await client.get("/api/bot/encomiendas/26000106", headers=claves["ro"], params={"caller_id": TELEFONO_DEMO})
    )
    assert c["pago_pendiente"] and c["monto_pendiente_bs"] > 0 and "bolivianos" in c["mensaje"]


async def test_guia_inexistente_o_mal_dictada(client, claves):
    c = _pequena(await client.get("/api/bot/encomiendas/26000999", headers=claves["ro"]))
    assert c == {"encontrado": False, "mensaje": c["mensaje"]} and "8 dígitos" in c["mensaje"]
    c = _pequena(await client.get("/api/bot/encomiendas/2600", headers=claves["ro"]))
    assert not c["encontrado"] and "8 dígitos" in c["mensaje"]
    # Dictada con espacios: se entiende igual.
    c = _pequena(await client.get("/api/bot/encomiendas/26 000 101", headers=claves["ro"]))
    assert c["encontrado"]


async def test_mis_encomiendas(client, claves):
    c = _pequena(await client.get("/api/bot/encomiendas", headers=claves["ro"], params={"caller_id": TELEFONO_DEMO}))
    guias = {e["numero_guia"] for e in c["encomiendas"]}
    assert 1 <= len(guias) <= 5
    assert "26000103" not in guias and "26000105" not in guias  # entregada y de otro número
    assert all(e["estado"] not in ("entregada", "devuelta", "cancelada") for e in c["encomiendas"])
    c = _pequena(await client.get("/api/bot/encomiendas", headers=claves["ro"], params={"caller_id": OTRO_TELEFONO}))
    assert not c["encontrado"] and "guía" in c["mensaje"]
    c = _pequena(await client.get("/api/bot/encomiendas", headers=claves["ro"]))
    assert not c["encontrado"]


# --- Pasajes ---------------------------------------------------------------------------------


async def test_salidas_con_alias_y_manana(client, claves):
    r = await client.get(
        "/api/bot/salidas",
        headers=claves["ro"],
        params={"origen": "sucre", "destino": "Santa Cruz de la Sierra", "fecha": "mañana"},
    )
    c = _pequena(r)
    assert c["encontrado"] and c["fecha"] == (hoy() + timedelta(days=1)).isoformat()
    assert 1 <= len(c["salidas"]) <= 5
    assert "bolivianos" in c["mensaje"] and "mañana" in c["mensaje"]


async def test_salidas_ruta_inexistente_y_fecha_invalida(client, claves):
    c = _pequena(
        await client.get("/api/bot/salidas", headers=claves["ro"], params={"origen": "Sucre", "destino": "Potosí"})
    )
    assert not c["encontrado"] and "Sucre" in c["mensaje"]
    c = _pequena(
        await client.get(
            "/api/bot/salidas",
            headers=claves["ro"],
            params={"origen": "Sucre", "destino": "La Paz", "fecha": "cuando sea"},
        )
    )
    assert not c["encontrado"] and "mañana" in c["mensaje"]
    c = _pequena(await client.get("/api/bot/salidas", headers=claves["ro"], params={"origen": "Sucre"}))
    assert not c["encontrado"] and "qué ciudad" in c["mensaje"]


async def test_rutas(client, claves):
    c = _pequena(await client.get("/api/bot/rutas", headers=claves["ro"]))
    assert len(c["rutas"]) == 6 and "Sucre" in c["mensaje"]


async def test_reserva_con_y_sin_el_caller_del_comprador(client, claves):
    c = _pequena(
        await client.get("/api/bot/reservas/mx7-k2p", headers=claves["ro"], params={"caller_id": TELEFONO_DEMO})
    )
    assert c["datos_completos"] and c["estado"] == "pagada" and c["boletos"] == 2 and "asientos" in c["mensaje"]
    c = _pequena(
        await client.get("/api/bot/reservas/MX7K2P", headers=claves["ro"], params={"caller_id": OTRO_TELEFONO})
    )
    assert not c["datos_completos"] and c["estado"] == "pagada"
    assert "total_bs" not in c and "ruta" not in c and "Santa Cruz" not in c["mensaje"]
    c = _pequena(await client.get("/api/bot/reservas/ZZZZZZ", headers=claves["ro"]))
    assert not c["encontrado"] and "6 caracteres" in c["mensaje"]


async def test_reserva_demorada_avisa_la_demora_aunque_no_coincida(client, claves):
    c = _pequena(
        await client.get("/api/bot/reservas/MX3T8W", headers=claves["ro"], params={"caller_id": OTRO_TELEFONO})
    )
    assert c["demora_min"] == 45 and "45 minutos de demora" in c["mensaje"]


# --- Carga, oficinas, ayuda, empresa ---------------------------------------------------------


async def test_cotizar_envio(client, claves):
    c = _pequena(
        await client.get(
            "/api/bot/tarifas-carga",
            headers=claves["ro"],
            params={"origen": "Sucre", "destino": "La Paz", "peso_kg": "3,5"},
        )
    )
    assert c["encontrado"] and c["tipo_envio"] == "paquete" and c["total_bs"] > 0 and "bolivianos" in c["mensaje"]
    c = _pequena(
        await client.get(
            "/api/bot/tarifas-carga",
            headers=claves["ro"],
            params={"origen": "Sucre", "destino": "Santa Cruz", "peso_kg": "40", "tipo": "sobre"},
        )
    )
    assert not c["encontrado"] and "30 kg" in c["mensaje"]
    c = _pequena(
        await client.get(
            "/api/bot/tarifas-carga",
            headers=claves["ro"],
            params={"origen": "Sucre", "destino": "Tarija", "peso_kg": "2", "puerta_a_puerta": "true"},
        )
    )
    assert not c["encontrado"] and "Santa Cruz" in c["mensaje"] and "Sucre" in c["mensaje"]


async def test_oficinas(client, claves):
    c = _pequena(await client.get("/api/bot/oficinas", headers=claves["ro"], params={"ciudad": "santa cruz"}))
    assert c["encontrado"] and len(c["oficinas"]) >= 2 and "atiende" in c["mensaje"]
    c = _pequena(await client.get("/api/bot/oficinas", headers=claves["ro"], params={"ciudad": "Cochabamba"}))
    assert not c["encontrado"] and "Atendemos" in c["mensaje"]


async def test_faq_devuelve_respuesta_corta(client, claves):
    c = _pequena(
        await client.get("/api/bot/faqs/buscar", headers=claves["ro"], params={"q": "puedo llevar a mi perro"})
    )
    assert c["encontrado"] and c["pregunta"]
    c = _pequena(await client.get("/api/bot/faqs/buscar", headers=claves["ro"], params={"q": "xyzzy plugh"}))
    assert not c["encontrado"]


async def test_empresa(client, claves):
    c = _pequena(await client.get("/api/bot/empresa", headers=claves["ro"]))
    assert c["encontrado"] and "El Mexicano" in c["mensaje"]


# --- Puerta a puerta -------------------------------------------------------------------------


def _solicitud(**extra) -> dict:
    return {
        "caller_id": TELEFONO_DEMO,
        "tipo": "recojo",
        "ciudad": "Sucre",
        "numero_documento": "9100001",
        "nombres": "Rosa",
        "apellidos": "Quispe",
        "direccion": "Calle Junín 450",
        "fecha": proximo_dia_habil(hoy(), saltar=1).isoformat(),
        "peso_kg": "3",
        **extra,
    }


async def test_puerta_a_puerta_crea_la_solicitud(client, claves):
    c = _pequena(await client.post("/api/bot/puerta-a-puerta", headers=claves["rw"], json=_solicitud()))
    assert c["encontrado"] and c["codigo"].startswith("PP-") and "14:00 a 17:00" in c["mensaje"]


async def test_puerta_a_puerta_rechaza_sabado_y_pide_lo_que_falta(client, claves):
    c = _pequena(
        await client.post(
            "/api/bot/puerta-a-puerta", headers=claves["rw"], json=_solicitud(fecha=proximo_sabado(hoy()).isoformat())
        )
    )
    assert not c["encontrado"] and "lunes a viernes" in c["mensaje"]
    c = _pequena(
        await client.post(
            "/api/bot/puerta-a-puerta", headers=claves["rw"], json={"caller_id": TELEFONO_DEMO, "ciudad": "Sucre"}
        )
    )
    assert not c["encontrado"] and "dirección" in c["mensaje"] and "carnet" in c["mensaje"]
    c = _pequena(await client.post("/api/bot/puerta-a-puerta", headers=claves["rw"], json=_solicitud(ciudad="Tarija")))
    assert not c["encontrado"] and "Santa Cruz" in c["mensaje"] and "Sucre" in c["mensaje"]


# --- Registro --------------------------------------------------------------------------------


async def test_cada_llamada_queda_registrada(client, claves):
    async with SessionLocal() as session:
        antes = await session.scalar(select(func.count()).select_from(BotConsultaLog))
    await client.get("/api/bot/encomiendas/26000101", headers=claves["ro"], params={"caller_id": "+" + TELEFONO_DEMO})
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(BotConsultaLog)) == antes + 1
        fila = await session.scalar(select(BotConsultaLog).order_by(BotConsultaLog.id.desc()).limit(1))
    assert fila.tool == "rastrear_encomienda" and fila.caller_id == TELEFONO_DEMO
    assert fila.parametros == {"numero_guia": "26000101"} and fila.encontrado and fila.coincide_caller
    assert fila.codigo_http == 200 and fila.latencia_ms >= 0 and fila.resultado["estado"] == "lista_para_retiro"


async def test_panel_lista_las_consultas_del_bot(client, claves, supervisor, boletero):
    await client.get("/api/bot/rutas", headers=claves["ro"])
    r = await client.get("/api/v1/admin/bot/consultas", headers=supervisor, params={"tool": "listar_rutas"})
    assert r.status_code == 200 and r.json()["total"] >= 1
    assert (await client.get("/api/v1/admin/bot/consultas", headers=boletero)).status_code == 403
