#!/usr/bin/env bash
# Respaldo diario de la base local. Guarda uno por día de la semana (se rotan solos: 7 respaldos).
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESTINO="${BACKUP_DIR:-$HOME/backups}"
mkdir -p "$DESTINO"

URL="$(grep -E '^DATABASE_URL=' "$APP_DIR/backend/.env" | head -1 | cut -d= -f2-)"
pg_dump --no-owner --no-privileges "$URL" | gzip > "$DESTINO/elmexicano-$(date +%u).sql.gz"
chmod 600 "$DESTINO"/elmexicano-*.sql.gz
