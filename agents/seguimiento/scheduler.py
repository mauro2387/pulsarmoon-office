"""
Scheduler del agente de seguimiento — corre diariamente a las 09:00 AM UY.
"""
import logging
import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_followup_check():
    """Ejecuta la detección de leads pendientes."""
    from agents.seguimiento.followup_agent import _agent
    try:
        result = _agent.create_followup_batch()
        logger.info("Follow-up batch: %d pendientes", result["pending"])
    except Exception as e:
        logger.error("Error en follow-up batch: %s", e)


def main():
    """Arranca scheduler con ejecución inmediata si hay pendientes."""
    logger.info("Iniciando scheduler de seguimiento...")

    # Ejecución inmediata al arrancar
    run_followup_check()

    scheduler = BlockingScheduler(timezone="America/Montevideo")
    scheduler.add_job(
        run_followup_check,
        "cron",
        hour=9,
        minute=0,
        id="daily_followup",
    )
    logger.info("Scheduler activo — próxima ejecución: 09:00 AM UY")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
