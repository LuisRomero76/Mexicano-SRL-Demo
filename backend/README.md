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
python -m seeds.run_seeds --reset          # carga completa desde cero (conserva las API keys)
python -m seeds.run_seeds                  # idempotente: actualiza catálogos y agrega salidas de los próximos 30 días
python -m seeds.run_seeds --solo-salidas   # solo salidas y estados; no toca lo editado desde el panel
```

Conviene correr `python -m seeds.run_seeds --solo-salidas` a diario (en el servidor lo hace un cron): genera las salidas nuevas y actualiza los estados (en ruta, llegada) según la hora. Sin `--solo-salidas` también restablece los catálogos con los datos semilla, lo que deshace los cambios hechos desde el panel.

La primera carga crea la API key del agente de voz y **la imprime una sola vez** (ver la sección 7).

## 4. Levantar el servidor

```powershell
uvicorn app.main:app --reload
```

- Documentación interactiva: http://localhost:8000/docs (ReDoc en `/redoc`)
- Estado: http://localhost:8000/health (incluye un ping a la base)

Para probar el agente de voz contra tu computadora: `ngrok http 8000` (ElevenLabs necesita una URL pública con HTTPS).

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

## 7. Agente de voz (ElevenLabs)

API en `/api/bot` para las *webhook tools* de un agente de ElevenLabs. Todas las respuestas pesan menos de 1 KB y traen `mensaje`, una frase en español lista para decirse en voz alta, más los datos mínimos. Cuando no hay resultado responden **200** con `{"encontrado": false, "mensaje": "…"}` y una sugerencia (por ejemplo: «No encontré la guía 26000999. ¿Puedes confirmar los 8 dígitos?»), para que el agente pueda decirlo tal cual. Con la base en el mismo servidor responden en menos de 100 ms.

### API key

- La primera carga de datos (`python -m seeds.run_seeds`) crea la key `elevenlabs-agent` (permisos `bot:read` y `bot:write`) y **la imprime una sola vez**. En la base solo queda su SHA-256.
- `--reset` conserva la key. Para reemplazarla: `python -m seeds.api_key --rotar` (la anterior deja de funcionar en menos de un minuto). Para revocarla: `python -m seeds.api_key --revocar --nombre elevenlabs-agent`.
- Se envía en la cabecera `X-Bot-Key`. Sin key o con una inválida: 401; sin el permiso: 403.
- Límite: `BOT_RATE_LIMIT_POR_MINUTO` solicitudes por minuto **por key** (120 por defecto; al pasarse, 429 con `Retry-After`). Los intentos con keys inválidas se limitan por IP.

### Privacidad por `caller_id`

`caller_id` es el teléfono de quien llama (en ElevenLabs, `{{system__caller_id}}`). Se normaliza a E.164 solo dígitos (`+591 70000001`, `59170000001` y `70000001` son el mismo número).

| | Coincide con destinatario, remitente o comprador | Otro número, vacío o `anonymous` |
|---|---|---|
| Estado, ciudades, si está lista para recoger | Sí | Sí |
| Oficina de retiro con dirección y horario (información pública) | Sí | Sí |
| Si hay pago pendiente | Sí, con el monto | Sí, sin monto |
| Nombres, montos, domicilio, últimos eventos, detalle del viaje | Sí | No |
| PIN de retiro | **Nunca** | **Nunca** |

El PIN no se devuelve en ningún caso: el `caller_id` se puede falsificar y el PIN es lo que protege la entrega. El agente debe indicar que el código de retiro lo tiene el remitente.

### Endpoints

```bash
BASE=https://tu-dominio
KEY=emk_...

# rastrear_encomienda: estado, oficina de retiro, pago pendiente y últimos 3 eventos
curl -s "$BASE/api/bot/encomiendas/26000101?caller_id=59170000001" -H "X-Bot-Key: $KEY"
# mis_encomiendas: envíos activos donde quien llama es remitente o destinatario (máx. 5)
curl -s "$BASE/api/bot/encomiendas?caller_id=59170000001" -H "X-Bot-Key: $KEY"
# consultar_salidas: acepta alias de ciudad y fechas como hoy, mañana, el viernes, 2/10
curl -s -G "$BASE/api/bot/salidas" -H "X-Bot-Key: $KEY" \
  --data-urlencode "origen=Sucre" --data-urlencode "destino=Santa Cruz" --data-urlencode "fecha=mañana"
