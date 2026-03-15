#!/usr/bin/env python3
"""
manage.py – CLI para administrar la configuración del Stock Monitor
Uso:
  python manage.py show-config
  python manage.py set-email  --host smtp.gmail.com --port 587 \
                              --user you@gmail.com --pass app_pass \
                              --from you@gmail.com --to dest@email.com
  python manage.py set-telegram --token BOT_TOKEN --chat CHAT_ID
  python manage.py add-symbol  --ticker TSLA --name "Tesla" --threshold 3.0
  python manage.py del-symbol  --ticker TSLA
  python manage.py list-symbols
  python manage.py list-alerts [--days 7]
  python manage.py enable-email  / disable-email
  python manage.py enable-telegram / disable-telegram
  python manage.py test-email
  python manage.py test-telegram
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DB_PATH", "/data/monitor.db")


def get_conn():
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada en {DB_PATH}")
        print("   Ejecuta primero: python monitor.py")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Commands ──────────────────────────────────────────────────────────────────
def show_config(args):
    with get_conn() as conn:
        print("\n📧 Email Config")
        print("-" * 50)
        row = conn.execute("SELECT * FROM email_config LIMIT 1").fetchone()
        if row:
            for k in row.keys():
                val = row[k] if k != "password" else "***"
                print(f"  {k:<15}: {val}")
        else:
            print("  (no configurado)")

        print("\n💬 Telegram Config")
        print("-" * 50)
        row = conn.execute("SELECT * FROM telegram_config LIMIT 1").fetchone()
        if row:
            for k in row.keys():
                val = row[k] if k != "bot_token" else row[k][:8] + "..."
                print(f"  {k:<15}: {val}")
        else:
            print("  (no configurado)")
    print()


def set_email(args):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM email_config LIMIT 1").fetchone()
        if existing:
            conn.execute("""
                UPDATE email_config SET
                    smtp_host=?, smtp_port=?, username=?, password=?,
                    from_addr=?, to_addr=?, enabled=1
                WHERE id=?
            """, (args.host, args.port, args.user, getattr(args, 'pass'),
                  args.frm, args.to, existing["id"]))
        else:
            conn.execute("""
                INSERT INTO email_config
                    (smtp_host, smtp_port, username, password, from_addr, to_addr, enabled)
                VALUES (?,?,?,?,?,?,1)
            """, (args.host, args.port, args.user, getattr(args, 'pass'),
                  args.frm, args.to))
    print("✅ Email configurado correctamente.")


def set_telegram(args):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM telegram_config LIMIT 1").fetchone()
        if existing:
            conn.execute(
                "UPDATE telegram_config SET bot_token=?, chat_id=?, enabled=1 WHERE id=?",
                (args.token, args.chat, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO telegram_config (bot_token, chat_id, enabled) VALUES (?,?,1)",
                (args.token, args.chat),
            )
    print("✅ Telegram configurado correctamente.")


def toggle_email(args, enabled: int):
    with get_conn() as conn:
        conn.execute("UPDATE email_config SET enabled=?", (enabled,))
    state = "activado" if enabled else "desactivado"
    print(f"✅ Email {state}.")


def toggle_telegram(args, enabled: int):
    with get_conn() as conn:
        conn.execute("UPDATE telegram_config SET enabled=?", (enabled,))
    state = "activado" if enabled else "desactivado"
    print(f"✅ Telegram {state}.")


def add_symbol(args):
    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO symbols (ticker, name, threshold) VALUES (?,?,?)",
                (args.ticker.upper(), args.name or args.ticker.upper(), args.threshold),
            )
            print(f"✅ Símbolo {args.ticker.upper()} añadido (umbral: ±{args.threshold}%).")
        except sqlite3.IntegrityError:
            print(f"⚠️  {args.ticker.upper()} ya existe. Actualizando...")
            conn.execute(
                "UPDATE symbols SET name=?, threshold=?, active=1 WHERE ticker=?",
                (args.name or args.ticker.upper(), args.threshold, args.ticker.upper()),
            )
            print(f"✅ {args.ticker.upper()} actualizado.")


def del_symbol(args):
    with get_conn() as conn:
        conn.execute(
            "UPDATE symbols SET active=0 WHERE ticker=?",
            (args.ticker.upper(),),
        )
    print(f"✅ {args.ticker.upper()} desactivado.")


def list_symbols(args):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker, name, threshold, active FROM symbols ORDER BY ticker"
        ).fetchall()
    print(f"\n{'Ticker':<8} {'Nombre':<30} {'Umbral':>8} {'Estado':>8}")
    print("-" * 60)
    for r in rows:
        estado = "✅ Activo" if r["active"] else "❌ Inactivo"
        print(f"{r['ticker']:<8} {(r['name'] or ''):<30} {r['threshold']:>7.1f}% {estado:>8}")
    print()


def list_alerts(args):
    days = getattr(args, "days", 7)
    since = (datetime.now() - timedelta(days=days)).date().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ticker, alert_date, open_price, current_price,
                      change_pct, direction, notified_email, notified_tg
               FROM alert_history WHERE alert_date >= ? ORDER BY created_at DESC""",
            (since,),
        ).fetchall()

    print(f"\nAlertas de los últimos {days} días:\n")
    print(f"{'Fecha':<12} {'Ticker':<8} {'Apertura':>10} {'Actual':>10} {'Cambio':>9} {'Email':>6} {'Tg':>4}")
    print("-" * 68)
    for r in rows:
        em = "✅" if r["notified_email"] else "❌"
        tg = "✅" if r["notified_tg"] else "❌"
        print(
            f"{r['alert_date']:<12} {r['ticker']:<8} "
            f"{r['open_price']:>10.2f} {r['current_price']:>10.2f} "
            f"{r['change_pct']:>+8.2f}% {em:>6} {tg:>4}"
        )
    print()


