#!/usr/bin/env bash
# Publica la última versión de la rama main: código, dependencias, migraciones y frontend.
# Uso (en la VPS):  ~/app/deploy/update.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_ROOT="/var/www/elmexicano"

echo "==> Descargando cambios"
git -C "$APP_DIR" pull --ff-only

echo "==> Backend"
cd "$APP_DIR/backend"
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/alembic upgrade head
sudo systemctl restart elmexicano-api

echo "==> Frontend"
cd "$APP_DIR/frontend"
pnpm install --frozen-lockfile
pnpm build
sudo rsync -a --delete dist/ "$WEB_ROOT/"

echo "==> Comprobando"
sleep 2
curl -fsS http://127.0.0.1:8000/health && echo
echo "Listo."