# listar_rutas
curl -s "$BASE/api/bot/rutas" -H "X-Bot-Key: $KEY"
# cotizar_envio: tipo (sobre, paquete, carga) opcional; puerta_a_puerta=true para entrega a domicilio
curl -s "$BASE/api/bot/tarifas-carga?origen=Sucre&destino=La%20Paz&peso_kg=3.5&puerta_a_puerta=false" -H "X-Bot-Key: $KEY"
# consultar_reserva: detalle del viaje solo para el comprador
curl -s "$BASE/api/bot/reservas/MX7K2P?caller_id=59170000001" -H "X-Bot-Key: $KEY"
# info_oficinas: tipo opcional (pasajes o carga)
curl -s "$BASE/api/bot/oficinas?ciudad=Santa%20Cruz&tipo=carga" -H "X-Bot-Key: $KEY"
# buscar_faq: devuelve la respuesta corta pensada para voz
curl -s -G "$BASE/api/bot/faqs/buscar" -H "X-Bot-Key: $KEY" --data-urlencode "q=¿puedo llevar a mi perro?"
# info_empresa
curl -s "$BASE/api/bot/empresa" -H "X-Bot-Key: $KEY"
# solicitar_puerta_a_puerta (permiso bot:write). Si falta un dato, el mensaje dice cuál pedir.
curl -s -X POST "$BASE/api/bot/puerta-a-puerta" -H "X-Bot-Key: $KEY" -H "Content-Type: application/json" -d '{
  "caller_id": "59170000001", "tipo": "recojo", "ciudad": "Sucre", "numero_documento": "7654321",
  "nombres": "Rosa", "apellidos": "Quispe", "direccion": "Calle Junín 450", "fecha": "el lunes", "peso_kg": "3"
}'
```

Ejemplo de respuesta (`rastrear_encomienda` con el número del destinatario):

```json
{
  "encontrado": true, "datos_completos": true, "numero_guia": "26000101", "estado": "lista_para_retiro",
  "lista_para_retiro": true, "pago_pendiente": false, "oficina_retiro": "Bodega Santa Cruz 2",
  "remitente": "…", "destinatario": "…", "monto_pendiente_bs": null, "ultimos_eventos": ["…"],
  "mensaje": "Tu encomienda con guía 26000101, de Sucre a Santa Cruz, está lista para recoger. Se recoge en Bodega Santa Cruz 2, Av. Intermodal s/n entre Daniel Salamanca y Hernando Siles; atiende de lunes a sábado de 08:00 a 18:00. Hay que presentar el documento y el código de retiro que tiene el remitente."
}
```

### Configuración en ElevenLabs

1. **Secreto:** en el workspace de ElevenLabs crea un *secret* llamado `mexicano_bot_key` con el valor de la API key.
2. **Tools:** en el agente, *Tools → Add tool → Webhook*, una por fila de la tabla. En todas:
   - **Header:** `X-Bot-Key`, con el valor tomado del secreto `mexicano_bot_key`.
   - **`caller_id`** (cuando aparece): tipo de valor **Dynamic variable** = `system__caller_id`. No lo decide el modelo.
   - Los demás parámetros son de tipo **LLM prompt**: la última columna es la descripción que el modelo usa para completarlos.

| Tool | Método y URL | Parámetros | Descripción para el modelo |
|---|---|---|---|
| `rastrear_encomienda` | GET `https://tu-dominio/api/bot/encomiendas/{numero_guia}` | path `numero_guia` (requerido), query `caller_id` | Número de guía de 8 dígitos, solo números |
| `mis_encomiendas` | GET `https://tu-dominio/api/bot/encomiendas` | query `caller_id` | — |
| `consultar_salidas` | GET `https://tu-dominio/api/bot/salidas` | query `origen`, `destino`, `fecha` | Ciudades tal como las dice el cliente; fecha como la dice (hoy, mañana, el viernes, 5 de octubre) |
| `listar_rutas` | GET `https://tu-dominio/api/bot/rutas` | — | — |
| `cotizar_envio` | GET `https://tu-dominio/api/bot/tarifas-carga` | query `origen`, `destino`, `peso_kg`, `tipo` y `puerta_a_puerta` (opcionales) | Peso en kilos; tipo sobre, paquete o carga solo si el cliente lo dice; `true` si quiere entrega a domicilio |
| `consultar_reserva` | GET `https://tu-dominio/api/bot/reservas/{codigo}` | path `codigo` (requerido), query `caller_id` | Código de reserva de 6 letras y números |
| `info_oficinas` | GET `https://tu-dominio/api/bot/oficinas` | query `ciudad`, `tipo` (opcional) | Ciudad; tipo `pasajes` o `carga` si el cliente lo aclara |
| `buscar_faq` | GET `https://tu-dominio/api/bot/faqs/buscar` | query `q` | La pregunta del cliente con sus palabras |
| `info_empresa` | GET `https://tu-dominio/api/bot/empresa` | — | — |
| `solicitar_puerta_a_puerta` | POST `https://tu-dominio/api/bot/puerta-a-puerta` | body: `caller_id` (dynamic variable), `tipo`, `ciudad`, `numero_documento`, `nombres`, `apellidos`, `direccion`, `referencia`, `fecha`, `peso_kg`, `descripcion`, `numero_guia`, `telefono` | `tipo` recojo o entrega; carnet, nombre, dirección y día; `telefono` solo si quiere que lo contacten a otro número; `numero_guia` para entregas |

