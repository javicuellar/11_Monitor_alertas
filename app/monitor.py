#!/usr/bin/env python3
"""
Stock & ETF Price Monitor
Checks price changes and sends alerts via Email and Telegram.

Scheduling is controlled entirely from the `scheduler_config` table in SQLite:
  - interval_minutes : how often to run the check (default 30)
  - start_time       : market open time, checks won't run before this (HH:MM, default 09:00)
  - end_time         : market close time, checks won't run after this (HH:MM, default 22:00)
  - weekdays_only    : if 1, skips Saturday and Sunday (default 1)

Price change is calculated vs. the previous trading-day close (not today's open).
On Monday (or after a holiday), the reference price is Friday's (or last trading day's) close.
"""

import sqlite3
import smtplib
import time
import requests
import yfinance as yf
import logging
import sys
import os
from datetime import datetime, date, timedelta
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

        -- Scheduler configuration
        -- interval_minutes : minutes between each price check
        -- start_time       : earliest time to run a check (HH:MM, 24h)
        -- end_time         : latest time to run a check (HH:MM, 24h)
        -- weekdays_only    : 1 = skip Saturday & Sunday, 0 = run every day
        CREATE TABLE IF NOT EXISTS scheduler_config (
            id                INTEGER PRIMARY KEY,
            interval_minutes  INTEGER NOT NULL DEFAULT 30,
            start_time        TEXT    NOT NULL DEFAULT '09:00',
            end_time          TEXT    NOT NULL DEFAULT '22:00',
            weekdays_only     INTEGER NOT NULL DEFAULT 1
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
            prev_close      REAL,
            current_price   REAL,
            change_pct      REAL,
            direction       TEXT,
            notified_email  INTEGER DEFAULT 0,
            notified_tg     INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        """)

        # ── Default scheduler config ──────────────────────────────────────────
        if not conn.execute("SELECT 1 FROM scheduler_config LIMIT 1").fetchone():
            conn.execute("""
                INSERT INTO scheduler_config
                    (interval_minutes, start_time, end_time, weekdays_only)
                VALUES (30, '09:00', '22:00', 1)
            """)

        # ── Default email config ──────────────────────────────────────────────
        if not conn.execute("SELECT 1 FROM email_config LIMIT 1").fetchone():
            conn.execute("""
                INSERT INTO email_config
                    (smtp_host, smtp_port, username, password, from_addr, to_addr, enabled)
                VALUES
                    ('smtp.gmail.com', 587, 'your@gmail.com', 'your_app_password',
                     'your@gmail.com', 'recipient@email.com', 0)
            """)

        # ── Default telegram config ───────────────────────────────────────────
        if not conn.execute("SELECT 1 FROM telegram_config LIMIT 1").fetchone():
            conn.execute("""
                INSERT INTO telegram_config (bot_token, chat_id, enabled)
                VALUES ('YOUR_BOT_TOKEN', 'YOUR_CHAT_ID', 0)
            """)

        # ── Default symbols ───────────────────────────────────────────────────
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


def get_scheduler_config() -> dict:
    """Read scheduler settings from DB, returning safe defaults if missing."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scheduler_config LIMIT 1").fetchone()
    if row:
        return {
            "interval_minutes": int(row["interval_minutes"]),
            "start_time":       row["start_time"],
            "end_time":         row["end_time"],
            "weekdays_only":    bool(row["weekdays_only"]),
        }
    return {
        "interval_minutes": 30,
        "start_time":       "09:00",
        "end_time":         "22:00",
        "weekdays_only":    True,
    }


# ── Price fetching ────────────────────────────────────────────────────────────
def _last_trading_close(ticker: str) -> Optional[float]:
    """
    Return the most recent *completed* trading-day close price.
    Fetches 7 calendar days of history to safely skip weekends/holidays,
    then takes the second-to-last row (yesterday or last trading day).
    If the market is currently open the last row is today's partial session,
    so [-2] is the previous full close.  If the market is closed (after hours
    or pre-market) yfinance still returns only completed days, so [-1] would
    be the last full close — but we always want the day *before* today,
    so we filter explicitly by date.
    """
    try:
        tk = yf.Ticker(ticker)
        # Fetch enough history to always have at least one full trading day
        # before today, even across long weekends or holidays.
        hist = tk.history(period="7d", interval="1d")
        if hist.empty:
            log.warning("No historical data for %s", ticker)
            return None

        today_str = date.today().isoformat()
        # Keep only rows whose date is strictly before today
        hist.index = hist.index.normalize()          # strip time component
        prev_rows = hist[hist.index.strftime("%Y-%m-%d") < today_str]

        if prev_rows.empty:
            log.warning("No previous trading day data for %s", ticker)
            return None

        prev_close = float(prev_rows.iloc[-1]["Close"])
        return prev_close
    except Exception as exc:
        log.error("Error fetching prev close for %s: %s", ticker, exc)
        return None


