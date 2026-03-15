"""
prices.py
─────────
Obtención de precios via yfinance y cálculo de la variación diaria
respecto al *cierre del último día hábil anterior* (no la apertura de hoy).

El manejo de fines de semana y festivos es automático: la función siempre
retrocede hasta encontrar un día de trading completo, por lo que el lunes
siempre usa el cierre del viernes, y una sesión tras un festivo usa el
cierre del último día hábil previo.
"""

from datetime import date
from typing import Optional

import yfinance as yf

from .config import obtener_logger




log = obtener_logger(__name__)


# ── Funciones internas ────────────────────────────────────────────────────────

def _cierre_ultimo_dia_habil(ticker: str) -> Optional[float]:
    """
    Devuelve el precio de cierre del día de trading más reciente
    que sea estrictamente anterior a hoy.

    Obtiene 7 días naturales de barras diarias para cubrir siempre
    fines de semana y festivos de un solo día.
    """
    try:
        tk = yf.Ticker(ticker)
        historial = tk.history(period="7d", interval="1d")
        if historial.empty:
            log.warning("Sin datos históricos para %s", ticker)
            return None

        hoy_str = date.today().isoformat()
        historial.index = historial.index.normalize()  # type: ignore
        filas_anteriores = historial[historial.index.strftime("%Y-%m-%d") < hoy_str]  # type: ignore

        if filas_anteriores.empty:
            log.warning("Sin datos del día anterior para %s", ticker)
            return None

        return float(filas_anteriores.iloc[-1]["Close"])

    except Exception as exc:
        log.error("Error al obtener el cierre anterior de %s: %s", ticker, exc)
        return None


def _precio_actual(ticker: str) -> Optional[float]:
    """
    Devuelve el precio más reciente disponible para el ticker.

    Intenta primero fast_info (cotización en tiempo real o diferida);
    si no está disponible, usa la última barra del historial intradía de 1 minuto.
    """
    try:
        tk = yf.Ticker(ticker)
        precio = tk.fast_info.get("lastPrice") or tk.fast_info.get("last_price")
        if precio:
            return float(precio)

        # Alternativa: última barra de 1 minuto
        historial = tk.history(period="1d", interval="1m")
        if not historial.empty:
            return float(historial.iloc[-1]["Close"])

        return None

    except Exception as exc:
        log.error("Error al obtener el precio actual de %s: %s", ticker, exc)
        return None


# ── API pública ───────────────────────────────────────────────────────────────

def obtener_variacion_precio(ticker: str) -> Optional[dict]:
    """
    Devuelve un diccionario con los datos de precio y el % de variación
    respecto al cierre del último día hábil, o None si no se pueden obtener datos.

    Claves del diccionario devuelto:
        ticker              str   – símbolo
        cierre_anterior     float – cierre del último día hábil completo
        precio_actual       float – precio más reciente
        cambio_porcentaje   float – redondeado a 2 decimales
        direccion           str   – "▲ SUBE" | "▼ BAJA"
        fecha               str   – fecha de hoy (ISO-8601)
    """
    cierre_anterior = _cierre_ultimo_dia_habil(ticker)
    if cierre_anterior is None:
        return None

    precio_actual = _precio_actual(ticker)
    if precio_actual is None:
        return None

    cambio_porcentaje = ((precio_actual - cierre_anterior) / cierre_anterior) * 100

    return {
        "ticker":            ticker,
        "cierre_anterior":   cierre_anterior,
        "precio_actual":     precio_actual,
        "cambio_porcentaje": round(cambio_porcentaje, 2),
        "direccion":         "▲ SUBE" if cambio_porcentaje > 0 else "▼ BAJA",
        "fecha":             date.today().isoformat(),
    }
