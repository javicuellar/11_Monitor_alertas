"""
alerts.py
─────────
Orquesta un ciclo completo de comprobación de precios:
  1. Carga los símbolos activos desde la BD.
  2. Obtiene la variación de precio de cada uno.
  3. Para los que superan el umbral (y no han sido alertados hoy),
     construye y envía las notificaciones, luego persiste la alerta.
"""

from datetime import date

from .config import obtener_logger
from .database import ya_alertado, obtener_simbolos_activos, guardar_alerta
from .notifications import (
    construir_html_email,
    construir_mensaje_telegram,
    enviar_email,
    enviar_telegram,
)
from .prices import obtener_variacion_precio




log = obtener_logger(__name__)



def ejecutar_comprobacion() -> None:
    """Ejecuta un ciclo completo de comprobación de precios y alertas."""
    log.info("=== Iniciando ciclo de comprobación ===")

    simbolos = obtener_simbolos_activos()
    if not simbolos:
        log.warning("No hay símbolos activos en la base de datos.")
        return

    alertas_a_enviar: list[dict] = []

    for sim in simbolos:
        ticker = sim["ticker"]
        umbral = sim["umbral"]
        log.info("Comprobando %s (umbral: ±%.1f%%)", ticker, umbral)

        datos = obtener_variacion_precio(ticker)
        if datos is None:
            continue

        log.info("  %s → cambio vs. cierre anterior: %+.2f%%", ticker, datos["cambio_porcentaje"])

        if abs(datos["cambio_porcentaje"]) >= umbral:
            if ya_alertado(ticker, datos["fecha"]):
                log.info("  Ya se envió alerta hoy para %s, omitiendo.", ticker)
                continue
            log.info("  ⚡ ¡ALERTA! Supera el umbral de ±%.1f%%", umbral)
            alertas_a_enviar.append(datos)

    if not alertas_a_enviar:
        log.info("Sin alertas que enviar en este ciclo.")
        return

    # Construir y despachar notificaciones
    asunto = (
        f"⚠️ Alerta precios {date.today().strftime('%d/%m/%Y')} "
        f"– {len(alertas_a_enviar)} activo(s)"
    )
    ok_email    = enviar_email(asunto, construir_html_email(alertas_a_enviar))
    ok_telegram = enviar_telegram(construir_mensaje_telegram(alertas_a_enviar))

    # Persistir resultados
    for a in alertas_a_enviar:
        guardar_alerta(a, ok_email, ok_telegram)

    log.info("Ciclo finalizado. Alertas enviadas: %d", len(alertas_a_enviar))
