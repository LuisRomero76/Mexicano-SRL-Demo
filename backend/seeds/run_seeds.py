"""Carga los datos semilla.

Uso:
    python -m seeds.run_seeds            # idempotente: actualiza catálogos y agrega salidas nuevas
    python -m seeds.run_seeds --reset    # vacía las tablas (salvo api_keys) y recarga todo
    python -m seeds.run_seeds --solo-salidas   # tarea diaria: salidas nuevas y estados, sin tocar catálogos

La API key del agente de voz se crea la primera vez y se imprime una sola vez; `--reset` la conserva
para no romper la configuración de ElevenLabs. Para cambiarla: python -m seeds.api_key --rotar
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.models import Base
from app.models.vistas import SEQUENCES
from app.services import api_keys
from app.utils.telefonos import normalizar_e164
from seeds.catalogos import seed_catalogos
from seeds.data import demo
from seeds.operacion import seed_salidas
from seeds.transaccional import seed_transaccional, ya_sembrado

# Tablas que --reset no vacía: credenciales configuradas fuera del sistema.
CONSERVAR_EN_RESET = {"api_keys"}


async def _reset(session) -> None:
    tablas = ", ".join(t.name for t in Base.metadata.sorted_tables if t.name not in CONSERVAR_EN_RESET)
    await session.execute(text(f"TRUNCATE TABLE {tablas} RESTART IDENTITY CASCADE"))
    for nombre, inicio in SEQUENCES.items():
        await session.execute(text(f"ALTER SEQUENCE {nombre} RESTART WITH {inicio}"))
    await session.commit()


async def _resumen(session) -> list[tuple[str, int]]:
    conteos = []
    for tabla in Base.metadata.sorted_tables:
        conteos.append((tabla.name, await session.scalar(select(func.count()).select_from(tabla))))
    return conteos


async def solo_salidas() -> None:
    """Para la tarea programada: no sobrescribe los catálogos editados desde el panel."""
    async with SessionLocal() as session:
        await seed_salidas(session)
    await engine.dispose()
    print("Salidas generadas y estados actualizados.")


async def main(reset: bool) -> None:
    settings = get_settings()
    telefono_demo = normalizar_e164(settings.demo_telefono_e164)
    if not telefono_demo:
        sys.exit("DEMO_TELEFONO_E164 no es un teléfono válido (ej. 59170000000).")

    async with SessionLocal() as session:
        if reset:
            print("Vaciando tablas…")
            await _reset(session)
        print("Catálogos (datos reales + demo)…")
        await seed_catalogos(session)
        clave_bot = await api_keys.asegurar(
            session, api_keys.KEY_AGENTE, [api_keys.SCOPE_LECTURA, api_keys.SCOPE_ESCRITURA]
        )
        print("Salidas, buses y tripulación…")
        await seed_salidas(session)
        if await ya_sembrado(session):
            print("Datos transaccionales ya existen (usa --reset para regenerarlos).")
        else:
            print("Clientes, ventas, encomiendas y puerta a puerta…")
            await seed_transaccional(session, telefono_demo)

        print("\nResumen de filas por tabla")
        print("-" * 40)
        for tabla, n in await _resumen(session):
            print(f"{tabla:<32}{n:>8}")

    await engine.dispose()
    print(
        "\nPersonal demo (todas con la misma contraseña):\n"
        f"  contraseña: {demo.PASSWORD_DEMO}\n"
        "  admin@elmexicanosrl.com · supervisor@ · boleteria.sucre@ · bodega.sucre@ · reparto.sucre@ …\n"
        f"\nPruebas con tu teléfono {telefono_demo}:\n"
        "  Guías: 26000101 (lista, PIN 4821) · 26000102 (en tránsito) · 26000103 (entregada) · "
        "26000104 (en reparto) · 26000105 (otro número) · 26000106 (pago en destino)\n"
        "  Reservas: MX7K2P (pagada) · MX9H4R (pendiente) · MX3T8W (salida demorada) — documento 6123456"
    )
    if clave_bot:
        print(
            f"\nAPI key del agente de voz ({api_keys.KEY_AGENTE}), cabecera X-Bot-Key:\n  {clave_bot}\n"
            "  Guárdala ahora (por ejemplo como secreto en ElevenLabs): no se vuelve a mostrar.\n"
            "  Si la pierdes, genera otra con: python -m seeds.api_key --rotar"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga datos semilla de El Mexicano")
    parser.add_argument("--reset", action="store_true", help="Vacía todas las tablas antes de cargar")
    parser.add_argument("--solo-salidas", action="store_true", help="Solo genera salidas y actualiza estados")
    args = parser.parse_args()
    asyncio.run(solo_salidas() if args.solo_salidas else main(args.reset))
