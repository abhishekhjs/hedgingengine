#!/usr/bin/env python3
"""Standalone ingestion script for the Japan Manufacturing Market Risk Monitor.

Usage:
    python run_ingestion.py

This script can be called manually or scheduled via cron / Windows Task Scheduler.
It initializes the database (if needed), runs the full ingestion pipeline for all
data sources (FRED, yfinance, MOF), computes risk metrics, and exits.

Exit codes:
    0 — All sources ingested successfully
    1 — Partial failure (some sources failed, others succeeded)
    2 — Total failure (all sources failed or critical error)
"""
import sys
import logging
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("run_ingestion")


def main():
    """Run the full ingestion pipeline."""
    logger.info("=" * 60)
    logger.info("Japan Manufacturing Market Risk Monitor — Data Ingestion")
    logger.info("=" * 60)

    from src.ingestion.runner import run_full_ingestion, check_source_connectivity

    # Pre-flight connectivity check
    logger.info("Checking data source connectivity...")
    connectivity = check_source_connectivity()
    for source, reachable in connectivity.items():
        status = "[OK] reachable" if reachable else "[FAIL] unreachable"
        logger.info(f"  {source}: {status}")

    unreachable = [s for s, r in connectivity.items() if not r]
    if len(unreachable) == len(connectivity):
        logger.error("All data sources are unreachable. Check your network connection.")
        sys.exit(2)
    elif unreachable:
        logger.warning(
            f"Some sources are unreachable: {', '.join(unreachable)}. "
            "Proceeding with available sources."
        )

    # Run ingestion
    logger.info("")
    logger.info("Starting data ingestion...")
    status = run_full_ingestion()

    # Report results
    logger.info("")
    logger.info("Ingestion Results:")
    logger.info("-" * 40)
    failures = 0
    for source, result in status.items():
        icon = "[OK]" if result == "ok" else "[FAIL]"
        logger.info(f"  {icon} {source}: {result}")
        if result != "ok":
            failures += 1

    total = len(status)
    logger.info("-" * 40)
    logger.info(f"  {total - failures}/{total} sources completed successfully.")

    if failures == total:
        logger.error("All ingestion steps failed.")
        sys.exit(2)
    elif failures > 0:
        logger.warning("Some ingestion steps failed. See errors above.")
        sys.exit(1)
    else:
        logger.info("All ingestion steps completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
