"""
stock_monitor
─────────────
Stock & ETF price monitor package.

Public re-exports for convenient one-line imports:

    from stock_monitor import run_scheduler, run_check
"""

from .alerts import run_check
from .database import init_db
from .scheduler import run_scheduler


__all__ = ["init_db", "run_check", "run_scheduler"]
