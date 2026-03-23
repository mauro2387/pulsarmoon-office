"""
Agente de Inteligencia de Mercado de PulsarMoon.
Orquesta: colección de señales → análisis con Haiku → insights para otros agentes.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from agents.inteligencia.collector import (
    collect_google_trends,
    collect_mercadolibre_signals,
    collect_rss_feeds,
    save_raw_signals,
)
from agents.inteligencia.analyzer import analyze_weekly_signals
from db.database import get_db

logger = logging.getLogger(__name__)


class IntelligenceAgent(BaseAgent):
    """Recolecta señales del mercado y genera insights semanales."""

    def __init__(self):
        super().__init__(
            agent_id="intel-01",
            agent_name="Analista",
            department="inteligencia",
            model="haiku",
            company_id="pulsarmoon",
        )

    def run_weekly(self) -> dict:
        """Pipeline semanal completo: recolectar + analizar."""
        now = datetime.now()
        week = now.isocalendar()[1]
        year = now.year

        # 1. Google Trends
        self.write_event("working", "Recolectando señales del mercado...")
        try:
            signals_trends = collect_google_trends()
        except Exception as e:
            logger.error("Error Google Trends: %s", e)
            signals_trends = []

        # 2. RSS + noticias
        self.write_event("working", "Leyendo noticias de negocios Uruguay...")
        try:
            signals_rss = collect_rss_feeds()
        except Exception as e:
            logger.error("Error RSS: %s", e)
            signals_rss = []

        # 3. MercadoLibre
        self.write_event("working", "Analizando Mercado Libre Uruguay...")
        try:
            signals_ml = collect_mercadolibre_signals()
        except Exception as e:
            logger.error("Error MercadoLibre: %s", e)
            signals_ml = []

        # 4. Guardar señales
        all_signals = signals_trends + signals_rss + signals_ml
        saved = save_raw_signals(all_signals)
        self.log("signals_collected", {
            "trends": len(signals_trends),
            "rss": len(signals_rss),
            "mercadolibre": len(signals_ml),
            "saved": saved,
        })

        # 5. Análisis con Haiku (1 llamada)
        self.write_event("working",
                         f"Analizando {len(all_signals)} señales con IA...")
        insights = analyze_weekly_signals(week, year)
        self.log("weekly_analysis", insights)

        summary = insights.get("opportunity_summary", "")[:50]
        self.write_event("done", f"Análisis listo: {summary}...")
        return insights

    def get_current_insights(self) -> dict:
        """Retorna insights de la semana actual. Corre análisis si no hay."""
        now = datetime.now()
        week = now.isocalendar()[1]
        year = now.year

        try:
            row = get_db().fetchone(
                "SELECT * FROM intelligence_insights "
                "WHERE week_number = %s AND year = %s",
                (week, year))
            if row:
                # Deserializar JSONB si vienen como string
                for field in ("hot_sectors", "prospector_queries",
                              "marketing_keywords"):
                    if isinstance(row.get(field), str):
                        row[field] = __import__("json").loads(row[field])
                return dict(row)
        except Exception as e:
            logger.warning("Error leyendo insights: %s", e)

        # No hay insights de esta semana → correr pipeline
        return self.run_weekly()


# Instancia global
_agent = IntelligenceAgent()


def run_weekly() -> dict:
    """Wrapper para scheduler."""
    return _agent.run_weekly()


def get_current_insights() -> dict:
    """Wrapper para otros agentes."""
    return _agent.get_current_insights()
