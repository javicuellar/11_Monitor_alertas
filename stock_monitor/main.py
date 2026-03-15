#!/usr/bin/env python3
"""
main.py
───────
Entry point for the Stock & ETF Price Monitor.

Usage
─────
    python main.py            # start the scheduler loop (default)
    python main.py --once     # run a single check cycle and exit

Environment variables
─────────────────────
    DB_PATH   path to the SQLite database file  (default: /data/monitor.db)
"""

import argparse
import sys

from database import init_db
from alerts import run_check
from scheduler import run_scheduler




def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor de precios de acciones y ETFs",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single check cycle and exit (useful for cron jobs)",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    print("args:", args)
    init_db()

    if args.once:
        run_check()
        sys.exit(0)
    else:
        run_scheduler()



if __name__ == "__main__":
    main()
