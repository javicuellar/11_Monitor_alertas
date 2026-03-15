# ── Stock Monitor – Dockerfile ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Stock Monitor"
LABEL description="Monitor de precios de acciones y ETFs con alertas por email y Telegram"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Entrypoint: run once immediately on start, then keep cron alive
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
