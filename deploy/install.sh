#!/usr/bin/env bash
# Instalación completa en una VPS Ubuntu 24.04 (Oracle Cloud Always Free, ARM o x86):
# PostgreSQL local + API (systemd) + frontend compilado + Caddy con HTTPS + tareas programadas.
#
# Uso (en la VPS, como el usuario "ubuntu", desde el repositorio clonado en ~/app):
#   DOMINIO=elmexicano-demo.duckdns.org ~/app/deploy/install.sh
# Opcional: DEMO_TELEFONO=591XXXXXXXX (número al que se asocian las guías y reservas de prueba).
#
# Se puede volver a ejecutar sin romper nada: reutiliza la base, el .env y los datos existentes.
set -euo pipefail

: "${DOMINIO:?Indica el dominio, por ejemplo: DOMINIO=elmexicano-demo.duckdns.org $0}"
DEMO_TELEFONO="${DEMO_TELEFONO:-59170000000}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USUARIO="$(id -un)"
WEB_ROOT="/var/www/elmexicano"
ENV_FILE="$APP_DIR/backend/.env"
DB_NOMBRE="elmexicano"
DB_USUARIO="elmexicano"

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

if [[ "$USUARIO" == "root" ]]; then
  echo "Ejecuta el script como tu usuario normal (ubuntu), no como root: usa sudo internamente." >&2
  exit 1
fi

paso "Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a
sudo -E apt-get update -y
sudo -E apt-get upgrade -y
sudo -E apt-get install -y \
  git curl rsync openssl python3-venv python3-pip postgresql netfilter-persistent \
  debian-keyring debian-archive-keyring apt-transport-https gnupg

paso "Zona horaria de Bolivia (para las tareas programadas)"
sudo timedatectl set-timezone America/La_Paz

paso "Firewall interno: puertos 80 y 443"
# Las imágenes de Ubuntu de Oracle terminan la cadena INPUT con un REJECT: la regla va antes.
for puerto in 80 443; do
  if ! sudo iptables -C INPUT -p tcp --dport "$puerto" -m state --state NEW -j ACCEPT 2>/dev/null; then
    rechazo="$(sudo iptables -L INPUT --line-numbers | awk '$2 == "REJECT" {print $1; exit}')"
    if [[ -n "$rechazo" ]]; then
      sudo iptables -I INPUT "$rechazo" -p tcp --dport "$puerto" -m state --state NEW -j ACCEPT
    else
      sudo iptables -A INPUT -p tcp --dport "$puerto" -m state --state NEW -j ACCEPT
    fi
  fi
done
sudo netfilter-persistent save

paso "Node.js 22 y pnpm"
if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1 | tr -d v)" -lt 20 ]]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo -E apt-get install -y nodejs
fi
command -v pnpm >/dev/null || sudo npm install -g pnpm@10.17.1

paso "Caddy"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo -E apt-get update -y
  sudo -E apt-get install -y caddy
fi

URL_ACTUAL="$(grep -sE '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)"
if [[ -z "$URL_ACTUAL" || "$URL_ACTUAL" == *"@localhost"* ]]; then
  paso "Base de datos PostgreSQL local (solo escucha en localhost)"
  if [[ -n "$URL_ACTUAL" ]]; then
    DB_CLAVE="$(sed -E 's#^postgresql://[^:]+:([^@]+)@.*#\1#' <<<"$URL_ACTUAL")"
  else
    DB_CLAVE="$(openssl rand -hex 24)"
  fi
  if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USUARIO'" | grep -q 1; then
    sudo -u postgres psql -qc "ALTER USER $DB_USUARIO WITH PASSWORD '$DB_CLAVE';"
  else
    sudo -u postgres psql -qc "CREATE USER $DB_USUARIO WITH PASSWORD '$DB_CLAVE';"
  fi
  if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NOMBRE'" | grep -q 1; then
    sudo -u postgres createdb -O "$DB_USUARIO" "$DB_NOMBRE"
  fi
else
  paso "Base de datos externa (definida en $ENV_FILE)"
  DB_CLAVE=""
fi

paso "Configuración de la API (.env)"
if [[ ! -f "$ENV_FILE" ]]; then
  umask 077
  cat > "$ENV_FILE" <<EOF
DATABASE_URL=postgresql://$DB_USUARIO:$DB_CLAVE@localhost:5432/$DB_NOMBRE
APP_ENV=production
APP_TZ=America/La_Paz
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n=+/')
JWT_EXPIRE_MINUTES=480
DEMO_TELEFONO_E164=$DEMO_TELEFONO
CORS_ORIGINS=https://$DOMINIO
JOB_EXPIRAR_RESERVAS_SEGUNDOS=60
COOKIE_SECURE=true
RATE_LIMIT_ENABLED=true
DOCS_ENABLED=false
TRUST_PROXY_HEADERS=true
EOF
  umask 022
  echo "Creado $ENV_FILE (secretos generados al azar)."
else
  echo "Ya existe $ENV_FILE: se conserva."
fi
chmod 600 "$ENV_FILE"

paso "Backend: entorno de Python, migraciones y datos"
cd "$APP_DIR/backend"
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/alembic upgrade head
URL_ACTUAL="$(grep -E '^DATABASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
USUARIOS="$(psql "$URL_ACTUAL" -tAc 'SELECT count(*) FROM usuarios')"
if [[ "$USUARIOS" == "0" ]]; then
  .venv/bin/python -m seeds.run_seeds --reset
else
  .venv/bin/python -m seeds.run_seeds
fi

paso "Servicio de la API"
sed -e "s#__USUARIO__#$USUARIO#g" -e "s#__APP_DIR__#$APP_DIR#g" \
  "$APP_DIR/deploy/elmexicano-api.service.template" | sudo tee /etc/systemd/system/elmexicano-api.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable elmexicano-api >/dev/null
sudo systemctl restart elmexicano-api

paso "Frontend"
cd "$APP_DIR/frontend"
pnpm install --frozen-lockfile
pnpm build
sudo mkdir -p "$WEB_ROOT"
sudo rsync -a --delete dist/ "$WEB_ROOT/"

paso "Caddy (HTTPS automático para $DOMINIO)"
sed -e "s#__DOMINIO__#$DOMINIO#g" -e "s#__WEB_ROOT__#$WEB_ROOT#g" \
  "$APP_DIR/deploy/Caddyfile.template" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
sudo systemctl reload caddy || sudo systemctl restart caddy

paso "Tareas programadas"
chmod +x "$APP_DIR/deploy/"*.sh
sudo tee /etc/cron.d/elmexicano >/dev/null <<EOF
# Salidas de los próximos días y estados según la hora (04:00, hora de Bolivia)
0 4 * * * $USUARIO cd $APP_DIR/backend && .venv/bin/python -m seeds.run_seeds >> /home/$USUARIO/seeds.log 2>&1
# Respaldo diario de la base (se conservan 7)
30 3 * * * $USUARIO $APP_DIR/deploy/backup.sh >> /home/$USUARIO/backup.log 2>&1
EOF

paso "Comprobación"
sleep 2
curl -fsS http://127.0.0.1:8000/health && echo
echo
echo "Instalación terminada: https://$DOMINIO  (panel: https://$DOMINIO/admin)"
echo "La primera visita puede tardar unos segundos mientras Caddy obtiene el certificado."
echo "IMPORTANTE: cambia la contraseña de las cuentas de demostración desde el panel (Personal)."
