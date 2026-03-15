# ── Stock Monitor – Dockerfile ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Stock Monitor"
LABEL description="Monitors stocks and ETFs and sends alerts via Email and Telegram"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Timezone (override with TZ env var)
ENV TZ=Europe/Madrid
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Python deps
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ .

# Data volume
VOLUME ["/data"]
ENV DB_PATH=/data/monitor.db

# Cron schedule: every 30 min between 09:00-18:00, Mon-Fri
# Adjust to your market timezone
RUN echo "*/30 9-18 * * 1-5 python /app/monitor.py >> /var/log/monitor.log 2>&1" \
    > /etc/cron.d/stock-monitor \
    && chmod 0644 /etc/cron.d/stock-monitor \
    && crontab /etc/cron.d/stock-monitor

# Entrypoint: run once immediately on start, then keep cron alive
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
