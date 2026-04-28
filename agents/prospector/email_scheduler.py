"""
Scheduler del Email Prospector — corre run_daily() a las 9:00 AM.
"""
import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)


def daily_job() -> None:
    """Ejecuta pipeline diario del email prospector."""
    from agents.prospector.email_prospector import get_agent
    agent = get_agent()
    try:
        result = agent.run_daily()
        logger.info("EmailProspector OK: %s", result)
        agent.log("scheduler_ok", result)
    except Exception as e:
        logger.exception("EmailProspector falló")
        try:
            agent.send_whatsapp(
                "59891722750",
                f"❌ Email Prospector scheduler falló: {e}"
            )
        except Exception:
            pass
        agent.log("scheduler_error", {"error": str(e)})


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Iniciando scheduler del Email Prospector...")

    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, "cron", hour=9, minute=0,
                       id="email_prospector_daily")
    logger.info("Job programado: run_daily() a las 09:00 AM")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
