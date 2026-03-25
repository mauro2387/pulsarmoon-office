"""
Analizador semanal de inteligencia de mercado.
EXACTAMENTE 1 llamada a Haiku por semana — analiza todas las señales.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.base_agent import BaseAgent
from db.database import get_db

logger = logging.getLogger(__name__)

# Meses en español
_MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# Sistema para el analista — cacheado con ephemeral
_SYSTEM_ANALYST = """
Sos un analista de mercado senior especializado en el mercado uruguayo,
especialmente en Punta del Este y Maldonado. Trabajás para PulsarMoon,
una agencia de desarrollo web, sistemas y marketing digital.

TU OBJETIVO: identificar oportunidades de negocio reales para PulsarMoon
analizando señales del mercado uruguayo.

SECTORES QUE NOS INTERESAN:
- Turismo y hotelería (hoteles, apart hoteles, alquileres temporada)
- Gastronomía (restaurants, bares, cafeterías, delivery)
- Salud privada (clínicas, consultorios, centros médicos, estética)
- Inmobiliarias y constructoras
- Comercios y retail (tiendas, boutiques, farmacias)
- Servicios profesionales (estudios contables, jurídicos, arquitectura)
- Fitness y bienestar (gimnasios, spas, centros de yoga)
- Educación privada (institutos, academias)
- Automotrices y servicios de vehículos
- Tecnología y startups locales

SEÑALES DE OPORTUNIDAD ESPECIAL:
- Si ves búsquedas como 'trabaja con nosotros', 'empleos', 'se busca personal'
  → significa que una empresa está creciendo y necesita digitalización
- Si ves 'impo_empresas_nuevas' en las señales → son empresas recién constituidas,
  máxima prioridad como leads potenciales
- Relacioná siempre las tendencias con oportunidades concretas para PulsarMoon

IGNORAR COMPLETAMENTE:
- Política, elecciones, partidos
- Deportes y equipos de fútbol
- Farándula y entretenimiento
- Crímenes y accidentes
- Clima y desastres naturales
- Noticias internacionales sin relación directa con negocios locales
- Pornografía o contenido adulto
- Criptomonedas especulativas

Respondé SIEMPRE en JSON válido, sin texto extra ni backticks.
"""


def _get_season(month: int) -> str:
    """Retorna temporada turística según el mes."""
    if month in (12, 1, 2, 3):
        return "ALTA (verano, temporada turística fuerte en Punta del Este)"
    if month in (4, 5):
        return "Media-baja (otoño, post-temporada)"
    if month in (6, 7, 8):
        return "BAJA (invierno, vacaciones julio pueden activar turismo interno)"
    return "Media (primavera, pre-temporada, negocios preparándose)"


def _get_history() -> tuple[list[str], list[str]]:
    """Obtiene temas de marketing y sectores prospectados recientes."""
    db = get_db()
    topics = []
    sectors = []
    try:
        rows = db.fetchall(
            "SELECT topic FROM content ORDER BY created_at DESC LIMIT 4")
        topics = [r["topic"] for r in rows]
    except Exception:
        pass
    try:
        rows = db.fetchall(
            "SELECT sector FROM leads "
            "GROUP BY sector ORDER BY MAX(created_at) DESC LIMIT 4")
        sectors = [r["sector"] for r in rows]
    except Exception:
        pass
    return topics, sectors


def analyze_weekly_signals(week_number: int, year: int) -> dict:
    """Analiza señales de la semana con 1 llamada a Haiku."""
    db = get_db()

    # 1. Obtener señales de la semana
    rows = db.fetchall(
        "SELECT title, content, source FROM raw_intelligence "
        "WHERE week_number = %s AND year = %s "
        "ORDER BY collected_at DESC LIMIT 150",
        (week_number, year))

    if not rows:
        logger.warning("Sin señales para semana %d/%d", week_number, year)
        return _empty_insights()

    # 2. Formatear señales como lista numerada
    signals_text = "\n".join(
        f"{i+1}. [{r['source']}] {r['title']}"
        for i, r in enumerate(rows))

    # 3. Historial para evitar repetición
    topics, sectors = _get_history()
    topics_str = ", ".join(topics) if topics else "ninguno aún"
    sectors_str = ", ".join(sectors) if sectors else "ninguno aún"

    # 4. Contexto temporal
    now = datetime.now()
    month = now.month
    mes_nombre = _MESES[month]
    season = _get_season(month)

    # 5. Llamada a Haiku (1 por semana)
    user_msg = f"""Semana {week_number} del año {year}. Mes: {mes_nombre}.
Temporada: {season}.

Temas de marketing ya usados (NO repetir): {topics_str}
Sectores ya prospectados recientemente (variar): {sectors_str}

SEÑALES DEL MERCADO ESTA SEMANA ({len(rows)} señales):
{signals_text}

Analizá estas señales y devolvé:
{{
  "hot_sectors": ["sector1", "sector2", "sector3"],
  "prospector_queries": [
    "hotel Punta del Este",
    "apart hotel Maldonado",
    "restaurant Punta del Este",
    "clinica privada Maldonado",
    "gym Punta del Este"
  ],
  "marketing_topic": "tema concreto y específico para un blog post esta semana",
  "marketing_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "opportunity_summary": "2 líneas explicando qué está pasando en el mercado esta semana",
  "seasonal_context": "qué tiene de especial esta época del año para los negocios en Uruguay",
  "ignore_reason": "qué descartaste y por qué"
}}"""

    # Crear agente temporal para la llamada LLM
    agent = BaseAgent(
        agent_id="intel-01", agent_name="Analista",
        department="inteligencia", model="haiku",
        company_id="pulsarmoon")

    insights = agent.call_llm_json(user_msg, _SYSTEM_ANALYST, max_tokens=1000)

    if not insights:
        logger.error("Haiku no retornó insights válidos")
        return _empty_insights()

    # 6. Guardar en intelligence_insights
    try:
        db.execute(
            "INSERT INTO intelligence_insights "
            "(week_number, year, hot_sectors, prospector_queries, "
            "marketing_topic, marketing_keywords, opportunity_summary, "
            "raw_signals_count) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (week_number, year) DO UPDATE SET "
            "hot_sectors = EXCLUDED.hot_sectors, "
            "prospector_queries = EXCLUDED.prospector_queries, "
            "marketing_topic = EXCLUDED.marketing_topic, "
            "marketing_keywords = EXCLUDED.marketing_keywords, "
            "opportunity_summary = EXCLUDED.opportunity_summary, "
            "raw_signals_count = EXCLUDED.raw_signals_count",
            (week_number, year,
             json.dumps(insights.get("hot_sectors", [])),
             json.dumps(insights.get("prospector_queries", [])),
             insights.get("marketing_topic", ""),
             json.dumps(insights.get("marketing_keywords", [])),
             insights.get("opportunity_summary", ""),
             len(rows)))
    except Exception as e:
        logger.error("Error guardando insights: %s", e)

    logger.info("Insights semana %d/%d: %s", week_number, year,
                insights.get("opportunity_summary", "")[:80])
    return insights


def _empty_insights() -> dict:
    """Retorna insights vacíos como fallback."""
    return {
        "hot_sectors": [],
        "prospector_queries": [],
        "marketing_topic": "",
        "marketing_keywords": [],
        "opportunity_summary": "Sin señales suficientes esta semana",
        "seasonal_context": "",
        "ignore_reason": "",
    }
