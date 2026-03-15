"""
scheduler.py
────────────
Time-window guard and the main scheduler loop.

The loop re-reads `scheduler_config` from the DB on every iteration,
so any change made while the process is running takes effect on the
next tick — no restart needed.

scheduler_config columns
────────────────────────
interval_minutes  – how often to run a check cycle          (default 30)
start_time        – earliest allowed start time  HH:MM 24h  (default 09:00)
end_time          – latest  allowed start time   HH:MM 24h  (default 22:00)
weekdays_only     – 1 = skip Sat & Sun, 0 = run every day   (default 1)
"""

import time
from datetime import datetime

from alerts import run_check
from config import get_logger
from database import get_scheduler_config



log = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_hhmm(hhmm: str) -> tuple[int, int]:
    """Parse 'HH:MM' string into (hour, minute) integers."""
    h, m = hhmm.strip().split(":")
    return int(h), int(m)


def is_active_window(cfg: dict) -> bool:
    """
    Return True if *now* falls within the configured check window.

    Checks:
      - weekday constraint  (weekdays_only=1 skips Saturday=5 and Sunday=6)
      - time-of-day window  [start_time, end_time] inclusive
    """
    now = datetime.now()

    if cfg["weekdays_only"] and now.weekday() >= 5:
        return False

    start_h, start_m = _parse_hhmm(cfg["start_time"])
    end_h,   end_m   = _parse_hhmm(cfg["end_time"])

    start_dt = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_dt   = now.replace(hour=end_h,   minute=end_m,   second=0, microsecond=0)

    return start_dt <= now <= end_dt



# ── Main loop ─────────────────────────────────────────────────────────────────

def run_scheduler() -> None:
    """
    Infinite loop that fires run_check() whenever the current moment
    is inside the configured active window.

    Configuration is reloaded from the DB on every iteration.
    """
    log.info("=== Scheduler arrancado ===")

    while True:
        cfg              = get_scheduler_config()
        interval_seconds = cfg["interval_minutes"] * 60

        if is_active_window(cfg):
            try:
                run_check()
            except Exception as exc:
                log.error("Error inesperado en run_check: %s", exc)
        else:
            log.info(
                "Fuera de ventana horaria (%s–%s, solo_laborables=%s). "
                "Próximo ciclo en %d min.",
                cfg["start_time"], cfg["end_time"],
                cfg["weekdays_only"], cfg["interval_minutes"],
            )

        log.info("Durmiendo %d minutos…", cfg["interval_minutes"])
        time.sleep(interval_seconds)
