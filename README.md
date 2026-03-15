# 📈 Stock & ETF Price Monitor

Monitoriza acciones y ETFs y envía alertas por **Email** y **Telegram** cuando el precio sube o baja más de un umbral configurable (por defecto ±2%) en el día.

La configuración se almacena completamente en **SQLite** y se gestiona con un CLI incluido.

---

## 🚀 Inicio rápido con Docker

### 1. Construir y arrancar

```bash
docker compose up -d
```

El contenedor:
- Inicializa la base de datos SQLite en el volumen `/data`
- Ejecuta una comprobación inmediata al arrancar
- Repite cada 30 minutos de lunes a viernes entre 09:00 y 18:00 (hora del contenedor)

### 2. Configurar Email

Para Gmail necesitas una **App Password** (no tu contraseña normal):
<https://myaccount.google.com/apppasswords>

```bash
docker compose exec monitor python manage.py set-email \
  --host smtp.gmail.com \
  --port 587 \
  --user tu@gmail.com \
  --pass TU_APP_PASSWORD \
  --from tu@gmail.com \
  --to destinatario@email.com
```

### 3. Configurar Telegram

Crea un bot con [@BotFather](https://t.me/BotFather) y obtén tu `chat_id` con `@userinfobot`.

```bash
docker compose exec monitor python manage.py set-telegram \
  --token 123456:ABC-TU_TOKEN \
  --chat -100TU_CHAT_ID
```

### 4. Activar notificaciones

```bash
docker compose exec monitor python manage.py enable-email
docker compose exec monitor python manage.py enable-telegram
```

### 5. Probar que funciona

```bash
docker compose exec monitor python manage.py test-email
docker compose exec monitor python manage.py test-telegram
```

---

## 🔧 Gestión de símbolos

```bash
# Ver símbolos activos
docker compose exec monitor python manage.py list-symbols

# Añadir símbolo con umbral personalizado (ej. ±3%)
docker compose exec monitor python manage.py add-symbol \
  --ticker TSLA --name "Tesla Inc." --threshold 3.0

# Desactivar símbolo
docker compose exec monitor python manage.py del-symbol --ticker TSLA
```

**Símbolos por defecto:** SPY, QQQ, AAPL, MSFT, NVDA

---

## 📋 Historial de alertas

```bash
# Últimos 7 días (por defecto)
docker compose exec monitor python manage.py list-alerts

# Últimos 30 días
docker compose exec monitor python manage.py list-alerts --days 30
```

---

## ⚙️ Configuración avanzada

### Cambiar frecuencia del cron

Edita el `Dockerfile` (línea con `echo "*/30 9-18 ..."`):

```
# Cada hora de 8 a 20, L-V
0 8-20 * * 1-5 python /app/monitor.py >> /var/log/monitor.log 2>&1
```

Luego reconstruye: `docker compose up -d --build`

### Timezone

Cambia la variable `TZ` en `docker-compose.yml`:
```yaml
TZ: America/New_York   # mercados USA
TZ: Europe/London      # LSE
```

---

## 📂 Estructura del proyecto

```
stock-monitor/
├── app/
│   ├── monitor.py        # lógica principal
│   ├── manage.py         # CLI de administración
│   └── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── README.md
```

---

## 🗄️ Esquema de la base de datos

| Tabla             | Descripción                              |
|-------------------|------------------------------------------|
| `email_config`    | Configuración SMTP                       |
| `telegram_config` | Token de bot y chat_id                   |
| `symbols`         | Tickers monitorizados con umbral         |
| `alert_history`   | Registro de todas las alertas enviadas   |

---

## 🐛 Ver logs

```bash
docker compose logs -f
# o directamente:
docker compose exec monitor tail -f /var/log/monitor.log
```
