# El Mexicano — Bus Tickets & Cargo Platform (Demo)

A full-stack replica of the booking and operations platform of **Transportes El Mexicano S.R.L.**, a Bolivian intercity bus and cargo company. It includes a public customer portal and an internal operations panel, backed by a REST API.

> Demo project. Prices, schedules and some operational data are sample data; the company's public information comes from its website.

| | |
|---|---|
| [`backend/`](backend) | FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL (Neon) · pytest |
| [`frontend/`](frontend) | Vue 3 · TypeScript · Vite · Tailwind CSS 4 · TanStack Query · Vitest · Playwright |

## Features

**Customer portal** — ticket search with a price calendar, two-deck seat map, passenger details, simulated payments (QR, card, Tigo Money), printable e-tickets with QR, booking lookup/cancellation/refunds, parcel tracking, cargo quotes, door-to-door requests, routes, fleet, offices and a searchable help center.

**Operations panel** — role-based access (admin, supervisor, ticket office, warehouse, courier, driver, support): live dashboard, departures and manifests, point-of-sale ticketing, QR boarding, sales and refunds, parcel intake/dispatch/delivery with PIN, door-to-door board, master data catalogs, staff, customers, reports with charts and an audit log.

**Security** — httpOnly `SameSite=Strict` session cookie, CSRF header check, per-IP rate limiting, strict security headers and CSP, Argon2 password hashing, server-side role checks on every operation.

## Quick start

1. **Backend** (see [`backend/README.md`](backend/README.md)):
   ```bash
   cd backend
   conda env create -f environment.yml && conda activate elmexicano-api
   cp .env.example .env          # set DATABASE_URL, JWT_SECRET, etc.
   alembic upgrade head
   python -m seeds.run_seeds --reset
   uvicorn app.main:app --reload # http://localhost:8000/docs
   ```
2. **Frontend** (see [`frontend/README.md`](frontend/README.md)):
   ```bash
   cd frontend
   pnpm install
   pnpm dev                      # http://localhost:5173
   ```
3. Sign in to the panel at `/admin` with a demo account, e.g. `supervisor@elmexicanosrl.com` / `ElMexicano2026!`.

## Tests

```bash
cd backend && pytest                    # API: business rules, permissions, security
cd frontend && pnpm test                # unit and component tests
cd frontend && pnpm test:e2e            # end-to-end (needs the API running)
```
