# El Mexicano Web

Portal público y panel de operación de la réplica de **Transportes El Mexicano S.R.L.** Consume la API de [`../backend`](../backend).

**Stack:** Vue 3.5 · TypeScript · Vite · Tailwind CSS 4 · Vue Router · Pinia · TanStack Query · openapi-fetch (tipos generados del OpenAPI) · reka-ui · ECharts · Zod · Vitest · Playwright.

## Qué incluye

**Portal público** (sin cuentas de cliente):
- Búsqueda de pasajes con calendario de precios, resultados, mapa de asientos de dos pisos, datos de pasajeros, pago simulado (QR, tarjeta, Tigo Money) y e-tickets con QR imprimibles.
- *Mi reserva*: consulta con código + documento, cancelación y solicitud de reembolso.
- Rastreo de encomiendas por guía, cotizador de carga y solicitud de puerta a puerta.
- Rutas e itinerarios, buses, oficinas con horarios y mapa, centro de ayuda con búsqueda y páginas de contenido.

**Panel de operación** (`/admin`, menú según el rol):
- Tablero con indicadores del día, salidas en vivo y novedades.
- Salidas: estado, demoras, bus, tripulación y manifiesto. Boletería (punto de venta, atajo F9) y abordaje con lector QR por cámara.
- Ventas, cobros en ventanilla y reembolsos (aprobación y pago).
- Encomiendas: registro con cotización en vivo y comprobante imprimible, detalle con rastreo, despacho en bus o furgón, cobro y entrega con PIN. Tablero de puerta a puerta con asignación de repartidor.
- Catálogos (oficinas y horarios, rutas, horarios de salida, feriados, buses, vehículos, tarifas, cuentas corporativas, preguntas frecuentes, páginas del sitio y parámetros), personal, clientes, reportes con gráficos y exportación CSV, y auditoría.
- Modo oscuro, búsqueda global y diseño adaptable a celular.

## Puesta en marcha

Requisitos: Node 20+ y pnpm. El backend debe estar corriendo (por defecto en `http://localhost:8000`).

```bash
cd frontend
pnpm install
cp .env.example .env.local      # opcional: cambia VITE_API_PROXY si la API no está en :8000
pnpm dev                        # http://localhost:5173
```

En desarrollo Vite reenvía `/api` al backend, así que no hace falta CORS. Personal de prueba: ver `backend/README.md` (contraseña `ElMexicano2026!`).

## Scripts

| Comando | Qué hace |
|---|---|
| `pnpm dev` | Servidor de desarrollo |
| `pnpm build` | Verificación de tipos y build de producción en `dist/` |
| `pnpm preview` | Sirve el build localmente |
| `pnpm typecheck` / `pnpm lint` / `pnpm format` | Tipos, ESLint y Prettier |
| `pnpm test` | Pruebas unitarias y de componentes (Vitest) |
| `pnpm test:e2e` | Pruebas de extremo a extremo (Playwright) |
| `pnpm api:types` | Regenera `src/api/schema.d.ts` desde `openapi.json` |

### Pruebas de extremo a extremo

Necesitan el backend con los datos semilla. Como hacen muchos inicios de sesión seguidos, arranca la API sin límite de intentos:

```bash
# en backend/
RATE_LIMIT_ENABLED=false uvicorn app.main:app --port 8000
# en frontend/ (la primera vez: npx playwright install chromium)
pnpm test:e2e
```

Cubren la compra completa con tarjeta, rastreo, *Mi reserva*, páginas públicas (escritorio y celular), inicio de sesión, permisos por rol, cierre de sesión y que el token no sea accesible desde JavaScript.

### Tipos de la API

Cuando cambie el backend, exporta el esquema y regenera los tipos:

```bash
# en backend/
python -c "import json; from app.main import app; json.dump(app.openapi(), open('../frontend/openapi.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)"
# en frontend/
pnpm api:types
```

## Seguridad

- La sesión del panel es una cookie *httpOnly* `SameSite=Strict`: el token no se guarda en `localStorage` ni es legible por scripts. Todas las peticiones envían `X-Requested-With` (defensa CSRF que exige la API).
- El build inyecta una Content-Security-Policy estricta (`script-src 'self'`, sin scripts en línea); las fuentes se sirven desde el propio sitio.
- El contenido Markdown editable se sanea con DOMPurify antes de mostrarse; ESLint prohíbe `v-html` fuera de ese componente.
- Los datos de tarjeta no salen del navegador salvo el número para la simulación, y nunca se guardan. La compra en curso vive en `sessionStorage` (se borra al cerrar la pestaña).
- Las redirecciones tras el login solo aceptan rutas internas del panel.

En producción sirve `dist/` desde el mismo dominio que la API (o deja `VITE_API_BASE_URL` con su URL) y añade en el servidor web las cabeceras `X-Frame-Options: DENY` / `frame-ancestors 'none'` y HSTS, que no se pueden fijar desde el HTML. Configura el servidor para devolver `index.html` en rutas desconocidas (historial de Vue Router).

## Estructura

```
frontend/
├── e2e/                 pruebas Playwright
├── public/              favicon
└── src/
    ├── api/             cliente tipado, consultas compartidas y tipos generados
    ├── components/      ui/ (sistema de diseño), booking/, cargo/, tracking/, admin/, charts/, brand/
    ├── composables/     cuenta regresiva, atributos de campos
    ├── layouts/         PublicLayout y AdminLayout
    ├── lib/             formatos (es-BO, America/La_Paz), etiquetas, roles, validación, tarjetas
    ├── pages/           public/ y admin/
    ├── router/          rutas, guardas por rol y títulos
    ├── stores/          sesión, compra en curso, avisos y tema
    └── styles/          tokens de diseño y utilidades (Tailwind 4)
```
