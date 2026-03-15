"""
database.py
───────────
SQLite connection, schema initialisation, and all data-access functions.

All other modules import from here — none of them touch sqlite3 directly.
"""

import sqlite3
from typing import Optional

from config import DB_PATH, get_logger



log = get_logger(__name__)

# ── Connection ────────────────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
-- Email configuration
CREATE TABLE IF NOT EXISTS email_config (
    id          INTEGER PRIMARY KEY,
    smtp_host   TEXT    NOT NULL,
    smtp_port   INTEGER NOT NULL DEFAULT 587,
    username    TEXT    NOT NULL,
    password    TEXT    NOT NULL,
    from_addr   TEXT    NOT NULL,
    to_addr     TEXT    NOT NULL,
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
--   interval_minutes : minutes between each price check
--   start_time       : earliest time to run a check (HH:MM, 24 h)
--   end_time         : latest  time to run a check (HH:MM, 24 h)
--   weekdays_only    : 1 = skip Saturday & Sunday, 0 = run every day
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
    ticker      TEXT    NOT NULL UNIQUE,
    name        TEXT,
    threshold   REAL    NOT NULL DEFAULT 2.0,
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
"""

_DEFAULT_SYMBOLS = [
    ("SPY",  "SPDR S&P 500 ETF",  2.0),
    ("QQQ",  "Invesco QQQ ETF",   2.0),
    ("AAPL", "Apple Inc.",        2.0),
    ("MSFT", "Microsoft Corp.",   2.0),
    ("NVDA", "NVIDIA Corp.",      2.0),
]



def init_db() -> None:
    """Create tables (if absent) and populate default seed rows."""
    with get_conn() as conn:
        conn.executescript(_SCHEMA)

        if not conn.execute("SELECT 1 FROM scheduler_config LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO scheduler_config "
                "(interval_minutes, start_time, end_time, weekdays_only) "
                "VALUES (30, '09:00', '22:00', 1)"
            )

        if not conn.execute("SELECT 1 FROM email_config LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO email_config "
                "(smtp_host, smtp_port, username, password, from_addr, to_addr, enabled) "
                "VALUES ('smtp.gmail.com', 587, 'your@gmail.com', 'your_app_password', "
                "        'your@gmail.com', 'recipient@email.com', 0)"
            )

        if not conn.execute("SELECT 1 FROM telegram_config LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO telegram_config (bot_token, chat_id, enabled) "
                "VALUES ('YOUR_BOT_TOKEN', 'YOUR_CHAT_ID', 0)"
            )

        for ticker, name, threshold in _DEFAULT_SYMBOLS:
            conn.execute(
                "INSERT OR IGNORE INTO symbols (ticker, name, threshold) VALUES (?,?,?)",
                (ticker, name, threshold),
            )

    log.info("Database initialised at %s", DB_PATH)




# ── Scheduler config ──────────────────────────────────────────────────────────

def get_scheduler_config() -> dict:
    """Return scheduler settings from DB (safe defaults if missing)."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM scheduler_config LIMIT 1").fetchone()
    if row:
        return {
            "interval_minutes": int(row["interval_minutes"]),
            "start_time":       row["start_time"],
            "end_time":         row["end_time"],
            "weekdays_only":    bool(row["weekdays_only"]),
        }
    return {"interval_minutes": 30, "start_time": "09:00",
            "end_time": "22:00", "weekdays_only": True}




# ── Notification configs ──────────────────────────────────────────────────────

def get_email_config() -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM email_config WHERE enabled=1 LIMIT 1"
        ).fetchone()


def get_telegram_config() -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM telegram_config WHERE enabled=1 LIMIT 1"
        ).fetchone()




# ── Symbols ───────────────────────────────────────────────────────────────────

def get_active_symbols() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT ticker, name, threshold FROM symbols WHERE active=1"
        ).fetchall()




# ── Alert history ─────────────────────────────────────────────────────────────

def already_alerted(ticker: str, alert_date: str) -> bool:
    """Return True if an alert was already recorded for this ticker today."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM alert_history WHERE ticker=? AND alert_date=?",
            (ticker, alert_date),
        ).fetchone()
    return row is not None



def save_alert(data: dict, notified_email: bool, notified_tg: bool) -> None:
    """Persist a triggered alert to the history table."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alert_history "
            "(ticker, alert_date, prev_close, current_price, change_pct, "
            " direction, notified_email, notified_tg) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                data["ticker"],      data["date"],
                data["prev_close"],  data["current"],
                data["change_pct"],  data["direction"],
                int(notified_email), int(notified_tg),
            ),
        )
