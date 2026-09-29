from datetime import timedelta

import httpx

from app.utils.fechas import hoy


async def salida_futura(
    client: httpx.AsyncClient, origen: str = "Sucre", destino: str = "Santa Cruz", dias: int = 10, indice: int = 0
) -> tuple[str, dict[str, list[int]]]:
    """Devuelve el id de una salida vendible y sus asientos libres por clase."""
    fecha = hoy() + timedelta(days=dias)
    r = await client.get("/api/v1/salidas", params={"origen": origen, "destino": destino, "fecha": fecha.isoformat()})
    assert r.status_code == 200, r.text
    salida = [s for s in r.json()["salidas"] if s["vendible"]][indice]
    detalle = (await client.get(f"/api/v1/salidas/{salida['id']}")).json()
    libres: dict[str, list[int]] = {}
    for a in detalle["asientos"]:
        if a["estado"] == "libre":
            libres.setdefault(a["tipo_asiento"], []).append(a["numero"])
    return salida["id"], libres


def comprador(documento: str = "7000001", **extra) -> dict:
    return {
        "numero_documento": documento,
        "nombres": "prueba",
        "apellidos": "automática",
        "telefono": "+591 70000002",
        "email": "prueba@correo.demo",
        **extra,
    }


def pasajero(asiento: int, documento: str = "7000001", **extra) -> dict:
    return {
        "numero_asiento": asiento,
        "numero_documento": documento,
        "nombres": "Prueba",
        "apellidos": "Automática",
        **extra,
    }
