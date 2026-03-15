#!/usr/bin/env python3
"""
Stock & ETF Price Monitor
Checks price changes and sends alerts via Email and Telegram
"""

import sqlite3
import smtplib
import requests
import yfinance as yf
import logging
import sys
import os
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "/data/monitor.db")


# ── Database ──────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist and insert default config."""
    with get_conn() as conn:
        conn.executescript("""
        -- Email configuration
        CREATE TABLE IF NOT EXISTS email_config (
            id          INTEGER PRIMARY KEY,
            smtp_host   TEXT NOT NULL,
            smtp_port   INTEGER NOT NULL DEFAULT 587,
            username    TEXT NOT NULL,
            password    TEXT NOT NULL,
            from_addr   TEXT NOT NULL,
            to_addr     TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1
        );

        -- Telegram configuration
        CREATE TABLE IF NOT EXISTS telegram_config (
            id          INTEGER PRIMARY KEY,
            bot_token   TEXT NOT NULL,
            chat_id     TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1
        );

        -- Symbols to monitor
        CREATE TABLE IF NOT EXISTS symbols (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT NOT NULL UNIQUE,
            name        TEXT,
            threshold   REAL NOT NULL DEFAULT 2.0,
            active      INTEGER NOT NULL DEFAULT 1
        );

        -- Alert history
        CREATE TABLE IF NOT EXISTS alert_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker          TEXT NOT NULL,
            alert_date      TEXT NOT NULL,
            open_price      REAL,
            current_price   REAL,
            change_pct      REAL,
            direction       TEXT,
            notified_email  INTEGER DEFAULT 0,
            notified_tg     INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        """)

        # Insert placeholder config rows if none exist
        if not conn.execute("SELECT 1 FROM email_config LIMIT 1").fetchone():
            conn.execute("""
                INSERT INTO email_config
                    (smtp_host, smtp_port, username, password, from_addr, to_addr, enabled)
                VALUES
                    ('smtp.gmail.com', 587, 'your@gmail.com', 'your_app_password',
                     'your@gmail.com', 'recipient@email.com', 0)
            """)

        if not conn.execute("SELECT 1 FROM telegram_config LIMIT 1").fetchone():
            conn.execute("""
                INSERT INTO telegram_config (bot_token, chat_id, enabled)
                VALUES ('YOUR_BOT_TOKEN', 'YOUR_CHAT_ID', 0)
            """)

        # Default symbols
        default_symbols = [
            ("SPY",  "SPDR S&P 500 ETF",      2.0),
            ("QQQ",  "Invesco QQQ ETF",        2.0),
            ("AAPL", "Apple Inc.",             2.0),
            ("MSFT", "Microsoft Corp.",        2.0),
            ("NVDA", "NVIDIA Corp.",           2.0),
        ]
        for ticker, name, threshold in default_symbols:
            conn.execute(
                "INSERT OR IGNORE INTO symbols (ticker, name, threshold) VALUES (?,?,?)",
                (ticker, name, threshold),
            )

    log.info("Database initialised at %s", DB_PATH)


