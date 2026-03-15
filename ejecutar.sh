#!/bin/bash
# entrypoint.sh – Initialise DB, run once, then start cron daemon

set -e

echo "=== Stock Monitor starting at $(date) ==="

# Inicializar BD y ejecutar el monitor
python /app/monitor.py
