"""
prices.py
─────────
Price fetching via yfinance and calculation of the daily change
relative to the *previous trading-day close* (not today's open).

Weekend / holiday handling is automatic: the function always looks
back until it finds a complete trading day, so Monday always uses
Friday's close, and a post-holiday session uses the last pre-holiday close.
"""

from datetime import date
from typing import Optional

import yfinance as yf

from config import get_logger



log = get_logger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _last_trading_close(ticker: str) -> Optional[float]:
    """
    Return the close price of the most recent *completed* trading day
    that is strictly before today.

    Fetches 7 calendar days of daily bars so that weekends and single-day
    holidays are always covered.
    """
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="7d", interval="1d")
        if hist.empty:
            log.warning("No historical data for %s", ticker)
            return None

        today_str = date.today().isoformat()
        hist.index = hist.index.normalize()     # type: ignore # strip intraday time component
        prev_rows = hist[hist.index.strftime("%Y-%m-%d") < today_str]   # type: ignore

        if prev_rows.empty:
            log.warning("No previous trading-day data for %s", ticker)
            return None

        return float(prev_rows.iloc[-1]["Close"])

    except Exception as exc:
        log.error("Error fetching previous close for %s: %s", ticker, exc)
        return None


def _current_price(ticker: str) -> Optional[float]:
    """
    Return the latest available price for *ticker*.

    Tries fast_info (real-time / delayed quote) first; falls back to the
    last bar of the intraday 1-minute history.
    """
    try:
        tk = yf.Ticker(ticker)
        price = tk.fast_info.get("lastPrice") or tk.fast_info.get("last_price")
        if price:
            return float(price)

        # Fallback: last 1-minute bar
        hist = tk.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist.iloc[-1]["Close"])

        return None

    except Exception as exc:
        log.error("Error fetching current price for %s: %s", ticker, exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_price_change(ticker: str) -> Optional[dict]:
    """
    Return a dict with price data and the % change vs. the previous
    trading-day close, or None if data cannot be retrieved.

    Returned keys:
        ticker      str   – symbol
        prev_close  float – last completed trading-day close
        current     float – latest price
        change_pct  float – rounded to 2 decimals
        direction   str   – "▲ SUBE" | "▼ BAJA"
        date        str   – today's date (ISO-8601)
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