# ── Price fetching ────────────────────────────────────────────────────────────
def get_price_change(ticker: str) -> Optional[dict]:
    """Return open, current price and % change for today."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="2d", interval="1d")
        if hist.empty or len(hist) < 1:
            log.warning("No data for %s", ticker)
            return None

        # Today's open
        today_row = hist.iloc[-1]
        open_price = float(today_row["Open"])
        current_price = float(today_row["Close"])

        change_pct = ((current_price - open_price) / open_price) * 100
        return {
            "ticker": ticker,
            "open": open_price,
            "current": current_price,
            "change_pct": round(change_pct, 2),
            "direction": "▲ SUBE" if change_pct > 0 else "▼ BAJA",
            "date": date.today().isoformat(),
        }
    except Exception as exc:
        log.error("Error fetching %s: %s", ticker, exc)
        return None


# ── Notifications ─────────────────────────────────────────────────────────────
def send_email(subject: str, body: str) -> bool:
    with get_conn() as conn:
        cfg = conn.execute(
            "SELECT * FROM email_config WHERE enabled=1 LIMIT 1"
        ).fetchone()
    if not cfg:
        log.info("Email notifications disabled or not configured.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["from_addr"]
        msg["To"] = cfg["to_addr"]
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["from_addr"], cfg["to_addr"], msg.as_string())
        log.info("Email sent to %s", cfg["to_addr"])
        return True
    except Exception as exc:
        log.error("Email error: %s", exc)
        return False


def send_telegram(message: str) -> bool:
    with get_conn() as conn:
        cfg = conn.execute(
            "SELECT * FROM telegram_config WHERE enabled=1 LIMIT 1"
        ).fetchone()
    if not cfg:
        log.info("Telegram notifications disabled or not configured.")
        return False

    try:
        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        payload = {
            "chat_id": cfg["chat_id"],
            "text": message,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            log.info("Telegram message sent to chat %s", cfg["chat_id"])
            return True
        log.error("Telegram API error: %s", resp.text)
        return False
    except Exception as exc:
        log.error("Telegram error: %s", exc)
        return False


# ── Alert logic ───────────────────────────────────────────────────────────────
def already_alerted(ticker: str, alert_date: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM alert_history WHERE ticker=? AND alert_date=?",
            (ticker, alert_date),
        ).fetchone()
    return row is not None


def save_alert(data: dict, notified_email: bool, notified_tg: bool):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO alert_history
               (ticker, alert_date, open_price, current_price, change_pct,
                direction, notified_email, notified_tg)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                data["ticker"], data["date"],
                data["open"], data["current"], data["change_pct"],
                data["direction"],
                int(notified_email), int(notified_tg),
            ),
        )


def build_email_html(alerts: list[dict]) -> str:
    rows = ""
    for a in alerts:
        color = "#c0392b" if a["change_pct"] < 0 else "#27ae60"
        rows += f"""
        <tr>
          <td style="padding:8px;border:1px solid #ddd"><b>{a['ticker']}</b></td>
          <td style="padding:8px;border:1px solid #ddd">{a['open']:.2f}</td>
          <td style="padding:8px;border:1px solid #ddd">{a['current']:.2f}</td>
          <td style="padding:8px;border:1px solid #ddd;color:{color}">
            {a['direction']} {abs(a['change_pct']):.2f}%
          </td>
        </tr>"""

    return f"""
    <html><body>
    <h2 style="font-family:Arial">📈 Alerta de Precio – {date.today().strftime('%d/%m/%Y')}</h2>
    <table style="border-collapse:collapse;font-family:Arial;font-size:14px">
      <thead>
        <tr style="background:#2c3e50;color:white">
          <th style="padding:8px">Ticker</th>
          <th style="padding:8px">Apertura</th>
          <th style="padding:8px">Actual</th>
          <th style="padding:8px">Cambio</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    <p style="font-family:Arial;color:#7f8c8d;font-size:12px">
      Generado automáticamente por Stock Monitor
    </p>
    </body></html>"""


def build_telegram_msg(alerts: list[dict]) -> str:
    lines = [f"📊 <b>Alertas de Precio</b> – {date.today().strftime('%d/%m/%Y')}\n"]
    for a in alerts:
        emoji = "🔴" if a["change_pct"] < 0 else "🟢"
        lines.append(
            f"{emoji} <b>{a['ticker']}</b>: {a['direction']} "
            f"<b>{abs(a['change_pct']):.2f}%</b>  "
            f"(Apertura: {a['open']:.2f} → Actual: {a['current']:.2f})"
        )
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    init_db()
    log.info("=== Stock Monitor iniciado ===")

    with get_conn() as conn:
        symbols = conn.execute(
            "SELECT ticker, name, threshold FROM symbols WHERE active=1"
        ).fetchall()

    if not symbols:
        log.warning("No hay símbolos activos en la base de datos.")
        return

    alerts_to_send = []

    for sym in symbols:
        ticker = sym["ticker"]
        threshold = sym["threshold"]
        log.info("Comprobando %s (umbral: ±%.1f%%)", ticker, threshold)

        data = get_price_change(ticker)
        if data is None:
            continue

        log.info(
            "  %s → cambio del día: %+.2f%%", ticker, data["change_pct"]
        )

        if abs(data["change_pct"]) >= threshold:
            if already_alerted(ticker, data["date"]):
                log.info("  Ya se envió alerta hoy para %s, omitiendo.", ticker)
                continue
            log.info("  ⚡ ¡ALERTA! Supera el umbral de ±%.1f%%", threshold)
            alerts_to_send.append(data)

    if not alerts_to_send:
        log.info("Sin alertas que enviar.")
        return

    # Build messages
    email_html = build_email_html(alerts_to_send)
    tg_msg = build_telegram_msg(alerts_to_send)

    subject = f"⚠️ Alerta precios {date.today().strftime('%d/%m/%Y')} – {len(alerts_to_send)} activo(s)"
    ok_email = send_email(subject, email_html)
    ok_tg = send_telegram(tg_msg)

    for a in alerts_to_send:
        save_alert(a, ok_email, ok_tg)

    log.info("Proceso finalizado. Alertas enviadas: %d", len(alerts_to_send))


if __name__ == "__main__":
    run()
