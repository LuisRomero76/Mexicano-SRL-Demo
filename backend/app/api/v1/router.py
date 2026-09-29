from fastapi import APIRouter

from app.api.v1.admin import carga as admin_carga
from app.api.v1.admin import catalogos as admin_catalogos
from app.api.v1.admin import reportes as admin_reportes
from app.api.v1.admin import salidas as admin_salidas
from app.api.v1.admin import ventas as admin_ventas
from app.api.v1.publico import auth, carga, catalogos, contenido, reservas, salidas

api_router = APIRouter(prefix="/api/v1")

for modulo in (catalogos, salidas, reservas, carga, contenido, auth):
    api_router.include_router(modulo.router)

admin_router = APIRouter(prefix="/admin")
for modulo in (admin_salidas, admin_ventas, admin_carga, admin_catalogos, admin_reportes):
    admin_router.include_router(modulo.router)
api_router.include_router(admin_router)
