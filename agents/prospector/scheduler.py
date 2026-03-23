"""
Scheduler del Prospector — ejecuta run_daily() a las 10:00 AM.
"""
import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

# Path para imports
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)


def daily_job():
    """Ejecuta pipeline diario del prospector."""
    from agents.prospector.prospector_agent import run_daily
    try:
        result = run_daily()
        logger.info("Prospector: %d leads encontrados", result["total"])
    except Exception as e:
        logger.error("Error en pipeline prospector: %s", e)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    logger.info("Iniciando scheduler del Prospector...")

    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, "cron", hour=10, minute=0)
    logger.info("Job programado: run_daily() a las 10:00 AM")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