def test_email(args):
    # Initialise DB first (creates tables if needed)
    sys.path.insert(0, os.path.dirname(__file__))
    from monitor import send_email, init_db
    init_db()
    ok = send_email(
        "✅ Test Email – Stock Monitor",
        "<h2>Stock Monitor</h2><p>El email funciona correctamente.</p>",
    )
    print("✅ Email enviado." if ok else "❌ No se pudo enviar el email.")


def test_telegram(args):
    sys.path.insert(0, os.path.dirname(__file__))
    from monitor import send_telegram, init_db
    init_db()
    ok = send_telegram("✅ <b>Stock Monitor</b> – Telegram funcionando correctamente.")
    print("✅ Telegram enviado." if ok else "❌ No se pudo enviar el mensaje.")


# ── Parser ────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Stock Monitor – Gestión de configuración")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("show-config", help="Muestra la configuración actual")

    e = sub.add_parser("set-email", help="Configura el email")
    e.add_argument("--host",      required=True)
    e.add_argument("--port",      type=int, default=587)
    e.add_argument("--user",      required=True)
    e.add_argument("--pass",      required=True, dest="pass")
    e.add_argument("--from",      required=True, dest="frm")
    e.add_argument("--to",        required=True)

    t = sub.add_parser("set-telegram", help="Configura Telegram")
    t.add_argument("--token",     required=True)
    t.add_argument("--chat",      required=True)

    sub.add_parser("enable-email")
    sub.add_parser("disable-email")
    sub.add_parser("enable-telegram")
    sub.add_parser("disable-telegram")

    a = sub.add_parser("add-symbol", help="Añade símbolo")
    a.add_argument("--ticker",    required=True)
    a.add_argument("--name",      default=None)
    a.add_argument("--threshold", type=float, default=2.0)

    d = sub.add_parser("del-symbol", help="Desactiva símbolo")
    d.add_argument("--ticker",    required=True)

    sub.add_parser("list-symbols", help="Lista símbolos")

    la = sub.add_parser("list-alerts", help="Lista historial de alertas")
    la.add_argument("--days", type=int, default=7)

    sub.add_parser("test-email",    help="Envía email de prueba")
    sub.add_parser("test-telegram", help="Envía mensaje Telegram de prueba")

    args = p.parse_args()

    dispatch = {
        "show-config":      show_config,
        "set-email":        set_email,
        "set-telegram":     set_telegram,
        "enable-email":     lambda a: toggle_email(a, 1),
        "disable-email":    lambda a: toggle_email(a, 0),
        "enable-telegram":  lambda a: toggle_telegram(a, 1),
        "disable-telegram": lambda a: toggle_telegram(a, 0),
        "add-symbol":       add_symbol,
        "del-symbol":       del_symbol,
        "list-symbols":     list_symbols,
        "list-alerts":      list_alerts,
        "test-email":       test_email,
        "test-telegram":    test_telegram,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
