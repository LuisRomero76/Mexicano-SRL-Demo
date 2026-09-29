"""API para el agente de voz de ElevenLabs (webhook tools). Autenticación con la cabecera `X-Bot-Key`.

Cada respuesta es pequeña (menos de 1 KB) y trae `mensaje` en español apto para voz. Los errores de negocio
(guía inexistente, ciudad desconocida, día no hábil…) responden 200 con `{"encontrado": false, "mensaje": …}`
para que el agente pueda decirlos tal cual. Cada llamada queda en `bot_consultas_log`, escrito después de
enviar la respuesta para no sumar latencia.
"""

import logging
import time
from collections.abc import Awaitable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from app.core.db import SessionLocal
from app.core.deps import SessionDep, requiere_bot
from app.core.errors import DomainError
from app.models import ApiKey, BotConsultaLog
from app.services import bot
from app.services.api_keys import SCOPE_ESCRITURA, SCOPE_LECTURA, KeyValida
from app.utils.fechas import ahora

log = logging.getLogger("elmexicano.bot")
router = APIRouter(prefix="/api/bot", tags=["Agente de voz (ElevenLabs)"])

Lectura = Annotated[KeyValida, Depends(requiere_bot(SCOPE_LECTURA))]
Escritura = Annotated[KeyValida, Depends(requiere_bot(SCOPE_ESCRITURA))]
CallerId = Annotated[
    str | None,
    Query(description="Teléfono de quien llama; en ElevenLabs, la variable dinámica {{system__caller_id}}"),
]


async def _registrar(
    api_key_id: int,
    tool: str,
    caller_id: str | None,
    parametros: dict[str, Any],
    cuerpo: dict[str, Any],
    codigo: int,
    ms: int,
    coincide: bool | None,
) -> None:
    try:
        async with SessionLocal() as session:
            session.add(
                BotConsultaLog(
                    api_key_id=api_key_id,
                    tool=tool,
                    caller_id=caller_id,
                    parametros=parametros,
                    encontrado=bool(cuerpo.get("encontrado")),
                    coincide_caller=coincide,
                    resultado=cuerpo,
                    codigo_http=codigo,
                    latencia_ms=ms,
                )
            )
            # Último uso, como máximo una escritura por minuto por key.
            key = await session.get(ApiKey, api_key_id)
            momento = ahora()
            if key and (key.ultimo_uso_at is None or (momento - key.ultimo_uso_at).total_seconds() > 60):
                key.ultimo_uso_at = momento
            await session.commit()
    except Exception:  # noqa: BLE001 - el registro nunca debe romper la respuesta
        log.exception("No se pudo registrar la consulta del bot (%s)", tool)


async def _responder(
    key: KeyValida, tool: str, parametros: dict[str, Any], operacion: Awaitable[dict[str, Any]]
) -> JSONResponse:
    inicio = time.perf_counter()
    codigo = 200
    try:
        cuerpo = await operacion
    except DomainError as exc:
        cuerpo = {"encontrado": False, "mensaje": exc.mensaje}
    except Exception:  # noqa: BLE001 - el agente necesita un mensaje que pueda decir
        log.exception("Error en la tool %s", tool)
        codigo = 500
        cuerpo = {"encontrado": False, "mensaje": "Tuve un problema al consultar. Intenta de nuevo en un momento."}
    coincide = cuerpo.pop("_coincide", None)
    ms = round((time.perf_counter() - inicio) * 1000)
    caller = bot.caller(parametros.get("caller_id"))
    limpios = {k: v for k, v in parametros.items() if v not in (None, "") and k != "caller_id"}
    return JSONResponse(
        status_code=codigo,
        content=cuerpo,
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(_registrar, key.id, tool, caller, limpios, cuerpo, codigo, ms, coincide),
    )


@router.get("/encomiendas/{numero_guia}", summary="rastrear_encomienda: estado de una guía")
async def rastrear_encomienda(session: SessionDep, key: Lectura, numero_guia: str, caller_id: CallerId = None):
    """Estado, oficina de retiro con dirección y horario, pago pendiente y últimos 3 eventos.
    Datos completos solo si `caller_id` es el teléfono del destinatario o del remitente. Nunca devuelve el PIN."""
    return await _responder(
        key,
        "rastrear_encomienda",
        {"numero_guia": numero_guia, "caller_id": caller_id},
        bot.rastrear_encomienda(session, numero_guia, caller_id),
    )


