"""Catálogos: upsert idempotente por código o clave única."""

from datetime import time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import (
    Asiento,
    Bus,
    Ciudad,
    Comodidad,
    CuentaCorporativa,
    Empresa,
    Faq,
    FaqCategoria,
    Feriado,
    HorarioOficina,
    Oficina,
    PaginaContenido,
    ParametroNegocio,
    PlantillaHorario,
    PoliticaTipoPasajero,
    Ruta,
    RutaParada,
    TarifaCarga,
    TarifaPasaje,
    TipoAsiento,
    Usuario,
    VehiculoCarga,
    tipo_asiento_comodidades,
)
from app.services import flota
from seeds.data import demo, reales


async def upsert(
    session: AsyncSession,
    modelo: Any,
    filas: list[dict[str, Any]],
    claves: list[str] | None = None,
    *,
    constraint: str | None = None,
) -> None:
    if not filas:
        return
    stmt = insert(modelo).values(filas)
    conflicto = {"constraint": constraint} if constraint else {"index_elements": claves}
    actualizar = {c: stmt.excluded[c] for c in filas[0] if c not in (claves or [])}
    stmt = (
        stmt.on_conflict_do_update(**conflicto, set_=actualizar)
        if actualizar
        else stmt.on_conflict_do_nothing(**conflicto)
    )
    await session.execute(stmt)


async def ids_por(session: AsyncSession, columna_clave, columna_id=None) -> dict[Any, Any]:
    columna_id = columna_id if columna_id is not None else columna_clave.class_.id
    return dict((await session.execute(select(columna_clave, columna_id))).all())


def _hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


