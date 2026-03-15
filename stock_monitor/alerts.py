"""
alerts.py
─────────
Orchestrates a single price-check cycle:
  1. Load active symbols from the DB.
  2. Fetch price change for each one.
  3. For any that exceed the threshold (and haven't been alerted today),
     build and dispatch notifications, then persist the alert.
"""

from datetime import date

from config import get_logger
from database import already_alerted, get_active_symbols, save_alert
from notifications import (build_email_html, build_telegram_msg, send_email, send_telegram )
from prices import get_price_change



log = get_logger(__name__)


def run_check() -> None:
    """Execute one full price-check and alert cycle."""
    log.info("=== Iniciando ciclo de comprobación ===")

    symbols = get_active_symbols()
    if not symbols:
        log.warning("No hay símbolos activos en la base de datos.")
        return

    alerts_to_send: list[dict] = []

    for sym in symbols:
        ticker    = sym["ticker"]
        threshold = sym["threshold"]
        log.info("Comprobando %s (umbral: ±%.1f%%)", ticker, threshold)

        data = get_price_change(ticker)
        if data is None:
            continue

        log.info("  %s → cambio vs. cierre anterior: %+.2f%%", ticker, data["change_pct"])

        if abs(data["change_pct"]) >= threshold:
            if already_alerted(ticker, data["date"]):
                log.info("  Ya se envió alerta hoy para %s, omitiendo.", ticker)
                continue
            log.info("  ⚡ ¡ALERTA! Supera el umbral de ±%.1f%%", threshold)
            alerts_to_send.append(data)

    if not alerts_to_send:
        log.info("Sin alertas que enviar en este ciclo.")
        return

    # Build and dispatch notifications
    subject   = (
        f"⚠️ Alerta precios {date.today().strftime('%d/%m/%Y')} "
        f"– {len(alerts_to_send)} activo(s)"
    )
    ok_email = send_email(subject, build_email_html(alerts_to_send))
    ok_tg    = send_telegram(build_telegram_msg(alerts_to_send))

    # Persist results
    for a in alerts_to_send:
        save_alert(a, ok_email, ok_tg)

    log.info("Ciclo finalizado. Alertas enviadas: %d", len(alerts_to_send))