@router.get("/encomiendas", summary="mis_encomiendas: envíos activos de quien llama")
async def mis_encomiendas(session: SessionDep, key: Lectura, caller_id: CallerId = None):
    """Hasta 5 encomiendas no finalizadas donde `caller_id` es remitente o destinatario."""
    return await _responder(key, "mis_encomiendas", {"caller_id": caller_id}, bot.mis_encomiendas(session, caller_id))


@router.get("/salidas", summary="consultar_salidas: horarios, precios y asientos libres de un día")
async def consultar_salidas(
    session: SessionDep,
    key: Lectura,
    origen: Annotated[
        str | None, Query(description="Ciudad de origen (acepta alias: 'Santa Cruz de la Sierra', 'SCZ')")
    ] = None,
    destino: Annotated[str | None, Query(description="Ciudad de destino")] = None,
    fecha: Annotated[
        str | None, Query(description="hoy, mañana, pasado mañana, un día de la semana, 2026-10-02 o 2/10")
    ] = None,
):
    return await _responder(
        key,
        "consultar_salidas",
        {"origen": origen, "destino": destino, "fecha": fecha},
        bot.consultar_salidas(session, origen, destino, fecha),
    )


@router.get("/rutas", summary="listar_rutas: rutas con distancia, duración y horarios")
async def listar_rutas(session: SessionDep, key: Lectura):
    return await _responder(key, "listar_rutas", {}, bot.listar_rutas(session))


@router.get("/tarifas-carga", summary="cotizar_envio: precio de un envío de carga o encomienda")
async def cotizar_envio(
    session: SessionDep,
    key: Lectura,
    origen: str | None = None,
    destino: str | None = None,
    peso_kg: Annotated[str | None, Query(description="Peso en kilos, por ejemplo 3 o 2,5")] = None,
    tipo: Annotated[str | None, Query(description="sobre, paquete o carga; si se omite se deduce del peso")] = None,
    puerta_a_puerta: Annotated[str | None, Query(description="true si se entrega a domicilio")] = None,
):
    return await _responder(
        key,
        "cotizar_envio",
        {"origen": origen, "destino": destino, "peso_kg": peso_kg, "tipo": tipo, "puerta_a_puerta": puerta_a_puerta},
        bot.cotizar_envio(session, origen, destino, peso_kg, tipo, puerta_a_puerta),
    )


@router.get("/reservas/{codigo}", summary="consultar_reserva: estado de una reserva de pasajes")
async def consultar_reserva(session: SessionDep, key: Lectura, codigo: str, caller_id: CallerId = None):
    """Estado, boletos, salida y demora. Detalle del viaje y montos solo si `caller_id` es el del comprador."""
    return await _responder(
        key,
        "consultar_reserva",
        {"codigo": codigo, "caller_id": caller_id},
        bot.consultar_reserva(session, codigo, caller_id),
    )


@router.get("/oficinas", summary="info_oficinas: dirección, teléfono y horario de las oficinas de una ciudad")
async def info_oficinas(
    session: SessionDep,
    key: Lectura,
    ciudad: str | None = None,
    tipo: Annotated[str | None, Query(description="pasajes o carga (opcional)")] = None,
):
    return await _responder(
        key, "info_oficinas", {"ciudad": ciudad, "tipo": tipo}, bot.info_oficinas(session, ciudad, tipo)
    )


@router.get("/faqs/buscar", summary="buscar_faq: respuesta corta a una pregunta frecuente")
async def buscar_faq(session: SessionDep, key: Lectura, q: str | None = None):
    return await _responder(key, "buscar_faq", {"q": q}, bot.buscar_faq(session, q))


@router.get("/empresa", summary="info_empresa: contactos y dónde comprar pasajes")
async def info_empresa(session: SessionDep, key: Lectura):
    return await _responder(key, "info_empresa", {}, bot.info_empresa(session))


@router.post("/puerta-a-puerta", summary="solicitar_puerta_a_puerta: agenda un recojo o una entrega a domicilio")
async def solicitar_puerta_a_puerta(session: SessionDep, key: Escritura, datos: bot.BotPuertaIn):
    """Solo Sucre y Santa Cruz, de lunes a viernes hábiles (recojos 14:00–17:00, entregas 08:00–12:00).
    Si falta algún dato responde qué pedirle al cliente. El teléfono de contacto por defecto es `caller_id`."""
    return await _responder(
        key,
        "solicitar_puerta_a_puerta",
        datos.model_dump(),
        bot.solicitar_puerta_a_puerta(session, datos),
    )
