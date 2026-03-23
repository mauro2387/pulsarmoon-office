"""
Scheduler del agente de inteligencia — lunes 06:00 AM Montevideo.
Al arrancar verifica si ya corrió esta semana; si no, ejecuta inmediatamente.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()
logger = logging.getLogger(__name__)


def weekly_job():
    """Ejecuta pipeline semanal de inteligencia."""
    from agents.inteligencia.intelligence_agent import run_weekly
    try:
        result = run_weekly()
        logger.info("Inteligencia: %s",
                     result.get("opportunity_summary", "completado"))
    except Exception as e:
        logger.error("Error en pipeline inteligencia: %s", e)


def _already_ran_this_week() -> bool:
    """Verifica si ya hay insights de esta semana."""
    try:
        from db.database import get_db
        now = datetime.now()
        week = now.isocalendar()[1]
        year = now.year
        row = get_db().fetchone(
            "SELECT id FROM intelligence_insights "
            "WHERE week_number = %s AND year = %s",
            (week, year))
        return row is not None
    except Exception:
        return False


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )

    # Crear tablas si no existen
    try:
        from db.database import get_db
        db = get_db()
        db.setup_tables()
        db.setup_intelligence_tables()
    except Exception as e:
        logger.error("Error creando tablas: %s", e)

    # Si no corrió esta semana, ejecutar ahora
    if not _already_ran_this_week():
        logger.info("Sin análisis esta semana — ejecutando ahora...")
        weekly_job()
    else:
        logger.info("Ya hay análisis de esta semana, esperando próximo lunes.")

    logger.info("Iniciando scheduler de Inteligencia...")
    scheduler = BlockingScheduler(timezone="America/Montevideo")
    scheduler.add_job(weekly_job, "cron", day_of_week="mon",
                      hour=6, minute=0)
    logger.info("Job programado: run_weekly() lunes 06:00 AM UY")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido.")


if __name__ == "__main__":
    main()
