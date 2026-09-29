"""Gestión de API keys del agente de voz.

Uso:
    python -m seeds.api_key --rotar                       # nueva key para elevenlabs-agent (invalida la anterior)
    python -m seeds.api_key --rotar --nombre otro-agente --solo-lectura
    python -m seeds.api_key --revocar --nombre otro-agente
"""

import argparse
import asyncio
import sys

from app.core.db import SessionLocal, engine
from app.services import api_keys


async def main(nombre: str, rotar: bool, revocar: bool, solo_lectura: bool) -> None:
    async with SessionLocal() as session:
        if revocar:
            ok = await api_keys.revocar(session, nombre)
            print(f"Key «{nombre}» revocada." if ok else f"No hay una key activa llamada «{nombre}».")
        elif rotar:
            scopes = [api_keys.SCOPE_LECTURA] if solo_lectura else [api_keys.SCOPE_LECTURA, api_keys.SCOPE_ESCRITURA]
            clave = await api_keys.crear_o_rotar(session, nombre, scopes)
            print(f"Nueva API key para «{nombre}» ({', '.join(scopes)}), cabecera X-Bot-Key:\n  {clave}")
            print("Guárdala ahora: no se vuelve a mostrar. La key anterior deja de funcionar en menos de un minuto.")
        else:
            sys.exit("Indica --rotar o --revocar.")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API keys del agente de voz")
    parser.add_argument("--nombre", default=api_keys.KEY_AGENTE)
    parser.add_argument("--rotar", action="store_true", help="Crea la key o la reemplaza por una nueva")
    parser.add_argument("--revocar", action="store_true", help="Desactiva la key")
    parser.add_argument("--solo-lectura", action="store_true", help="Sin permiso bot:write")
    a = parser.parse_args()
    asyncio.run(main(a.nombre, a.rotar, a.revocar, a.solo_lectura))
