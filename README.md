# Stock Monitor

Monitor de precios de acciones y ETFs que comprueba periódicamente si el precio de cada activo ha variado más de un umbral configurable respecto al cierre del día anterior, y envía alertas por **email** y/o **Telegram**.

---

## Características

- Comparación de precio actual vs. **cierre del día anterior** (no apertura).
- Manejo automático de fines de semana y festivos: el lunes usa el cierre del viernes, tras un festivo el del último día hábil.
- **Scheduler interno** configurable desde base de datos: intervalo, ventana horaria y días de la semana.
- Notificaciones por **email** (SMTP) y **Telegram** (Bot API).
- Historial de alertas persistido en SQLite.
- Modo `--once` para integración con cron externo.

---

## Estructura del proyecto

```
stock_monitor/
├── __init__.py          # Re-exports públicos del paquete
├── config.py            # DB_PATH y configuración de logging
├── database.py          # Conexión SQLite, esquema y todas las queries
├── prices.py            # Obtención de precios via yfinance
├── notifications.py     # Constructores de mensajes y envío por email/Telegram
├── alerts.py            # Lógica de un ciclo de comprobación
├── scheduler.py         # Ventana horaria y bucle principal
└── main.py              # Punto de entrada (argparse)
```

### Responsabilidades por módulo

| Módulo | Responsabilidad |
|---|---|
| `config.py` | Define `DB_PATH` (sobreescribible via `$DB_PATH`) y el logger compartido |
| `database.py` | Única capa que toca SQLite: crea tablas, inserta defaults y expone funciones de lectura/escritura |
| `prices.py` | Llama a yfinance, calcula el % de cambio respecto al cierre anterior |
| `notifications.py` | Construye el HTML del email y el texto de Telegram; ejecuta el envío |
| `alerts.py` | Orquesta un ciclo completo: carga símbolos → obtiene precios → filtra → notifica → persiste |
| `scheduler.py` | Bucle infinito que respeta la ventana horaria y el intervalo configurados en BD |
| `main.py` | Entrada principal; inicializa la BD y despacha a `run_check` o `run_scheduler` |

---

## Requisitos

- Python 3.10+
- Dependencias:

```
yfinance
requests
```

Instalación:

```bash
pip install yfinance requests
```

---

## Instalación y uso

### 1. Clonar / copiar el paquete

Coloca la carpeta `stock_monitor/` en tu proyecto. El punto de entrada es `main.py` dentro del propio paquete.

### 2. Configurar la ruta de la base de datos

Por defecto la BD se crea en `/data/monitor.db`. Para cambiarla:

```bash
export DB_PATH=/ruta/a/tu/monitor.db
```

### 3. Arrancar el scheduler

```bash
python -m stock_monitor.main
```

En el primer arranque se crean automáticamente todas las tablas y se insertan los valores por defecto.

### 4. Un solo ciclo (modo cron)

```bash
python -m stock_monitor.main --once
```

Útil si prefieres delegar la periodicidad a `cron` o a cualquier gestor de tareas externo.

Ejemplo de crontab (cada 30 min, de lunes a viernes, entre las 9:00 y las 22:00):

```cron
*/30 9-22 * * 1-5 /usr/bin/python3 -m stock_monitor.main --once
```

---

## Configuración en base de datos

Toda la configuración se gestiona directamente con SQL sobre el fichero SQLite.

### Scheduler (`scheduler_config`)

```sql
UPDATE scheduler_config SET
    interval_minutes = 15,   -- comprobar cada 15 minutos
    start_time       = '09:00',
    end_time         = '20:00',
    weekdays_only    = 1;    -- 1 = solo lunes-viernes, 0 = todos los días
```

El scheduler relee esta tabla en cada iteración, por lo que los cambios surten efecto **sin reiniciar** el proceso.

### Email (`email_config`)

```sql
UPDATE email_config SET
    smtp_host = 'smtp.gmail.com',
    smtp_port = 587,
    username  = 'tu@gmail.com',
    password  = 'tu_app_password',  -- usa una App Password de Google
    from_addr = 'tu@gmail.com',
    to_addr   = 'destino@email.com',
    enabled   = 1;
```

> Para Gmail es necesario usar una **App Password** (no la contraseña de la cuenta). Se genera en: Cuenta de Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones.

### Telegram (`telegram_config`)

```sql
UPDATE telegram_config SET
    bot_token = '123456789:ABCdef...',
    chat_id   = '-100123456789',   -- puede ser un chat personal o un grupo
    enabled   = 1;
```

Para obtener el `bot_token` crea un bot con [@BotFather](https://t.me/BotFather). Para obtener el `chat_id` puedes usar `@userinfobot` o la API `getUpdates`.

### Símbolos monitorizados (`symbols`)

```sql
-- Añadir un símbolo
INSERT INTO symbols (ticker, name, threshold) VALUES ('SPYD.DE', 'SPDR Dividend Aristocrats', 1.5);

-- Cambiar el umbral de alerta de un símbolo existente
UPDATE symbols SET threshold = 3.0 WHERE ticker = 'NVDA';

-- Desactivar un símbolo (sin borrarlo)
UPDATE symbols SET active = 0 WHERE ticker = 'QQQ';

-- Ver todos los símbolos
SELECT * FROM symbols;
```

El campo `threshold` es el **porcentaje mínimo de variación** (positivo o negativo) que dispara una alerta. Por defecto es `2.0` (±2 %).

---

## Lógica de alertas

1. Se obtiene el **cierre del último día hábil anterior** a hoy usando 7 días de histórico de yfinance, filtrando fechas estrictamente anteriores al día actual.
2. Se obtiene el **precio actual** via `fast_info` (cotización en tiempo real o diferida); si no está disponible, se usa la última barra del histórico intradía de 1 minuto.
3. Se calcula `cambio_pct = (actual - cierre_anterior) / cierre_anterior * 100`.
4. Si `|cambio_pct| >= threshold` **y** no se ha enviado ya una alerta para ese ticker hoy, se registra y notifica.

---

## Historial de alertas (`alert_history`)

Cada alerta disparada se guarda con el siguiente esquema:

| Campo | Descripción |
|---|---|
| `ticker` | Símbolo del activo |
| `alert_date` | Fecha de la alerta (ISO-8601) |
| `prev_close` | Precio de cierre del día anterior |
| `current_price` | Precio en el momento de la alerta |
| `change_pct` | Variación en porcentaje |
| `direction` | `▲ SUBE` o `▼ BAJA` |
| `notified_email` | `1` si el email se envió con éxito |
| `notified_tg` | `1` si el mensaje de Telegram se envió con éxito |
| `created_at` | Timestamp de inserción |

Consulta de ejemplo:

```sql
SELECT ticker, alert_date, prev_close, current_price, change_pct, direction
FROM alert_history
ORDER BY created_at DESC
LIMIT 20;
```

---

## Variables de entorno

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DB_PATH` | `/data/monitor.db` | Ruta completa al fichero SQLite |

---

## Extensión y personalización

- **Añadir un canal de notificación** (p.ej. Slack): implementa las funciones `build_slack_msg` y `send_slack` en `notifications.py` y llama a ambas desde `alerts.py`.
- **Cambiar la fuente de precios**: toda la lógica de yfinance está encapsulada en `prices.py`; sustitúyela sin tocar el resto.
- **Múltiples destinatarios de email**: amplía la tabla `email_config` con un campo `to_addr_cc` o crea varias filas con `enabled=1`.
