"""Herramientas del agente de voz (ElevenLabs): respuestas breves con un `mensaje` apto para decirse en voz alta.

Reutiliza los servicios de catálogos, salidas, carga, reservas, contenido y puerta a puerta; aquí solo
se decide qué datos mostrar (privacidad por `caller_id`) y cómo decirlos.

Privacidad: con el `caller_id` del destinatario, del remitente o del comprador se dan los datos
completos; con cualquier otro número, solo el estado general (sin nombres, montos, domicilios).
El PIN de retiro nunca se devuelve: el `caller_id` se puede falsificar y el PIN protege la entrega.
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NoEncontrado, ReglaNegocio
from app.models import Cliente, Encomienda
from app.models.enums import (
    CanalVenta,
    EstadoBoleto,
    EstadoEncomienda,
    EstadoSalida,
    EstadoVenta,
    ModalidadEntrega,
    TipoEnvio,
    TipoSolicitudPuerta,
)
from app.models.vistas import v_encomienda_rastreo
from app.schemas.carga import SolicitudPuertaIn
from app.schemas.ventas import PersonaIn
from app.services import carga, catalogos, contenido, puerta_a_puerta, reservas, salidas
from app.utils.fechas import DIAS_SEMANA, MESES, a_local, ahora, fecha_legible, hoy
from app.utils.telefonos import normalizar_e164
from app.utils.texto import normalizar

E = EstadoEncomienda
MAX_SALIDAS = 5
MAX_ENCOMIENDAS = 5
MAX_EVENTOS = 3

# --- Formato para voz ----------------------------------------------------------------------------


def caller(valor: str | None) -> str | None:
    """`{{system__caller_id}}` a E.164 solo dígitos; vacío, 'anonymous' o inválido → None."""
    return normalizar_e164(valor) if valor else None


def dinero(valor: Decimal | float | str) -> str:
    d = Decimal(str(valor)).quantize(Decimal("0.01"))
    entero = int(d)
    centavos = int((d - entero) * 100)
    texto = f"{entero} boliviano{'' if entero == 1 else 's'}"
    return f"{texto} con {centavos} centavos" if centavos else texto


def hora(dt: datetime) -> str:
    return f"{a_local(dt):%H:%M}"


def dia(valor: date | datetime) -> str:
    """'hoy', 'mañana' o 'el viernes 2 de octubre'."""
    d = a_local(valor).date() if isinstance(valor, datetime) else valor
    if d == hoy():
        return "hoy"
    if d == hoy() + timedelta(days=1):
        return "mañana"
    return f"el {fecha_legible(d)}"


def cuando(dt: datetime) -> str:
    return f"{dia(dt)} a las {hora(dt)}"


def lista(partes: list[str], conjuncion: str = "y") -> str:
    partes = [p for p in partes if p]
    if len(partes) <= 1:
        return "".join(partes)
    return f"{', '.join(partes[:-1])} {conjuncion} {partes[-1]}"


def telefono(e164: str | None) -> str | None:
    if not e164:
        return None
    return e164[3:] if e164.startswith("591") else f"+{e164}"


def duracion(minutos: int) -> str:
    h, m = divmod(minutos, 60)
    if m == 0:
        return f"{h} horas"
    if m == 30:
        return f"{h} horas y media"
    return f"{h} horas y {m} minutos"


_DIAS_ABREV = {
    "Lun": "lunes",
    "Mar": "martes",
    "Mié": "miércoles",
    "Jue": "jueves",
    "Vie": "viernes",
    "Sáb": "sábado",
    "Dom": "domingo",
}


def horario(texto: str | None) -> str | None:
    """'Lun–Vie 08:00–12:00; Lun–Vie 14:30–18:30; Sáb 08:00–12:00'
    → 'de lunes a viernes de 08:00 a 12:00 y de 14:30 a 18:30, y el sábado de 08:00 a 12:00'."""
    if not texto:
        return None
    grupos: dict[str, list[str]] = {}
    for tramo in texto.split("; "):
        dias_txt, _, horas = tramo.rpartition(" ")
        abre, _, cierra = horas.partition("–")
        grupos.setdefault(dias_txt, []).append(f"de {abre} a {cierra}")
    partes = []
    for dias_txt, horas in grupos.items():
        if "–" in dias_txt:
            d1, d2 = (_DIAS_ABREV.get(d, d) for d in dias_txt.split("–"))
            dias_voz = f"de {d1} a {d2}"
        else:
            dias_voz = "el " + lista([_DIAS_ABREV.get(d.strip(), d) for d in dias_txt.split(",")])
        partes.append(f"{dias_voz} {lista(horas)}")
    return lista(partes)


def web(url: str | None) -> str | None:
    return re.sub(r"^https?://(www\.)?", "", url).rstrip("/") if url else None


# --- Interpretación de parámetros dictados -------------------------------------------------------

_DIAS_NORM = [normalizar(d) for d in DIAS_SEMANA]
_MESES_NORM = [normalizar(m) for m in MESES]


def interpretar_fecha(texto: str | None) -> date:
    """Acepta hoy, mañana, pasado mañana, días de la semana, 2026-10-02, 2/10, 2/10/2026 y '2 de octubre'."""
    t = normalizar(texto or "hoy").replace("proximo ", "").replace("este ", "").strip()
    t = re.sub(r"^(el|para el|para) ", "", t)
    base = hoy()
    if t in ("", "hoy", "esta noche", "hoy en la noche"):
        return base
    if t in ("manana", "manana en la noche"):
        return base + timedelta(days=1)
    if t == "pasado manana":
        return base + timedelta(days=2)
    if t in _DIAS_NORM:
        return base + timedelta(days=(_DIAS_NORM.index(t) - base.weekday()) % 7)
    try:
        return date.fromisoformat(t)
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", t)
    if m:
        d, mes, anio = int(m[1]), int(m[2]), m[3]
    else:
        m = re.fullmatch(r"(?:\w+ )?(\d{1,2}) (?:de )?(\w+)(?: (?:de )?(\d{4}))?", t)
        if not m or m[2] not in _MESES_NORM:
            raise ReglaNegocio(
                f"No entendí la fecha «{texto}». Puedes decirme, por ejemplo: "
                "hoy, mañana, el viernes o el 5 de octubre.",
                codigo="fecha_invalida",
            )
        d, mes, anio = int(m[1]), _MESES_NORM.index(m[2]) + 1, m[3]
    try:
        if anio:
            return date(int(anio) + (2000 if len(anio) == 2 else 0), mes, d)
        fecha = date(base.year, mes, d)
        return fecha if fecha >= base else date(base.year + 1, mes, d)
    except ValueError as exc:
        raise ReglaNegocio(f"La fecha «{texto}» no existe. ¿Me la repites?", codigo="fecha_invalida") from exc


def interpretar_bool(texto: str | bool | None) -> bool:
    if isinstance(texto, bool):
        return texto
    return normalizar(texto or "") in {"true", "1", "si", "yes", "puerta a puerta", "domicilio"}


def interpretar_peso(texto: str | None) -> Decimal:
    m = re.search(r"\d+(?:[.,]\d+)?", texto or "")
    if not m:
        raise ReglaNegocio("¿Cuántos kilos pesa el envío, más o menos?", codigo="peso_requerido")
    return Decimal(m[0].replace(",", "."))


async def _ciudad(session: AsyncSession, texto: str | None, pregunta: str, *, carga_: bool | None = None):
    if not texto or not texto.strip():
        raise ReglaNegocio(pregunta, codigo="dato_requerido")
    try:
        return await catalogos.resolver_ciudad(session, texto)
    except NoEncontrado as exc:
        nombres = [c.nombre for c in await catalogos.listar_ciudades(session, carga=carga_ or None)]
        raise NoEncontrado(
            f"No reconozco la ciudad «{texto}». Atendemos {lista(nombres)}.", codigo="ciudad_no_encontrada"
        ) from exc


def _pedir(valor: Any, pregunta: str) -> None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        raise ReglaNegocio(pregunta, codigo="dato_requerido")


# --- Encomiendas -------------------------------------------------------------------------------

_ESTADO_VOZ = {
    E.registrada: "fue registrada y aún no llega a nuestra oficina",
    E.recibida_en_origen: "está en nuestra oficina de origen, lista para salir",
    E.en_transito: "está en camino",
    E.llegada_a_destino: "ya llegó a la ciudad de destino y la estamos preparando",
    E.lista_para_retiro: "está lista para recoger",
    E.en_reparto: "está en reparto hacia el domicilio",
    E.entregada: "ya fue entregada",
    E.intento_fallido: "tuvo un intento de entrega fallido",
    E.devuelta: "fue devuelta al remitente",
    E.cancelada: "fue cancelada",
}


async def rastrear_encomienda(session: AsyncSession, numero_guia: str, caller_id: str | None) -> dict[str, Any]:
    _pedir(numero_guia, "¿Cuál es el número de guía? Tiene 8 dígitos.")
    publico = await carga.rastreo_publico(session, numero_guia)
    guia = publico["numero_guia"]
    privado = (
        await session.execute(
            select(
                Encomienda.destinatario_telefono_e164,
                Encomienda.destinatario_nombre,
                Encomienda.precio_bs,
                Encomienda.direccion_entrega,
                Cliente.telefono_e164.label("remitente_telefono"),
                Cliente.nombres,
                Cliente.apellidos,
            )
            .join(Cliente, Cliente.id == Encomienda.remitente_cliente_id)
            .where(Encomienda.numero_guia == guia)
        )
    ).one()
    llamante = caller(caller_id)
    coincide = llamante is not None and llamante in {privado.destinatario_telefono_e164, privado.remitente_telefono}

    estado = E(publico["estado"])
    retiro = publico["modalidad_entrega"] == ModalidadEntrega.retiro_en_oficina
    pago_pendiente = publico["pago_pendiente_en_destino"]
    frases = [
        f"{'Tu' if coincide else 'La'} encomienda con guía {guia}, de {publico['ciudad_origen']} a "
        f"{publico['ciudad_destino']}, {_ESTADO_VOZ[estado]}."
    ]
    if estado == E.lista_para_retiro and retiro:
        h = horario(publico["horario_oficina"])
        frases.append(
            f"Se recoge en {publico['oficina_retiro']}, {publico['direccion_retiro']}"
            + (f"; atiende {h}." if h else ".")
            + " Hay que presentar el documento y el código de retiro que tiene el remitente."
        )
    elif (
        estado in (E.registrada, E.recibida_en_origen, E.en_transito)
        and publico["fecha_estimada_entrega"]
        and publico["fecha_estimada_entrega"] > ahora()
    ):
        frases.append(f"La llegada estimada es {cuando(publico['fecha_estimada_entrega'])}.")
    if estado == E.en_reparto and coincide and privado.direccion_entrega:
        frases.append(f"Va a {privado.direccion_entrega}.")
    if pago_pendiente:
        frases.append(
            f"Al recogerla se pagan {dinero(privado.precio_bs)}."
            if coincide
            else "Tiene un pago pendiente que se hace al recogerla."
        )
    if not coincide:
        frases.append("Para darte más detalles, llama desde el número registrado en el envío.")

    respuesta: dict[str, Any] = {
        "encontrado": True,
        "datos_completos": coincide,
        "numero_guia": guia,
        "estado": estado.value,
        "lista_para_retiro": publico["lista_para_retiro"],
        "pago_pendiente": pago_pendiente,
        "oficina_retiro": publico["oficina_retiro"],
    }
    if coincide:
        respuesta |= {
            "remitente": f"{privado.nombres} {privado.apellidos}",
            "destinatario": privado.destinatario_nombre,
            "monto_pendiente_bs": float(privado.precio_bs) if pago_pendiente else None,
            "ultimos_eventos": [
                {"estado": ev["estado"], "fecha": fecha_legible(ev["ocurrido_at"]), "ciudad": ev["ciudad"]}
                for ev in publico["eventos"][:MAX_EVENTOS]
            ],
        }
    respuesta["mensaje"] = " ".join(frases)
    respuesta["_coincide"] = coincide
    return respuesta


async def mis_encomiendas(session: AsyncSession, caller_id: str | None) -> dict[str, Any]:
    llamante = caller(caller_id)
    if not llamante:
        raise ReglaNegocio(
            "No pude identificar tu número. Dime el número de guía de 8 dígitos y la reviso.", codigo="sin_caller"
        )
    v = v_encomienda_rastreo.c
    filas = (
        await session.execute(
            select(v.numero_guia, v.estado, v.ciudad_origen, v.ciudad_destino, Encomienda.destinatario_telefono_e164)
            .join(Encomienda, Encomienda.id == v.encomienda_id)
            .join(Cliente, Cliente.id == Encomienda.remitente_cliente_id)
            .where(
                or_(Encomienda.destinatario_telefono_e164 == llamante, Cliente.telefono_e164 == llamante),
                Encomienda.estado.notin_(list(carga.ESTADOS_FINALES)),
            )
            .order_by(v.fecha_registro.desc())
            .limit(MAX_ENCOMIENDAS)
        )
    ).all()
    if not filas:
        raise NoEncontrado(
            "No encontré envíos activos asociados a tu número. Si tienes el número de guía, dímelo y lo reviso.",
            codigo="sin_encomiendas",
        )
    items = [
        {
            "numero_guia": f.numero_guia,
            "estado": f.estado,
            "destino": f.ciudad_destino,
            "rol": "destinatario" if f.destinatario_telefono_e164 == llamante else "remitente",
        }
        for f in filas
    ]
    detalle = [f"la guía {f.numero_guia} a {f.ciudad_destino} {_ESTADO_VOZ[E(f.estado)]}" for f in filas]
    n = len(filas)
    return {
        "encontrado": True,
        "encomiendas": items,
        "mensaje": f"Tienes {n} envío{'' if n == 1 else 's'} activo{'' if n == 1 else 's'}: {lista(detalle)}.",
        "_coincide": True,
    }


# --- Pasajes -----------------------------------------------------------------------------------


def _descripcion_salida(s: dict[str, Any]) -> str:
    inicio = f"a las {hora(s['fecha_hora_salida'])}"
    if s["estado"] == EstadoSalida.cancelada:
        return f"{inicio}, cancelada"
    if s["estado"] == EstadoSalida.demorada and s["minutos_demora"]:
        inicio += f", con {s['minutos_demora']} minutos de demora"
    if not s["vendible"]:
        return f"{inicio}, ya no está a la venta"
    clases = [
        f"{c['nombre']} a {dinero(c['precio_bs'])} "
        + (f"con {c['asientos_libres']} libres" if c["asientos_libres"] else "agotado")
        for c in s["clases"]
    ]
    return f"{inicio}, {lista(clases)}"


async def consultar_salidas(
    session: AsyncSession, origen: str | None, destino: str | None, fecha: str | None
) -> dict[str, Any]:
    ciudad_origen = await _ciudad(session, origen, "¿Desde qué ciudad quieres viajar?")
    ciudad_destino = await _ciudad(session, destino, "¿A qué ciudad quieres viajar?")
    dia_viaje = interpretar_fecha(fecha)
    if dia_viaje < hoy():
        raise ReglaNegocio("Esa fecha ya pasó. ¿Para qué día quieres viajar?", codigo="fecha_pasada")
    _, encontradas = await salidas.buscar(session, ciudad_origen.nombre, ciudad_destino.nombre, dia_viaje)
    viaje = f"de {ciudad_origen.nombre} a {ciudad_destino.nombre}"
    if not encontradas:
        raise NoEncontrado(
            f"No hay salidas {viaje} para {dia(dia_viaje)}. ¿Quieres que revise otro día?", codigo="sin_salidas"
        )
    mostradas = encontradas[:MAX_SALIDAS]
    n = len(mostradas)
    mensaje = (
        f"Para {dia(dia_viaje)} {viaje} hay {n} salida{'' if n == 1 else 's'}: "
        f"{'; '.join(_descripcion_salida(s) for s in mostradas)}."
    )
    if any(s["vendible"] for s in mostradas):
        mensaje += " Puedes comprar en elmexicanosrl.com o en nuestras boleterías."
    return {
        "encontrado": True,
        "fecha": dia_viaje.isoformat(),
        "salidas": [
            {
                "hora": hora(s["fecha_hora_salida"]),
                "estado": s["estado"],
                "demora_min": s["minutos_demora"] or 0,
                "vendible": s["vendible"],
                "clases": [
                    {"clase": c["nombre"], "precio_bs": float(c["precio_bs"]), "libres": c["asientos_libres"]}
                    for c in s["clases"]
                ],
            }
            for s in mostradas
        ],
        "mensaje": mensaje,
    }


async def listar_rutas(session: AsyncSession) -> dict[str, Any]:
    rutas = await catalogos.listar_rutas(session)
    horarios = await catalogos.horarios_por_ruta(session)
    desde_sucre = [r for r in rutas if r.origen.codigo == "SRE"]
    todas_las_horas = sorted({h for r in rutas for h in horarios.get(r.id, [])})
    destinos = [f"a {r.destino.nombre} en unas {duracion(r.duracion_estimada_min)}" for r in desde_sucre]
    mensaje = (
        f"Tenemos {len(rutas)} rutas, todas desde o hacia Sucre: {lista(destinos)}, en ambos sentidos."
        if desde_sucre
        else f"Tenemos {len(rutas)} rutas."
    )
    if todas_las_horas:
        mensaje += f" Las salidas son a las {lista(todas_las_horas)}."
    return {
        "encontrado": True,
        "rutas": [
            {
                "ruta": f"{r.origen.nombre} - {r.destino.nombre}",
                "km": r.distancia_km,
                "horas": round(r.duracion_estimada_min / 60, 1),
            }
            for r in rutas
        ],
        "mensaje": mensaje,
    }


async def consultar_reserva(session: AsyncSession, codigo: str, caller_id: str | None) -> dict[str, Any]:
    _pedir(codigo, "¿Cuál es el código de tu reserva? Tiene 6 letras y números.")
    venta = await reservas.obtener(session, codigo)
    llamante = caller(caller_id)
    coincide = llamante is not None and llamante == venta.comprador.telefono_e164
    salida = venta.boletos[0].salida if venta.boletos else None
    estado = EstadoVenta(venta.estado)
    estado_voz = {
        EstadoVenta.pendiente_pago: "está pendiente de pago",
        EstadoVenta.pagada: "está pagada",
        EstadoVenta.expirada: "expiró sin pago y los asientos se liberaron",
        EstadoVenta.cancelada: "fue cancelada",
    }.get(estado, "tiene boletos reembolsados")

    frases = [f"{'Tu' if coincide else 'La'} reserva {venta.codigo_reserva} {estado_voz}."]
    if coincide and salida:
        activos = [
            b
            for b in venta.boletos
            if b.estado in (EstadoBoleto.emitido, EstadoBoleto.reservado, EstadoBoleto.abordado)
        ]
        asientos = lista([str(b.numero_asiento) for b in activos])
        if activos:
            frases.append(
                ("Es 1 boleto, asiento " if len(activos) == 1 else f"Son {len(activos)} boletos, asientos ")
                + f"{asientos}, para el viaje de {salida.ruta.origen.nombre} a {salida.ruta.destino.nombre} "
                f"{cuando(salida.fecha_hora_salida)}."
            )
        if estado == EstadoVenta.pendiente_pago and venta.expira_at:
            frases.append(
                f"Falta pagar {dinero(venta.total_bs)} antes de las {hora(venta.expira_at)}; "
                "puedes hacerlo en elmexicanosrl.com, en Mi reserva."
            )
        if estado == EstadoVenta.pagada and salida.oficina_salida:
            frases.append(
                f"El bus sale de {salida.oficina_salida.nombre}" + (f", andén {salida.anden}." if salida.anden else ".")
            )
    if salida and estado in (EstadoVenta.pagada, EstadoVenta.pendiente_pago):
        if salida.estado == EstadoSalida.demorada and salida.minutos_demora:
            nueva = salida.fecha_hora_salida + timedelta(minutes=salida.minutos_demora)
            frases.append(
                f"La salida tiene {salida.minutos_demora} minutos de demora"
                + (f"; la nueva hora es {hora(nueva)}." if coincide else ".")
            )
        elif salida.estado == EstadoSalida.cancelada:
            frases.append("La salida fue cancelada; el pago se reembolsa al 100 %.")
    if not coincide:
        frases.append(
            "Para darte los detalles del viaje, llama desde el número con el que se hizo la compra "
            "o revisa Mi reserva en elmexicanosrl.com con tu documento."
        )

    respuesta: dict[str, Any] = {
        "encontrado": True,
        "datos_completos": coincide,
        "codigo_reserva": venta.codigo_reserva,
        "estado": estado.value,
        "demora_min": salida.minutos_demora if salida and salida.estado == EstadoSalida.demorada else 0,
    }
    if coincide and salida:
        respuesta |= {
            "salida": salida.fecha_hora_salida.isoformat(),
            "ruta": f"{salida.ruta.origen.nombre} - {salida.ruta.destino.nombre}",
            "boletos": len(venta.boletos),
            "total_bs": float(venta.total_bs),
        }
    respuesta["mensaje"] = " ".join(frases)
    respuesta["_coincide"] = coincide
    return respuesta


# --- Carga -------------------------------------------------------------------------------------


async def cotizar_envio(
    session: AsyncSession,
    origen: str | None,
    destino: str | None,
    peso_kg: str | None,
    tipo: str | None,
    puerta_a_puerta: str | bool | None,
) -> dict[str, Any]:
    ciudad_origen = await _ciudad(session, origen, "¿Desde qué ciudad envías?", carga_=True)
    ciudad_destino = await _ciudad(session, destino, "¿A qué ciudad va el envío?", carga_=True)
    peso = interpretar_peso(peso_kg)
    tipo_envio = None
    if tipo and normalizar(tipo) not in ("", "auto"):
        try:
            tipo_envio = TipoEnvio(normalizar(tipo))
        except ValueError as exc:
            raise ReglaNegocio("El tipo de envío puede ser sobre, paquete o carga.", codigo="tipo_invalido") from exc
    domicilio = interpretar_bool(puerta_a_puerta)
    c = await carga.cotizar(session, ciudad_origen.nombre, ciudad_destino.nombre, float(peso), tipo_envio, domicilio)
    extra = f", que incluye {dinero(c['recargo_puerta_a_puerta_bs'])} por la entrega a domicilio" if domicilio else ""
    kilos = f"{c['peso_kg']:g}".replace(".", ",")  # "3,5": la coma se lee bien en voz
    return {
        "encontrado": True,
        "tipo_envio": c["tipo_envio"],
        "peso_kg": c["peso_kg"],
        "total_bs": float(c["total_bs"]),
        "mensaje": (
            f"Enviar un {c['tipo_envio']} de {kilos} kilos de {c['origen']} a {c['destino']} cuesta "
            f"{dinero(c['total_bs'])}{extra}. Se paga al enviar o, si prefieres, lo paga quien lo recibe."
        ),
    }


_ETIQUETAS = {
    "numero_documento": "el número de carnet",
    "nombres": "el nombre",
    "apellidos": "el apellido",
    "telefono": "el número de celular",
    "direccion": "la dirección (al menos 5 letras)",
    "peso_estimado_kg": "el peso (desde 1 kilo)",
    "referencia": "la referencia",
    "descripcion": "la descripción",
}


async def solicitar_puerta_a_puerta(session: AsyncSession, datos: "BotPuertaIn") -> dict[str, Any]:
    faltan = [
        etiqueta
        for campo, etiqueta in (
            ("tipo", "si es recojo o entrega"),
            ("ciudad", "la ciudad"),
            ("numero_documento", "tu número de carnet"),
            ("nombres", "tu nombre"),
            ("apellidos", "tu apellido"),
            ("direccion", "la dirección"),
            ("fecha", "el día"),
        )
        if not (getattr(datos, campo) or "").strip()
    ]
    if faltan:
        raise ReglaNegocio(f"Para agendarlo necesito {lista(faltan)}.", codigo="datos_incompletos")
    tipo = normalizar(datos.tipo or "")
    if tipo not in ("recojo", "entrega"):
        raise ReglaNegocio(
            "¿Es un recojo (pasamos a buscar tu envío) o una entrega a domicilio?", codigo="tipo_invalido"
        )
    telefono_contacto = normalizar_e164(datos.telefono) if datos.telefono else caller(datos.caller_id)
    if not telefono_contacto:
        raise ReglaNegocio("¿A qué número de celular te contactamos?", codigo="telefono_requerido")
    try:
        solicitud_in = SolicitudPuertaIn(
            tipo=TipoSolicitudPuerta(tipo),
            ciudad=datos.ciudad,
            cliente=PersonaIn(
                numero_documento=datos.numero_documento, nombres=datos.nombres, apellidos=datos.apellidos
            ),
            telefono=telefono_contacto,
            direccion=datos.direccion,
            referencia=datos.referencia or None,
            fecha_programada=interpretar_fecha(datos.fecha),
            peso_estimado_kg=float(interpretar_peso(datos.peso_kg)) if datos.peso_kg else None,
            descripcion=datos.descripcion or None,
            numero_guia="".join(ch for ch in datos.numero_guia if ch.isdigit()) if datos.numero_guia else None,
        )
    except ValidationError as exc:
        campo = str(exc.errors()[0]["loc"][-1])
        raise ReglaNegocio(
            f"Revisa {_ETIQUETAS.get(campo, campo)}: no parece válido. ¿Me lo repites?", codigo="dato_invalido"
        ) from exc

    solicitud = await puerta_a_puerta.crear(session, solicitud_in, canal=CanalVenta.whatsapp_chat)
    r = await puerta_a_puerta.a_respuesta(session, solicitud)
    accion = "pasaremos a recoger tu envío" if tipo == "recojo" else "llevaremos tu envío"
    costo = f" El costo es {dinero(r['costo_bs'])}." if r["costo_bs"] else ""
    return {
        "encontrado": True,
        "codigo": r["codigo"],
        "fecha": r["fecha_programada"].isoformat(),
        "franja": r["franja_texto"],
        "mensaje": (
            f"Listo, registré tu solicitud {r['codigo']}: {accion} en {r['ciudad']} {dia(r['fecha_programada'])} "
            f"{r['franja_texto']}, en {r['direccion']}.{costo} Te escribiremos por WhatsApp para confirmarlo."
        ),
        "_coincide": True,
    }


# --- Información general -----------------------------------------------------------------------


async def info_oficinas(session: AsyncSession, ciudad: str | None, tipo: str | None) -> dict[str, Any]:
    c = await _ciudad(session, ciudad, "¿De qué ciudad necesitas la oficina?")
    oficinas = await catalogos.listar_oficinas(session, c.nombre)
    t = normalizar(tipo or "")
    if t in ("pasajes", "boleteria", "pasaje"):
        oficinas = [o for o in oficinas if o["tipo"] in ("boleteria", "mixta")]
    elif t in ("carga", "encomiendas", "encomienda", "bodega"):
        oficinas = [o for o in oficinas if o["tipo"] in ("bodega_carga", "mixta")]
    if not oficinas:
        raise NoEncontrado(f"No tenemos oficinas de ese tipo en {c.nombre}.", codigo="sin_oficinas")
    detalle = []
    for o in oficinas[:2]:
        h = horario(o["horario_texto"])
        tel = telefono(o["telefono_e164"])
        detalle.append(
            f"{o['nombre']}, en {o['direccion']}"
            + (f", teléfono {tel}" if tel else "")
            + (f"; atiende {h}" if h else "")
        )
    otras = [o["nombre"] for o in oficinas[2:]]
    n = len(oficinas)
    mensaje = f"En {c.nombre} tenemos {n} oficina{'' if n == 1 else 's'}. " + ". ".join(detalle) + "."
    if otras:
        mensaje += f" También está {lista(otras)}; pregúntame si necesitas su dirección."
    return {
        "encontrado": True,
        "ciudad": c.nombre,
        "oficinas": [{"nombre": o["nombre"], "tipo": o["tipo"]} for o in oficinas],
        "mensaje": mensaje,
    }


def _recortar(texto: str, maximo: int = 420) -> str:
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo]
    fin = corte.rfind(". ")
    return corte[: fin + 1] if fin > 150 else corte.rsplit(" ", 1)[0] + "…"


async def buscar_faq(session: AsyncSession, q: str | None) -> dict[str, Any]:
    if not q or len(q.strip()) < 3:
        raise ReglaNegocio("¿Sobre qué tema tienes la duda?", codigo="consulta_vacia")
    resultados = await contenido.buscar_faqs(session, q, limite=1)
    if not resultados:
        empresa = await catalogos.empresa(session)
        wa = telefono(empresa.whatsapp_central_e164)
        raise NoEncontrado(
            "No encontré una respuesta a eso." + (f" Puedes escribirnos por WhatsApp al {wa}." if wa else ""),
            codigo="faq_no_encontrada",
        )
    faq = resultados[0]
    texto = re.sub(r"[*_#>`]", "", faq.respuesta_corta_voz or faq.respuesta)
    return {"encontrado": True, "pregunta": faq.pregunta, "mensaje": _recortar(" ".join(texto.split()))}


async def info_empresa(session: AsyncSession) -> dict[str, Any]:
    e = await catalogos.empresa(session)
    datos = {
        "whatsapp": telefono(e.whatsapp_central_e164),
        "telefono": telefono(e.telefono_atencion_cliente_e164 or e.telefono_central_e164),
        "sitio_web": web(e.sitio_web),
        "compra_pasajes": web(e.url_compra_pasajes),
        "email": e.email_contacto,
    }
    partes = [f"Somos {e.nombre_comercial}, {e.razon_social.rstrip('.')}."]
    if datos["sitio_web"]:
        partes.append(f"Los pasajes se compran en {datos['sitio_web']} o en nuestras boleterías.")
    contactos = []
    if datos["whatsapp"]:
        contactos.append(f"WhatsApp {datos['whatsapp']}")
    if datos["telefono"] and datos["telefono"] != datos["whatsapp"]:
        contactos.append(f"teléfono {datos['telefono']}")
    if datos["email"]:
        contactos.append(f"correo {datos['email']}")
    if contactos:
        partes.append(f"Puedes contactarnos por {lista(contactos, 'o')}.")
    return {"encontrado": True, **{k: v for k, v in datos.items() if v}, "mensaje": " ".join(partes)}


class BotPuertaIn(BaseModel):
    """Datos que el agente recoge en la conversación; todos opcionales para poder pedir lo que falte."""

    caller_id: str | None = None
    tipo: str | None = None
    ciudad: str | None = None
    numero_documento: str | None = None
    nombres: str | None = None
    apellidos: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    referencia: str | None = None
    fecha: str | None = None
    peso_kg: str | None = None
    descripcion: str | None = None
    numero_guia: str | None = None
