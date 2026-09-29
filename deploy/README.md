# Despliegue en Oracle Cloud (Always Free)

Todo en una sola VPS gratuita: **portal + API + PostgreSQL**, con HTTPS automático.

```
Navegador ──HTTPS──> Caddy :443 ─┬─ /        → frontend compilado (/var/www/elmexicano)
                                 └─ /api/*   → FastAPI 127.0.0.1:8000 (systemd)
                                                  └─> PostgreSQL (solo localhost)
```

| Archivo | Para qué |
|---|---|
| `install.sh` | Instalación completa (se puede repetir sin romper nada) |
| `update.sh` | Publicar una versión nueva después de `git push` |
| `backup.sh` | Respaldo diario de la base (cron, conserva 7) |
| `Caddyfile.template` | Servidor web y certificado HTTPS |
| `elmexicano-api.service.template` | Servicio de la API |

## Costo

Nada, si solo usas recursos marcados *Always Free*: una VM Ampere A1 de hasta 4 OCPU y 24 GB de RAM, hasta 200 GB de disco y 10 TB de tráfico al mes. El subdominio de DuckDNS y el certificado de Let's Encrypt también son gratis. Crea una alerta de presupuesto de 1 USD para enterarte si algo se sale del plan gratuito.

## Paso 1 · Cuenta de Oracle Cloud

1. Regístrate en https://www.oracle.com/cloud/free/ (piden tarjeta solo para verificar).
2. **Home Region: Brazil East (São Paulo).** No se puede cambiar después y los recursos gratuitos solo existen ahí.
3. Recomendado: *Billing → Upgrade and Manage Payment → Pay As You Go*. Sigue siendo gratis dentro de los límites y evita que Oracle reclame la VM por poco uso.
4. *Billing → Budgets → Create Budget*: 1 USD, con alerta a tu correo.

## Paso 2 · Crear la VPS

*Compute → Instances → Create instance*

- **Image:** Canonical Ubuntu 24.04.
- **Shape:** *Ampere → VM.Standard.A1.Flex*, 2 OCPU / 12 GB (o 4 / 24).
- **Networking:** VCN nueva con subred pública y *Assign a public IPv4 address*.
- **SSH keys:** *Generate a key pair* y **descarga la clave privada**.
- **Boot volume:** 50 GB.

Si aparece *Out of capacity*, prueba otro *Availability Domain* o vuelve a intentarlo más tarde.

Anota la **IP pública** de la instancia.

## Paso 3 · Abrir los puertos 80 y 443 en Oracle

Instancia → *Subnet* → *Security Lists* → la lista por defecto → *Add Ingress Rules*:

| Source CIDR | Protocolo | Puerto destino |
|---|---|---|
| 0.0.0.0/0 | TCP | 80 |
| 0.0.0.0/0 | TCP | 443 |

(El firewall interno de Ubuntu lo abre `install.sh`.)

## Paso 4 · Subdominio gratis

En https://www.duckdns.org (entra con GitHub o Google) crea un subdominio, por ejemplo `elmexicano-demo`, pon la IP pública de la VPS en *current ip* y guarda.

## Paso 5 · Entrar a la VPS

Desde PowerShell, en la carpeta donde guardaste la clave:

```powershell
icacls .\ssh-key.key /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i .\ssh-key.key ubuntu@IP_PUBLICA
```

## Paso 6 · Descargar el código (repositorio privado)

En la VPS:

```bash
ssh-keygen -t ed25519 -C "vps-oracle" -N "" -f ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub
```

En GitHub: repositorio → *Settings → Deploy keys → Add deploy key*, pega la clave y deja **sin marcar** *Allow write access*. Luego:

```bash
ssh -o StrictHostKeyChecking=accept-new -T git@github.com   # responde "successfully authenticated"
git clone git@github.com:LuisRomero76/Mexicano-SRL-Demo.git ~/app
```

## Paso 7 · Instalar

```bash
DOMINIO=elmexicano-demo.duckdns.org DEMO_TELEFONO=591XXXXXXXX bash ~/app/deploy/install.sh
```

Tarda entre 5 y 10 minutos. Instala PostgreSQL, Node, Caddy, crea la base con una contraseña aleatoria, genera el `.env` de producción con un `JWT_SECRET` aleatorio, carga los datos, compila el frontend, deja la API como servicio, configura HTTPS y programa las salidas diarias y el respaldo.

**Al final de la salida aparece la API key del agente de voz** (`X-Bot-Key: emk_…`). Cópiala en ese momento: solo se muestra una vez. Si la pierdes, genera otra con:

```bash
cd ~/app/backend && .venv/bin/python -m seeds.api_key --rotar
```

La configuración de las herramientas en ElevenLabs está en `backend/README.md`, sección 7. La URL base es `https://TU_DOMINIO/api/bot`.

## Paso 8 · Comprobar y asegurar

1. Abre `https://elmexicano-demo.duckdns.org` y `…/admin`.
2. **Cambia las contraseñas de demostración.** `ElMexicano2026!` está en el repositorio: entra como `admin@elmexicanosrl.com` y, en *Personal*, cambia la de cada cuenta que vayas a usar y desactiva las demás.
3. En las herramientas del navegador, la cookie `em_session` debe verse como *Secure* y *HttpOnly*.

## Publicar cambios

Después de hacer `git push` desde tu computadora:

```bash
ssh -i .\ssh-key.key ubuntu@IP_PUBLICA
bash ~/app/deploy/update.sh
```

## Operación

| Qué | Comando |
|---|---|
| Estado de la API | `sudo systemctl status elmexicano-api` |
| Registros de la API | `journalctl -u elmexicano-api -f` |
| Registros de Caddy | `journalctl -u caddy -f` |
| Reiniciar la API | `sudo systemctl restart elmexicano-api` |
| Respaldos | `ls ~/backups` |
| Restaurar un respaldo | `gunzip -c ~/backups/elmexicano-1.sql.gz \| psql "$(grep ^DATABASE_URL= ~/app/backend/.env \| cut -d= -f2-)"` |
| Recargar datos de demostración desde cero | `cd ~/app/backend && .venv/bin/python -m seeds.run_seeds --reset` |

## Usar Neon en lugar de PostgreSQL local

Antes del Paso 7 crea `~/app/backend/.env` con las cadenas de Neon (`DATABASE_URL` *pooled* y `DATABASE_URL_DIRECT`), el resto de variables como en `install.sh` y `JOB_EXPIRAR_RESERVAS_SEGUNDOS=900`, para que la base pueda suspenderse y no se agoten las horas del plan gratuito. Crea el proyecto de Neon en **AWS São Paulo** para tener baja latencia. El script respetará ese `.env`, aunque igual instalará PostgreSQL local (sin usarlo).