async def seed_catalogos(session: AsyncSession) -> None:
    await upsert(session, Empresa, [reales.EMPRESA], ["id"])
    await upsert(session, Ciudad, reales.CIUDADES, ["codigo"])
    ciudades = await ids_por(session, Ciudad.codigo)

    await upsert(
        session,
        Oficina,
        [
            {
                "ciudad_id": ciudades[c],
                "codigo": cod,
                "nombre": nom,
                "tipo": tipo,
                "direccion": dir_,
                "referencia": ref,
                "telefono_e164": tel,
                "whatsapp_e164": wa,
                "url_mapa": mapa,
                "es_principal": principal,
                "latitud": lat,
                "longitud": lon,
                "es_dato_demo": False,
            }
            for c, cod, nom, tipo, dir_, ref, tel, wa, mapa, principal, lat, lon in reales.OFICINAS
        ],
        ["codigo"],
    )
    oficinas = await ids_por(session, Oficina.codigo)
    tipos_oficina = dict((await session.execute(select(Oficina.codigo, Oficina.tipo))).all())
    horarios = []
    for codigo, oficina_id in oficinas.items():
        es_boleteria = tipos_oficina[codigo] == "boleteria"
        apertura, cierre, dias = reales.HORARIO_BOLETERIA if es_boleteria else reales.HORARIO_BODEGA
        for dia in dias:
            horarios.append(
                {
                    "oficina_id": oficina_id,
                    "servicio": "boleteria" if es_boleteria else "carga",
                    "dia_semana": dia,
                    "hora_apertura": _hora(apertura),
                    "hora_cierre": _hora(cierre),
                    "observacion": "Horario real; días de atención demo",
                }
            )
    await upsert(session, HorarioOficina, horarios, ["oficina_id", "servicio", "dia_semana", "hora_apertura"])

    await upsert(
        session,
        Feriado,
        [{"fecha": f, "nombre": n, "departamento": d} for f, n, d in demo.FERIADOS],
        constraint="uq_feriados_fecha_departamento",
    )
    await upsert(
        session,
        ParametroNegocio,
        [
            {"clave": k, "valor": v, "descripcion": desc, "es_dato_demo": es_demo}
            for k, (v, desc, es_demo) in demo.PARAMETROS.items()
        ],
        ["clave"],
    )

    # Flota
    await upsert(session, TipoAsiento, reales.TIPOS_ASIENTO, ["codigo"])
    await upsert(
        session,
        Comodidad,
        [{"codigo": c, "nombre": n, "icono": i} for c, n, i in reales.COMODIDADES],
        ["codigo"],
    )
    tipos = await ids_por(session, TipoAsiento.codigo)
    comodidades = await ids_por(session, Comodidad.codigo)
    await session.execute(
        insert(tipo_asiento_comodidades)
        .values(
            [
                {"tipo_asiento_id": tipos[t], "comodidad_id": comodidades[c]}
                for t, cs in reales.COMODIDADES_POR_TIPO.items()
                for c in cs
            ]
        )
        .on_conflict_do_nothing()
    )

    await upsert(
        session,
        Bus,
        [
            {
                "numero_interno": n,
                "placa": p,
                "marca": ma,
                "modelo": mo,
                "anio": a,
                "estado": e,
                "pisos": 2,
                "capacidad_total": 48,
                "gps_dispositivo_id": f"GPS-{n}",
                "es_dato_demo": True,
            }
            for n, p, ma, mo, a, e in demo.BUSES
        ],
        ["numero_interno"],
    )
    buses = await ids_por(session, Bus.numero_interno)
    asientos = []
    for bus_id in buses.values():
        asientos += await flota.asientos_estandar(session, bus_id)
    await upsert(session, Asiento, asientos, ["bus_id", "numero"])

    await upsert(
        session,
        VehiculoCarga,
        [
            {
                "placa": p,
                "tipo": t,
                "capacidad_kg": cap,
                "ciudad_base_id": ciudades[c],
                "gps_dispositivo_id": f"GPS-{p}",
                "ultima_latitud": lat,
                "ultima_longitud": lon,
                "es_dato_demo": True,
            }
            for p, t, cap, c, lat, lon in demo.VEHICULOS
        ],
        ["placa"],
    )

    # Rutas, paradas, plantillas y tarifas
    await upsert(
        session,
        Ruta,
        [
            {
                "codigo": cod,
                "origen_ciudad_id": ciudades[o],
                "destino_ciudad_id": ciudades[d],
                "distancia_km": km,
                "duracion_estimada_min": mins,
                "cargo_exceso_equipaje_kg_bs": demo.CARGO_EXCESO_EQUIPAJE[_corredor(cod)],
                "descripcion": f"Servicio Suite Cama - Leito Cama, {km} km, {mins // 60} h",
            }
            for cod, o, d, km, mins in reales.RUTAS
        ],
        ["codigo"],
    )
    rutas = await ids_por(session, Ruta.codigo)
    await upsert(
        session,
        RutaParada,
        [
            {
                "ruta_id": rutas[r],
                "ciudad_id": ciudades[c],
                "orden": o,
                "km_desde_origen": km,
                "minutos_desde_origen": m,
                "permite_carga": True,
                "permite_pasajeros": False,
                "es_dato_demo": True,
            }
            for r, c, o, km, m in demo.PARADAS
        ],
        ["ruta_id", "orden"],
    )
    boleteria_origen = {cod: oficinas[f"{o}-BOL"] for cod, o, *_ in reales.RUTAS}
    await upsert(
        session,
        PlantillaHorario,
        [
            {
                "ruta_id": rutas[cod],
                "hora_salida": _hora(h),
                "dias_semana": [1, 2, 3, 4, 5, 6, 7],
                "oficina_salida_id": boleteria_origen[cod],
                "vigente_desde": demo.TARIFAS_VIGENTES_DESDE,
                "vigente_hasta": None,
                "es_dato_demo": True,
            }
            for cod, *_ in reales.RUTAS
            for h in demo.HORAS_SALIDA
        ],
        ["ruta_id", "hora_salida", "vigente_desde"],
    )
    await upsert(
        session,
        TarifaPasaje,
        [
            {
                "ruta_id": rutas[cod],
                "tipo_asiento_id": tipos[clase],
                "precio_bs": Decimal(precio),
                "precio_maximo_referencial_bs": Decimal(maximo),
                "vigente_desde": demo.TARIFAS_VIGENTES_DESDE,
                "es_dato_demo": True,
            }
            for cod, *_ in reales.RUTAS
            for clase, (precio, maximo) in demo.TARIFAS_PASAJE[_corredor(cod)].items()
        ],
        ["ruta_id", "tipo_asiento_id", "vigente_desde"],
    )
    await upsert(
        session,
        PoliticaTipoPasajero,
        [
            {
                "tipo_pasajero": t,
                "nombre": n,
                "descuento_porcentaje": Decimal(p),
                "solo_boleteria": sb,
                "edad_min": emin,
                "edad_max": emax,
                "requisito": req,
                "es_dato_demo": es_demo,
            }
            for t, n, p, sb, emin, emax, req, es_demo in reales.POLITICAS
        ],
        ["tipo_pasajero"],
    )
    tarifas_carga = []
    for origen, oid in ciudades.items():
        for destino, did in ciudades.items():
            if origen == destino:
                continue
            for tipo, (pmin, pmax, base, adicional) in demo.TARIFAS_CARGA.items():
                tarifas_carga.append(
                    {
                        "origen_ciudad_id": oid,
                        "destino_ciudad_id": did,
                        "tipo_envio": tipo,
                        "peso_min_kg": Decimal(pmin),
                        "peso_max_kg": Decimal(pmax) if pmax is not None else None,
                        "precio_base_bs": Decimal(base),
                        "precio_kg_adicional_bs": Decimal(str(adicional)),
                        "recargo_puerta_a_puerta_bs": Decimal(demo.RECARGO_PUERTA_A_PUERTA),
                        "vigente_desde": demo.TARIFAS_VIGENTES_DESDE,
                        "es_dato_demo": True,
                    }
                )
    await upsert(
        session,
        TarifaCarga,
        tarifas_carga,
        ["origen_ciudad_id", "destino_ciudad_id", "tipo_envio", "peso_min_kg", "vigente_desde"],
    )

    # Contenido
    await upsert(
        session,
        FaqCategoria,
        [{"codigo": c, "nombre": n, "orden": o} for c, n, o in reales.FAQ_CATEGORIAS],
        ["codigo"],
    )
    categorias = await ids_por(session, FaqCategoria.codigo)
    await upsert(
        session,
        Faq,
        [
            {
                "categoria_id": categorias[cat],
                "slug": slug,
                "pregunta": preg,
                "respuesta": resp,
                "respuesta_corta_voz": corta,
                "palabras_clave": claves,
                "orden": i,
                "es_dato_demo": False,
                "activo": True,
            }
            for i, (cat, slug, preg, resp, corta, claves) in enumerate(reales.FAQS, start=1)
        ],
        ["slug"],
    )
    await upsert(
        session,
        PaginaContenido,
        [
            {"slug": s, "titulo": t, "meta_descripcion": m, "contenido_md": c, "url_original": u}
            for s, t, m, c, u in reales.PAGINAS
        ],
        ["slug"],
    )

    # Personal (una sola contraseña demo, hash calculado una vez)
    password_hash = hash_password(demo.PASSWORD_DEMO)
    personal = [
        {
            "email": email,
            "password_hash": password_hash,
            "nombres": n,
            "apellidos": a,
            "rol": rol,
            "oficina_id": oficinas[of],
            "telefono_e164": tel,
            "licencia_conducir": None,
        }
        for email, n, a, rol, of, tel in demo.PERSONAL
    ]
    for i in range(24):
        n = demo.NOMBRES[(i * 7) % len(demo.NOMBRES)]
        a = f"{demo.APELLIDOS[(i * 5) % len(demo.APELLIDOS)]} {demo.APELLIDOS[(i * 11 + 3) % len(demo.APELLIDOS)]}"
        personal.append(
            {
                "email": f"conductor{i + 1:02d}@elmexicanosrl.com",
                "password_hash": password_hash,
                "nombres": n,
                "apellidos": a,
                "rol": "conductor",
                "oficina_id": oficinas["SRE-BOL"],
                "telefono_e164": f"5917020{i + 1:04d}",
                "licencia_conducir": f"C-{4100200 + i * 37}",
            }
        )
    await upsert(session, Usuario, personal, ["email"])

    await upsert(
        session,
        CuentaCorporativa,
        [
            {
                "codigo": c,
                "razon_social": rs,
                "nit": nit,
                "contacto_nombre": cn,
                "contacto_telefono_e164": ct,
                "contacto_email": ce,
                "limite_credito_bs": Decimal(lim),
                "dias_credito": dias,
                "es_dato_demo": True,
            }
            for c, rs, nit, cn, ct, ce, lim, dias in demo.CUENTAS_CORPORATIVAS
        ],
        ["codigo"],
    )
    await session.commit()


def _corredor(codigo_ruta: str) -> str:
    return next(c for c in codigo_ruta.split("-") if c != "SRE")
