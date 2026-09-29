# El Mexicano API

Backend réplica (demo) de **Transportes El Mexicano S.R.L.** (https://www.elmexicanosrl.com): venta de pasajes, salidas y asientos, carga y encomiendas con rastreo, puerta a puerta, centro de ayuda y operación interna (boletería, bodega, reembolsos, reportes).

El frontend (portal público y panel de operación) está en [`../frontend`](../frontend).

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · asyncpg · PostgreSQL 16 (Neon) · Pydantic v2 · pytest · ruff.

---

## 1. Entorno (Anaconda)

```powershell
cd backend
conda env create -f environment.yml
conda activate elmexicano-api
```

Si `conda` no está en el PATH, usa la ruta completa: `& "$env:USERPROFILE\anaconda3\Scripts\conda.exe" env create -f environment.yml`, o abre el *Anaconda Prompt*.

## 2. Configurar Neon

1. En el panel de Neon crea un proyecto y una base `elmexicano` (PostgreSQL 16 o superior).
2. Copia `.env.example` a `.env` (ya hay uno con marcadores) y pega las dos cadenas **tal como las copias de Neon**:
   - `DATABASE_URL`: la **pooled** (el host contiene `-pooler`). La usa la app.
   - `DATABASE_URL_DIRECT`: la **directa** (sin `-pooler`). La usa Alembic.

   No hace falta cambiar el formato: la app convierte `postgresql://…?sslmode=require&channel_binding=require` al formato de asyncpg y, con el pooler, desactiva la caché de sentencias preparadas.
3. Cambia `JWT_SECRET` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) y pon tu número en `DEMO_TELEFONO_E164` (solo dígitos, con 591). Las guías y reservas de prueba quedan asociadas a ese número.

## 3. Migraciones y datos semilla

```powershell
alembic upgrade head                 # tablas, enums, índices, triggers, secuencias y vistas
python -m seeds.run_seeds --reset    # carga completa desde cero
python -m seeds.run_seeds            # idempotente: actualiza catálogos y agrega salidas de los próximos 30 días
```

Conviene volver a correr `python -m seeds.run_seeds` cada pocos días: genera las salidas nuevas y actualiza los estados (en ruta, llegada) según la hora.

## 4. Levantar el servidor

```powershell
uvicorn app.main:app --reload
```

- Documentación interactiva: http://localhost:8000/docs (ReDoc en `/redoc`)
- Estado: http://localhost:8000/health (incluye un ping a la base)

Para exponerlo hacia afuera (por ejemplo, para el futuro bot): `ngrok http 8000`.

## 5. Datos de prueba

**Personal** (todos con la contraseña `ElMexicano2026!`):

| Email | Rol |
|---|---|
| admin@elmexicanosrl.com | admin |
| supervisor@elmexicanosrl.com | supervisor |
| boleteria.sucre@ · boleteria.santacruz@ · boleteria.lapaz@ · boleteria.tarija@ | boletero |
| bodega.sucre@ · bodega.santacruz@ · bodega.lapaz@ | encargado de bodega |
| reparto.sucre@ · reparto.santacruz@ | repartidor |
| soporte@ | soporte |
| conductor01@ … conductor24@ | conductor |

(todos en `@elmexicanosrl.com`). En `/docs` usa el botón **Authorize** con email y contraseña.

**Guías fijas** (destinatario = `DEMO_TELEFONO_E164`, salvo la 105):

| Guía | Estado | Destino | PIN de retiro |
|---|---|---|---|
| 26000101 | lista para retiro | Santa Cruz | 4821 |
| 26000102 | en tránsito | La Paz | 7305 |
| 26000103 | entregada | Tarija | 1946 |
| 26000104 | en reparto (puerta a puerta) | Sucre | 5518 |
| 26000105 | lista para retiro (otro número) | Potosí | 3072 |
| 26000106 | llegó, pago en destino pendiente | El Alto | 8664 |

**Reservas fijas** (documento del comprador: `6123456`):

| Código | Estado |
|---|---|
| MX7K2P | pagada, 2 boletos Suite, Sucre → Santa Cruz mañana 20:00 |
| MX9H4R | pendiente de pago, Sucre → La Paz en 3 días |
| MX3T8W | pagada, Sucre → Tarija, salida demorada 45 min |

**Pagos simulados:** QR, tarjeta, Tigo Money y efectivo (este último solo en boletería). Una tarjeta terminada en `0002` simula un rechazo del banco.

## 6. API

Montos en bolivianos (número con 2 decimales); fechas en hora de Bolivia (`-04:00`). Los errores tienen siempre la forma `{"error": "codigo", "mensaje": "texto para mostrar", "detalle": …}`.

**Pública** (`/api/v1`): `empresa`, `ciudades`, `rutas`, `tipos-asiento`, `oficinas`, `politicas`, búsqueda de `salidas` y detalle con mapa de asientos, `reservas` (crear, consultar con documento, pagar, cancelar), reembolso de boletos, `carga/cotizar`, rastreo público de encomiendas (sin nombres, teléfonos, montos ni PIN), `puerta-a-puerta`, `faqs` y búsqueda full-text, `paginas`, `auth/login`.