def _current_price(ticker: str) -> Optional[float]:
    """Return the most recent price (intraday or last close)."""
    try:
        tk = yf.Ticker(ticker)
        # fast_info gives real-time or delayed last price without a full download
        price = tk.fast_info.get("lastPrice") or tk.fast_info.get("last_price")
        if price:
            return float(price)
        # Fallback: last row of today's 1-min bar history
        hist = tk.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist.iloc[-1]["Close"])
        return None
    except Exception as exc:
        log.error("Error fetching current price for %s: %s", ticker, exc)
        return None


def get_price_change(ticker: str) -> Optional[dict]:
    """
    Return prev_close, current price and % change vs. previous trading-day close.
    Weekends/holidays are handled automatically: the previous trading day's close
    is always used as the reference, regardless of how many calendar days ago it was.
    """
    prev_close = _last_trading_close(ticker)
    if prev_close is None:
        return None

    current = _current_price(ticker)
    if current is None:
        return None

    change_pct = ((current - prev_close) / prev_close) * 100
    return {
        "ticker":     ticker,
        "prev_close": prev_close,
        "current":    current,
        "change_pct": round(change_pct, 2),
        "direction":  "▲ SUBE" if change_pct > 0 else "▼ BAJA",
        "date":       date.today().isoformat(),
    }


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
        msg["From"]    = cfg["from_addr"]
        msg["To"]      = cfg["to_addr"]
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
            "chat_id":    cfg["chat_id"],
            "text":       message,
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
               (ticker, alert_date, prev_close, current_price, change_pct,
                direction, notified_email, notified_tg)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                data["ticker"],     data["date"],
                data["prev_close"], data["current"],
                data["change_pct"], data["direction"],
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
          <td style="padding:8px;border:1px solid #ddd">{a['prev_close']:.2f}</td>
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
          <th style="padding:8px">Cierre anterior</th>
          <th style="padding:8px">Precio actual</th>
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
            f"(Cierre ant.: {a['prev_close']:.2f} → Actual: {a['current']:.2f})"
        )
    return "\n".join(lines)


# ── Single check cycle ────────────────────────────────────────────────────────
def run_check():
    """Fetch prices and fire alerts for all active symbols."""
    log.info("=== Iniciando ciclo de comprobación ===")

    with get_conn() as conn:
        symbols = conn.execute(
            "SELECT ticker, name, threshold FROM symbols WHERE active=1"
        ).fetchall()

    if not symbols:
        log.warning("No hay símbolos activos en la base de datos.")
        return

    alerts_to_send = []

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

    email_html = build_email_html(alerts_to_send)
    tg_msg     = build_telegram_msg(alerts_to_send)

    subject    = (
        f"⚠️ Alerta precios {date.today().strftime('%d/%m/%Y')} "
        f"– {len(alerts_to_send)} activo(s)"
    )
    ok_email = send_email(subject, email_html)
    ok_tg    = send_telegram(tg_msg)

    for a in alerts_to_send:
        save_alert(a, ok_email, ok_tg)

    log.info("Ciclo finalizado. Alertas enviadas: %d", len(alerts_to_send))


# ── Scheduler helpers ─────────────────────────────────────────────────────────
def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute)."""
    h, m = hhmm.strip().split(":")
    return int(h), int(m)


def _is_active_window(cfg: dict) -> bool:
    """Return True if right now is within the configured check window."""
    now = datetime.now()

    if cfg["weekdays_only"] and now.weekday() >= 5:   # 5=Sat, 6=Sun
        return False

    start_h, start_m = _parse_hhmm(cfg["start_time"])
    end_h,   end_m   = _parse_hhmm(cfg["end_time"])

    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_dt   = now.replace(hour=end_h,   minute=end_m,   second=0, microsecond=0)

    return start_dt <= now <= end_dt


# ── Main / scheduler loop ─────────────────────────────────────────────────────
def run():
    init_db()
    log.info("=== Stock Monitor arrancado – modo scheduler ===")

    while True:
        # Re-read config on every iteration so changes take effect immediately
        cfg = get_scheduler_config()
        interval_seconds = cfg["interval_minutes"] * 60

        if _is_active_window(cfg):
            try:
                run_check()
            except Exception as exc:
                log.error("Error inesperado en run_check: %s", exc)
        else:
            now = datetime.now()
            log.info(
                "Fuera de ventana horaria (%s–%s, solo_laborables=%s). "
                "Próxima comprobación en %d min.",
                cfg["start_time"], cfg["end_time"],
                cfg["weekdays_only"], cfg["interval_minutes"],
            )

        log.info("Durmiendo %d minutos hasta el próximo ciclo…", cfg["interval_minutes"])
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run()
