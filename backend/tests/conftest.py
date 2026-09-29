"""Fixtures de tests.

Los tests corren contra una base PostgreSQL de pruebas (NUNCA la de Neon de producción):
    TEST_DATABASE_URL=postgresql://postgres@localhost:5432/elmexicano_test
La base se migra con Alembic y se carga con los seeds una vez por sesión.
"""

import os

TEST_DB = os.environ.get("TEST_DATABASE_URL")
if not TEST_DB:
    raise RuntimeError("Define TEST_DATABASE_URL con una base PostgreSQL de pruebas (se vacía en cada corrida).")
if "neon.tech" in TEST_DB and os.environ.get("PERMITIR_TESTS_EN_NEON") != "1":
    raise RuntimeError("TEST_DATABASE_URL apunta a Neon; usa una base de pruebas o define PERMITIR_TESTS_EN_NEON=1.")

# Debe configurarse antes de importar la app (el motor se crea al importar).
os.environ["DATABASE_URL"] = TEST_DB
os.environ["DATABASE_URL_DIRECT"] = TEST_DB
os.environ["DEMO_TELEFONO_E164"] = "59170000001"
os.environ["JOB_EXPIRAR_RESERVAS_SEGUNDOS"] = "0"
os.environ["RATE_LIMIT_ENABLED"] = "0"
os.environ.setdefault("JWT_SECRET", "secreto-de-tests-0123456789abcdefghij")

from datetime import date, timedelta  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
from app.main import app  # noqa: E402
from seeds.data.demo import PASSWORD_DEMO  # noqa: E402
from seeds.run_seeds import main as run_seeds  # noqa: E402

TELEFONO_DEMO = "59170000001"
DOC_DEMO = "6123456"


@pytest.fixture(scope="session", autouse=True)
async def base_de_datos():
    import asyncio

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    # Alembic usa asyncio.run internamente: se ejecuta en otro hilo.
    await asyncio.to_thread(command.upgrade, cfg, "head")
    await run_seeds(reset=True)
    yield


@pytest.fixture(scope="session")
async def client():
    transport = httpx.ASGITransport(app=app)

    # Cliente "de API": descarta las cookies para que cada test decida su autenticación (Bearer).
    async def _sin_cookies(response: httpx.Response) -> None:
        c.cookies.clear()

    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", event_hooks={"response": [_sin_cookies]}
    ) as c:
        yield c


async def _token(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    r = await client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD_DEMO})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
async def admin(client):
    return await _token(client, "admin@elmexicanosrl.com")


@pytest.fixture(scope="session")
async def supervisor(client):
    return await _token(client, "supervisor@elmexicanosrl.com")


@pytest.fixture(scope="session")
async def boletero(client):
    return await _token(client, "boleteria.sucre@elmexicanosrl.com")


@pytest.fixture(scope="session")
async def bodega(client):
    return await _token(client, "bodega.sucre@elmexicanosrl.com")


def proximo_dia_habil(desde: date, *, saltar: int = 0) -> date:
    """Próximo lunes a viernes (los tests evitan las fechas de feriados sembrados)."""
    dia = desde
    encontrados = -1
    while True:
        dia += timedelta(days=1)
        if dia.isoweekday() <= 5 and (dia.month, dia.day) not in {(10, 12), (11, 2), (11, 10), (12, 25), (1, 1)}:
            encontrados += 1
            if encontrados == saltar:
                return dia


def proximo_sabado(desde: date) -> date:
    return desde + timedelta(days=(5 - desde.weekday()) % 7 or 7)