**Operación** (`/api/v1/admin`, JWT con roles):
- **Salidas:** listar, generar desde plantillas de horario, cambiar estado (abordando, en ruta, llegada, demora, cancelación), asignar bus (valida superposición y mapa de asientos), tripulación (conductor + relevo en viajes largos), precio especial por salida, manifiesto de pasajeros y carga.
- **Boletería:** venta en ventanilla con tarifas especiales, cobro, abordaje por número o QR, equipaje con cálculo de exceso, reembolsos y su resolución.
- **Bodega:** registrar encomiendas (guía de 8 dígitos y PIN), eventos de rastreo con transiciones válidas, despacho en bus o en furgón, cobro y entrega con verificación de PIN; gestión de puerta a puerta.
- **Catálogos:** oficinas y horarios, buses, vehículos, rutas, plantillas, tarifas de pasaje y carga, FAQ, páginas, parámetros de negocio, feriados, cuentas corporativas, personal y clientes.
- **Reportes y auditoría:** ventas, ocupación, encomiendas y registro de acciones sensibles.

### Automatismos

- Las reservas sin pagar expiran a los 15 minutos (tarea en segundo plano cada `JOB_EXPIRAR_RESERVAS_SEGUNDOS`, y verificación al consultar).
- `en_ruta` marca *no-show* a quien no abordó y pone en tránsito las encomiendas asignadas al bus; `llegada` las marca como llegadas a destino.
- `cancelada` reembolsa al 100 % todos los boletos pagados y libera las encomiendas asignadas.

### Seguridad

- **Sesión del panel:** el login deja un JWT en una cookie `em_session` *httpOnly*, `SameSite=Strict` y limitada a `/api` (el JavaScript del navegador nunca ve el token). También se acepta `Authorization: Bearer` para `/docs` y clientes externos. `POST /api/v1/auth/logout` borra la cookie.
- **CSRF:** toda escritura autenticada por cookie exige la cabecera `X-Requested-With: XMLHttpRequest` (un formulario de otro sitio no puede enviarla).
- **Límite de intentos** por IP en login (10 cada 5 min), reservas, pagos y rastreo; responde `429` con `Retry-After`.
- **Cabeceras:** `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store` en respuestas con datos personales y HSTS cuando `COOKIE_SECURE=true`.
- **Contraseñas** con Argon2; mínimo 10 caracteres con letras y números. En producción la app no arranca con un `JWT_SECRET` débil.
- Los permisos por rol se validan en el servidor en cada operación; el rastreo público no expone nombres, teléfonos, montos ni el PIN.

**Producción:** `APP_ENV=production`, `COOKIE_SECURE=true`, `DOCS_ENABLED=false`, un `JWT_SECRET` largo y aleatorio, `CORS_ORIGINS` solo con el dominio real y, detrás de un proxy, `TRUST_PROXY_HEADERS=true`. Sirve el frontend y la API desde el mismo dominio (o subdominios del mismo sitio) para que la cookie `SameSite=Strict` funcione.

## 7. Tests

Los tests **vacían y recargan** la base que les indiques: usa una base de pruebas, nunca la de trabajo. Con Neon lo más simple es crear un *branch* de pruebas.

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres@localhost:5432/elmexicano_test"
pytest
ruff check . ; ruff format --check .
```

Cubren: no doble venta de asientos (incluida la concurrencia), precio especial de salida frente a tarifa vigente, descuentos sobre la tarifa máxima referencial, tarifas especiales solo en boletería, cotización de carga y sus límites, reglas de puerta a puerta (días hábiles, feriados, franjas), privacidad del rastreo público, guías y reservas fijas, reembolsos (85 % y 100 %), expiración de reservas, permisos por rol y el flujo completo de bodega.

## 8. Estructura

```
backend/
├── alembic/            migraciones (la inicial incluye vistas, triggers y secuencias)
├── app/
│   ├── api/v1/         routers: publico/ y admin/ (sin lógica de negocio)
│   ├── core/           config, base de datos, seguridad, errores, dependencias
│   ├── models/         SQLAlchemy por módulo del diseño (A–H) y vistas
│   ├── schemas/        Pydantic (entrada y salida)
│   ├── services/       reglas de negocio
│   └── utils/          fechas (America/La_Paz), teléfonos E.164, códigos
├── seeds/              datos reales (data/reales.py) y demo (data/demo.py)
└── tests/
```

## 9. Pendiente

- **Bot de atención (ElevenLabs):** endpoints `/api/bot`, servidor MCP, `api_keys` y registro de consultas (diferido). El modelo ya trae lo necesario: teléfonos E.164, códigos fáciles de dictar, `respuesta_corta_voz` en las FAQ, alias de ciudades y campos `mensaje` en lenguaje natural.
- Reemplazar los datos demo por reales cuando estén disponibles: precios, horarios de salida, paradas, tarifas de carga, días de atención y NIT .
