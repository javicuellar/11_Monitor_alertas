"""
notifications.py
────────────────
Funciones de envío de notificaciones por email y Telegram, junto con los
constructores de mensajes HTML y texto plano que dan formato a los datos
de alerta para cada canal.
"""

import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from .config import obtener_logger
from .database import obtener_config_email, obtener_config_telegram



log = obtener_logger(__name__)


# ── Constructores de mensajes ─────────────────────────────────────────────────

def construir_html_email(alertas: list[dict]) -> str:
    """Genera una tabla HTML con todas las alertas disparadas."""
    filas = ""
    for a in alertas:
        color = "#c0392b" if a["cambio_porcentaje"] < 0 else "#27ae60"
        filas += (
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #ddd'><b>{a['ticker']}</b></td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{a['cierre_anterior']:.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd'>{a['precio_actual']:.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;color:{color}'>"
            f"  {a['direccion']} {abs(a['cambio_porcentaje']):.2f}%"
            f"</td>"
            f"</tr>"
        )

    hoy = date.today().strftime("%d/%m/%Y")
    return f"""
    <html><body>
    <h2 style="font-family:Arial">📈 Alerta de Precio – {hoy}</h2>
    <table style="border-collapse:collapse;font-family:Arial;font-size:14px">
      <thead>
        <tr style="background:#2c3e50;color:white">
          <th style="padding:8px">Ticker</th>
          <th style="padding:8px">Cierre anterior</th>
          <th style="padding:8px">Precio actual</th>
          <th style="padding:8px">Cambio</th>
        </tr>
      </thead>
      <tbody>{filas}</tbody>
    </table>
    <p style="font-family:Arial;color:#7f8c8d;font-size:12px">
      Generado automáticamente por Monitor de Acciones
    </p>
    </body></html>"""



def construir_mensaje_telegram(alertas: list[dict]) -> str:
    """Genera un mensaje de Telegram con formato HTML para todas las alertas disparadas."""
    hoy = date.today().strftime("%d/%m/%Y")
    lineas = [f"📊 <b>Alertas de Precio</b> – {hoy}\n"]
    for a in alertas:
        emoji = "🔴" if a["cambio_porcentaje"] < 0 else "🟢"
        lineas.append(
            f"{emoji} <b>{a['ticker']}</b>: {a['direccion']} "
            f"<b>{abs(a['cambio_porcentaje']):.2f}%</b>  "
            f"(Cierre ant.: {a['cierre_anterior']:.2f} → Actual: {a['precio_actual']:.2f})"
        )
    return "\n".join(lineas)


# ── Envío de notificaciones ───────────────────────────────────────────────────

def enviar_email(asunto: str, cuerpo: str) -> bool:
    """
    Envía un email HTML usando la configuración SMTP almacenada en configuracion_email.
    Devuelve True si tiene éxito, False si está desactivado o hay un error.
    """
    cfg = obtener_config_email()
    if not cfg:
        log.info("Notificaciones por email desactivadas o no configuradas.")
        return False

    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"]    = cfg["direccion_origen"]
        mensaje["To"]      = cfg["direccion_destino"]
        mensaje.attach(MIMEText(cuerpo, "html", "utf-8"))

        with smtplib.SMTP(cfg["servidor_smtp"], cfg["puerto_smtp"]) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(cfg["usuario"], cfg["password"])
            servidor.sendmail(cfg["direccion_origen"], cfg["direccion_destino"], mensaje.as_string())

        log.info("Email enviado a %s", cfg["direccion_destino"])
        return True

    except Exception as exc:
        log.error("Error al enviar email: %s", exc)
        return False


def enviar_telegram(mensaje: str) -> bool:
    """
    Envía un mensaje de Telegram via Bot API usando la configuracion_telegram.
    Devuelve True si tiene éxito, False si está desactivado o hay un error.
    """
    cfg = obtener_config_telegram()
    if not cfg:
        log.info("Notificaciones de Telegram desactivadas o no configuradas.")
        return False

    try:
        url     = f"https://api.telegram.org/bot{cfg['token_bot']}/sendMessage"
        payload = {"chat_id": cfg["id_chat"], "text": mensaje, "parse_mode": "HTML"}
        resp    = requests.post(url, json=payload, timeout=10)

        if resp.ok:
            log.info("Mensaje de Telegram enviado al chat %s", cfg["id_chat"])
            return True

        log.error("Error en la API de Telegram: %s", resp.text)
        return False

    except Exception as exc:
        log.error("Error al enviar Telegram: %s", exc)
        return False