3. **Prompt del agente** (sugerencia): «Usa las herramientas para responder sobre encomiendas, pasajes, oficinas y preguntas frecuentes. Di el contenido de `mensaje` con tus palabras, sin inventar datos. Nunca pidas ni digas el código de retiro. Si `encontrado` es falso, sigue la sugerencia del mensaje.»

`system__caller_id` solo tiene valor en llamadas telefónicas (Twilio o SIP). En las pruebas desde el navegador llega vacío y la API responde como a un número desconocido. Para ver los datos completos, prueba con `curl` y `caller_id=` el número de `DEMO_TELEFONO_E164`.

### Registro

Cada llamada queda en `bot_consultas_log` (tool, parámetros, `caller_id`, si encontró resultado, si coincidió el número, respuesta, código HTTP y latencia). Se escribe después de enviar la respuesta, así que no suma latencia. Desde el panel: *Auditoría → Consultas del bot*, o `GET /api/v1/admin/bot/consultas?tool=&encontrado=`.

## 8. Tests

Los tests **vacían y recargan** la base que les indiques: usa una base de pruebas, nunca la de trabajo. Con Neon lo más simple es crear un *branch* de pruebas.

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres@localhost:5432/elmexicano_test"
pytest
ruff check . ; ruff format --check .
```

Cubren: no doble venta de asientos (incluida la concurrencia), precio especial de salida frente a tarifa vigente, descuentos sobre la tarifa máxima referencial, tarifas especiales solo en boletería, cotización de carga y sus límites, reglas de puerta a puerta (días hábiles, feriados, franjas), privacidad del rastreo público, guías y reservas fijas, reembolsos (85 % y 100 %), expiración de reservas, permisos por rol, el flujo completo de bodega y la API del agente de voz (key, permisos, límite por key, privacidad por `caller_id` con las guías 26000101 y 26000105, respuestas de menos de 1 KB y registro).

## 9. Estructura

```
backend/
├── alembic/            migraciones (la inicial incluye vistas, triggers y secuencias)
├── app/
│   ├── api/v1/         routers: publico/ y admin/ (sin lógica de negocio)
│   ├── api/bot.py      API del agente de voz (/api/bot)
│   ├── core/           config, base de datos, seguridad, errores, dependencias
│   ├── models/         SQLAlchemy por módulo del diseño (A–H) y vistas
│   ├── schemas/        Pydantic (entrada y salida)
│   ├── services/       reglas de negocio
│   └── utils/          fechas (America/La_Paz), teléfonos E.164, códigos
├── seeds/              datos reales (data/reales.py) y demo (data/demo.py)
└── tests/
```

## 10. Pendiente

- **Servidor MCP** para el agente de voz, reutilizando `app/services/bot.py`.
- Reemplazar los datos demo por reales cuando estén disponibles: precios, horarios de salida, paradas, tarifas de carga, días de atención y NIT .
