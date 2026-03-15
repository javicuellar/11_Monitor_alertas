"""
notifications.py
────────────────
Email and Telegram notification senders, plus the HTML / plain-text
message builders that format alert data for each channel.
"""

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import get_logger
from database import get_email_config, get_telegram_config



log = get_logger(__name__)



# ── Message builders ──────────────────────────────────────────────────────────

def build_email_html(alerts: list[dict]) -> str:
    """Render an HTML table summarising all triggered alerts."""
    rows = ""
    for a in alerts:
        color = "#c0392b" if a["change_pct"] < 0 else "#27ae60"
        rows += (
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #ddd'><b>{a['ticker']}</b></td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{a['prev_close']:.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{a['current']:.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;color:{color}'>"
            f"  {a['direction']} {abs(a['change_pct']):.2f}%"
            f"</td>"
            f"</tr>"
        )

    today = date.today().strftime("%d/%m/%Y")
    return f"""
    <html><body>
    <h2 style="font-family:Arial">📈 Alerta de Precio – {today}</h2>
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
    """Render a plain HTML-formatted Telegram message for all triggered alerts."""
    today = date.today().strftime("%d/%m/%Y")
    lines = [f"📊 <b>Alertas de Precio</b> – {today}\n"]
    for a in alerts:
        emoji = "🔴" if a["change_pct"] < 0 else "🟢"
        lines.append(
            f"{emoji} <b>{a['ticker']}</b>: {a['direction']} "
            f"<b>{abs(a['change_pct']):.2f}%</b>  "
            f"(Cierre ant.: {a['prev_close']:.2f} → Actual: {a['current']:.2f})"
        )
    return "\n".join(lines)




# ── Senders ───────────────────────────────────────────────────────────────────

def send_email(subject: str, body: str) -> bool:
    """
    Send an HTML e-mail using the SMTP settings stored in *email_config*.
    Returns True on success, False if disabled or on error.
    """
    cfg = get_email_config()
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
    """
    Send a Telegram message via the Bot API using settings in *telegram_config*.
    Returns True on success, False if disabled or on error.
    """
    cfg = get_telegram_config()
    if not cfg:
        log.info("Telegram notifications disabled or not configured.")
        return False

    try:
        url     = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        payload = {"chat_id": cfg["chat_id"], "text": message, "parse_mode": "HTML"}
        resp    = requests.post(url, json=payload, timeout=10)

        if resp.ok:
            log.info("Telegram message sent to chat %s", cfg["chat_id"])
            return True

        log.error("Telegram API error: %s", resp.text)
        return False

    except Exception as exc:
        log.error("Telegram error: %s", exc)
        return False
