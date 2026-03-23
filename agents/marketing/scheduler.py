"""
Scheduler con cron para ejecutar el agente de marketing.
Lunes, miércoles y viernes al mediodía (12:00 UTC-3).
"""
import logging
import time
import schedule
from datetime import datetime

logger = logging.getLogger(__name__)


def _run_agent() -> None:
    """Ejecuta el pipeline del agente de marketing."""
    # Import local para evitar circular
    from agents.marketing.marketing_agent import run_pipeline
    logger.info("=== Ejecución programada: %s ===", datetime.now().isoformat())
    try:
        run_pipeline()
    except Exception as e:
        logger.error("Error en ejecución programada: %s", e)


def start_scheduler() -> None:
    """Inicia el scheduler: lunes, miércoles y viernes a las 12:00."""
    logger.info("Iniciando scheduler de marketing...")

    # Lunes, miércoles y viernes al mediodía
    schedule.every().monday.at("12:00").do(_run_agent)
    schedule.every().wednesday.at("12:00").do(_run_agent)
    schedule.every().friday.at("12:00").do(_run_agent)

    logger.info("Programado: Lun/Mié/Vie a las 12:00")
    logger.info("Próxima ejecución: %s", schedule.next_run())

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    start_scheduler()
