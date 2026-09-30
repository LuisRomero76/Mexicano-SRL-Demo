# Despliegue gratuito: Vercel + Render + Neon

Alternativa temporal mientras no haya una VPS. Todo gratis, sin servidor propio.

```
Navegador ──HTTPS──> Vercel (frontend) ─┬─ /        → dist/ (Vue)
                                         └─ /api/*   → Render (FastAPI) ──> Neon (PostgreSQL)
```

El navegador solo ve el dominio de Vercel: Vercel reenvía `/api/*` a Render, así la cookie de sesión (`SameSite=Strict`) funciona sin cambios en el código.

**Regiones:** Render no tiene región en Sudamérica. Usa **Virginia (US East)** en Render y deja Neon en **AWS US East 1 (N. Virginia)**: API y base quedan juntas (lo que más pesa, porque cada petición hace varias consultas). Entre Bolivia y Virginia hay unos 150 ms, aceptable.

**Limitaciones del plan gratuito:**
- Render apaga la API tras 15 minutos sin tráfico; la primera petición después tarda 30–60 s. El paso 5 lo evita con un ping.
- Neon suspende la base tras 5 minutos sin consultas y tiene un límite mensual de horas de cómputo (míralo en *Usage*). El ping del paso 5 usa `/ping`, que no toca la base.
- Render gratis no tiene cron: las salidas diarias las genera GitHub Actions (paso 6).

## 1 · Preparar la base (desde tu PC)

Tu `backend/.env` ya apunta a Neon. En `backend/`, con el entorno de conda activo:

```powershell
alembic upgrade head                  # crea las tablas nuevas (api_keys, bot_consultas_log)
python -m seeds.run_seeds             # actualiza catálogos y salidas (no borra datos)
python -m seeds.api_key --rotar       # muestra la API key del agente de voz UNA vez: guárdala
```

## 2 · Backend en Render

1. Entra a https://render.com con tu cuenta de GitHub.
2. **New → Web Service → Build and deploy from a Git repository** → autoriza y elige `Mexicano-SRL-Demo`.
3. Completa:

   | Campo | Valor |
   |---|---|
   | Name | `elmexicano-api` (define la URL `https://elmexicano-api.onrender.com`) |
   | Region | **Virginia (US East)** |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` |
   | Instance Type | **Free** |

4. **Environment Variables** (*Add from .env* o una por una):

   | Variable | Valor |
   |---|---|
   | `PYTHON_VERSION` | `3.12.7` |
   | `DATABASE_URL` | la cadena **pooled** de Neon (host con `-pooler`), igual que en tu `.env` |
   | `DATABASE_URL_DIRECT` | la cadena **directa** de Neon (sin `-pooler`) |
   | `APP_ENV` | `production` |
   | `APP_TZ` | `America/La_Paz` |
   | `JWT_SECRET` | una cadena aleatoria larga: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `JWT_EXPIRE_MINUTES` | `480` |
   | `DEMO_TELEFONO_E164` | tu número de prueba (el mismo del `.env`) |
   | `CORS_ORIGINS` | `https://TU-PROYECTO.vercel.app` (lo completas después del paso 3) |
   | `COOKIE_SECURE` | `true` |
   | `DOCS_ENABLED` | `false` |
   | `TRUST_PROXY_HEADERS` | `true` |
   | `RATE_LIMIT_ENABLED` | `true` |
   | `JOB_EXPIRAR_RESERVAS_SEGUNDOS` | `1800` (despierta la base cada 30 min, no cada minuto) |

5. En **Advanced → Health Check Path** pon `/ping`.
6. **Create Web Service**. El primer despliegue tarda unos minutos. Al terminar, abre `https://elmexicano-api.onrender.com/health`: debe responder `"estado":"ok"`.

Si Render te asigna otra URL (porque el nombre estaba ocupado), cámbiala en `frontend/vercel.json` y haz `git push`.

## 3 · Frontend en Vercel

1. Entra a https://vercel.com con tu cuenta de GitHub.
2. **Add New → Project** → importa `Mexicano-SRL-Demo`.
3. **Root Directory:** `frontend`. Vercel lee `frontend/vercel.json` (framework Vite, `pnpm build`, salida `dist`, reenvío de `/api`).
4. No hace falta ninguna variable de entorno. **Deploy**.
5. Anota la URL (por ejemplo `https://mexicano-srl-demo.vercel.app`) y ponla en `CORS_ORIGINS` en Render (se redespliega solo).

## 4 · Comprobar

1. Abre la URL de Vercel: portal, búsqueda de pasajes, rastreo de la guía `26000101`.
2. `/admin` → inicia sesión. En las herramientas del navegador, la cookie `em_session` debe ser *Secure* y *HttpOnly*.
3. **Cambia las contraseñas de demostración** desde *Personal* (la de demo está en el repositorio).
4. Agente de voz: la URL base para ElevenLabs es `https://TU-PROYECTO.vercel.app/api/bot` (o directamente `https://elmexicano-api.onrender.com/api/bot`).

## 5 · Mantener la API despierta (opcional, recomendado para el agente de voz)

En https://cron-job.org (gratis) crea un trabajo que haga `GET https://elmexicano-api.onrender.com/ping` cada **10 minutos**. `/ping` no consulta la base, así que Neon sigue suspendiéndose y no gasta horas de cómputo. Render gratis da 750 horas al mes: alcanza para tener un servicio encendido todo el mes.

## 6 · Salidas diarias con GitHub Actions

El repositorio trae `.github/workflows/salidas-diarias.yml`, que ejecuta `seeds.run_seeds --solo-salidas` cada día a las 04:00 de Bolivia.

1. En GitHub: repositorio → **Settings → Secrets and variables → Actions → New repository secret**.
2. Nombre `DATABASE_URL`, valor: la cadena **directa** de Neon.
3. Para probarlo: pestaña **Actions → Salidas diarias → Run workflow**.

## Actualizar

Cada `git push` a `main` redespliega Render y Vercel solos. Las migraciones se aplican al arrancar la API (`alembic upgrade head` en el Start Command).

## Pasar luego a Oracle Cloud

Cuando tengas la VPS, sigue `deploy/README.md`. Puedes llevarte los datos con `pg_dump` desde Neon y `psql` en el servidor, o empezar limpio con los datos semilla.
