"""
config.py
─────────
Global constants and logging configuration shared by all modules.
"""

import logging
import os
import sys



# ── Database path ─────────────────────────────────────────────────────────────
DB_PATH: str = os.environ.get("DB_PATH", "/data/monitor.db")


# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger with a consistent format."""
    return logging.getLogger(name)
